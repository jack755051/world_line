using System.Collections.Concurrent;
using System.Runtime.InteropServices;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

namespace WorldLine.Api.Common;

/// <summary>
/// 依「變動區間」快取逐日查詢的結果（主權圖層、衝突）。
/// - 變動點＝主權紀錄、佔領歸屬、陣營、衝突紀錄、首都紀錄所有有效期間的起訖日；兩個相鄰變動點之間每天的結果都一樣，
///   所以播放時一週一格、連跳幾十天，只要還在同一區間就直接命中。
/// - 任何寫入（/api/v1 底下非 GET 且成功的請求，見 <see cref="BumpOnWriteMiddleware"/>）會讓版本 +1，整個快取作廢；
///   不會因為快取而讀到舊資料。
/// - 滑動視窗（Tai 2026-11-04）：以最近一次查詢的日期為中心，只保留前後各 <see cref="WindowRadius"/> 個變動區間
///   （WORLDLINE_CACHE_WINDOW，預設 10），視窗外的直接丟掉；並往播放方向（依前後兩次查詢判斷）背景預先載入
///   下 <see cref="PrefetchCount"/> 個（WORLDLINE_CACHE_PREFETCH，預設 3）。未命中時按需計算。
/// - 另有估算大小上限 <see cref="MaxBytes"/>（WORLDLINE_CACHE_MAX_MB，預設 1.5 GB）當保險：視窗內仍超過時以 LRU 淘汰。
///   （原本全部 591 個日期 × 4 種預熱會吃到 ~7 GB，被系統砍掉。）
/// </summary>
public sealed class DateIntervalCache
{
    /// <summary>預設估算大小上限：1.5 GB。</summary>
    public const long DefaultMaxBytes = 1536L * 1024 * 1024;
    public const int DefaultWindowRadius = 10;
    public const int DefaultPrefetchCount = 3;

    /// <summary>估算不了大小的值，一筆以此計。</summary>
    public const long FallbackEntryBytes = 64 * 1024;

    public DateIntervalCache() : this(DefaultMaxBytes) { }

    public DateIntervalCache(long maxBytes, int windowRadius = DefaultWindowRadius, int prefetchCount = DefaultPrefetchCount)
    {
        if (maxBytes <= 0) throw new ArgumentOutOfRangeException(nameof(maxBytes), "快取上限必須大於 0。");
        if (windowRadius < 0) throw new ArgumentOutOfRangeException(nameof(windowRadius), "視窗半徑不可為負。");
        if (prefetchCount < 0 || prefetchCount > windowRadius) throw new ArgumentOutOfRangeException(nameof(prefetchCount), "預先載入數須介於 0 與視窗半徑之間。");
        MaxBytes = maxBytes;
        WindowRadius = windowRadius;
        PrefetchCount = prefetchCount;
    }

    /// <summary>估算大小上限（位元組）。</summary>
    public long MaxBytes { get; }

    /// <summary>以目前查詢日期為中心，前後各保留幾個變動區間。</summary>
    public int WindowRadius { get; }

    /// <summary>往播放方向背景預先載入幾個變動區間。</summary>
    public int PrefetchCount { get; }

    /// <summary>背景預先載入用：建立新的 DI scope（拿自己的 DbContext）。未設定就不預先載入。</summary>
    public Func<IServiceScope>? ScopeFactory { get; set; }

    private long _version;
    private (long Version, DateOnly[] Points)? _points;
    private readonly SemaphoreSlim _pointsLock = new(1, 1);

    // 視窗＋LRU：字典找節點，串列頭＝最近用過、尾＝最久沒用；全部在 _lruLock 內操作
    private sealed record Entry((string Kind, long Version, DateOnly Key) Key, int Index, object Value, long Bytes);
    private readonly Dictionary<(string Kind, long Version, DateOnly Key), LinkedListNode<Entry>> _entries = new();
    private readonly LinkedList<Entry> _lru = new();
    private readonly Lock _lruLock = new();
    private long _bytes;
    private int _center = int.MinValue; // 目前視窗中心（變動點索引；-1＝早於所有變動點）
    private int _direction = 1;          // +1 往後播、-1 往前播
    private long _hits, _misses, _evictions, _prefetched;
    private readonly ConcurrentDictionary<(string Kind, long Version, DateOnly Key), Task<object>> _inflight = new();
    private readonly ConcurrentDictionary<string, int> _prefetchRunning = new();

    /// <summary>目前快取的估算大小（位元組）。</summary>
    public long EstimatedBytes { get { lock (_lruLock) return _bytes; } }

    /// <summary>目前快取筆數。</summary>
    public int Count { get { lock (_lruLock) return _entries.Count; } }

    /// <summary>目前視窗中心（變動點索引）與播放方向。</summary>
    public (int Center, int Direction) Window { get { lock (_lruLock) return (_center, _direction); } }

    /// <summary>統計（命中、未命中、淘汰、預先載入次數），供 log 與測試。</summary>
    public (long Hits, long Misses, long Evictions, long Prefetched) Stats =>
        (Interlocked.Read(ref _hits), Interlocked.Read(ref _misses), Interlocked.Read(ref _evictions), Interlocked.Read(ref _prefetched));

    public long Version => Interlocked.Read(ref _version);

    public void Invalidate()
    {
        Interlocked.Increment(ref _version);
        lock (_lruLock)
        {
            _entries.Clear();
            _lru.Clear();
            _bytes = 0;
            _center = int.MinValue;
            _direction = 1;
        }
    }

    /// <summary>d 所在區間的起點（不大於 d 的最大變動點；比所有變動點都早時回傳 DateOnly.MinValue）。</summary>
    public static DateOnly IntervalStart(DateOnly[] sortedPoints, DateOnly d)
    {
        var i = Array.BinarySearch(sortedPoints, d);
        if (i >= 0) return sortedPoints[i];
        i = ~i - 1;
        return i >= 0 ? sortedPoints[i] : DateOnly.MinValue;
    }

    public async Task<DateOnly[]> ChangePointsAsync(WorldLineDbContext db, CancellationToken ct)
    {
        var v = Version;
        if (_points is { } p && p.Version == v) return p.Points;
        await _pointsLock.WaitAsync(ct);
        try
        {
            if (_points is { } p2 && p2.Version == v) return p2.Points;
            // 只讀：各表有效期間的起訖日（含已撤回的紀錄也無妨，只是多切幾段）
            const string sql = """
                SELECT d FROM (
                  SELECT lower(valid_period) AS d FROM sovereignty_records UNION SELECT upper(valid_period) FROM sovereignty_records
                  UNION SELECT lower(valid_period) FROM occupation_attributions UNION SELECT upper(valid_period) FROM occupation_attributions
                  UNION SELECT lower(valid_period) FROM regime_alignments UNION SELECT upper(valid_period) FROM regime_alignments
                  UNION SELECT lower(valid_period) FROM conflict_records UNION SELECT upper(valid_period) FROM conflict_records
                  -- 衝突相鄰判定與弧端點用到的屬地對照、扶植關係
                  UNION SELECT lower(valid_period) FROM regime_dependencies UNION SELECT upper(valid_period) FROM regime_dependencies
                  UNION SELECT lower(valid_period) FROM regime_relations WHERE relation_type = 'patron_puppet'
                  UNION SELECT upper(valid_period) FROM regime_relations WHERE relation_type = 'patron_puppet'
                  -- 衝突弧端點優先用首都座標，首都起訖日也是變動點
                  UNION SELECT lower(valid_period) FROM capital_records UNION SELECT upper(valid_period) FROM capital_records
                ) x WHERE d IS NOT NULL ORDER BY d
                """;
            var list = await db.Database.SqlQueryRaw<DateOnly>(sql).ToListAsync(ct);
            var arr = list.ToArray();
            _points = (v, arr);
            return arr;
        }
        finally { _pointsLock.Release(); }
    }

    private (long Version, DateOnly[] Points)? _controlPoints;

    /// <summary>
    /// 控制區圖層（/control）的變動點（移植自 992baba「依變動日區段快取」的控制區部分）：兩個相鄰變動點之間每天的 /control 回應除 date 外相同。
    /// 涵蓋 /control 用到的所有日期條件（保守：寧可多切，不可少切）：控制紀錄現行版本、涵蓋備註、陣營的有效期間起訖；
    /// 快照 as_of 當天與隔天（戰區狀態 attested／interpolated、前後快照參照在這兩天切換）、快照 attested_period 起訖；事件發生日（陣營「補充」事件以 occurred 起日篩選）。
    /// 新增依日期查詢的條件時，這裡也要一起加。
    /// </summary>
    public async Task<DateOnly[]> ControlPointsAsync(WorldLineDbContext db, CancellationToken ct)
    {
        var v = Version;
        if (_controlPoints is { } p && p.Version == v) return p.Points;
        await _pointsLock.WaitAsync(ct);
        try
        {
            if (_controlPoints is { } p2 && p2.Version == v) return p2.Points;
            const string sql = """
                SELECT d FROM (
                  SELECT lower(valid_period) AS d FROM control_record_versions WHERE superseded_by IS NULL AND NOT is_retraction
                  UNION SELECT upper(valid_period) FROM control_record_versions WHERE superseded_by IS NULL AND NOT is_retraction
                  UNION SELECT lower(valid_period) FROM control_coverage_notes UNION SELECT upper(valid_period) FROM control_coverage_notes
                  UNION SELECT lower(valid_period) FROM regime_alignments UNION SELECT upper(valid_period) FROM regime_alignments
                  UNION SELECT as_of FROM control_snapshots UNION SELECT as_of + 1 FROM control_snapshots
                  UNION SELECT lower(attested_period) FROM control_snapshots UNION SELECT upper(attested_period) FROM control_snapshots
                  UNION SELECT lower(occurred) FROM historical_events
                ) x WHERE d IS NOT NULL ORDER BY d
                """;
            var arr = (await db.Database.SqlQueryRaw<DateOnly>(sql).ToListAsync(ct)).ToArray();
            _controlPoints = (v, arr);
            return arr;
        }
        finally { _pointsLock.Release(); }
    }

    /// <summary>
    /// 取 kind 在 d 所在區間的結果；沒有就用這個請求自己的 DbContext 算一次再存（大小以 <see cref="EstimateBytes"/> 估算），
    /// 並把視窗中心移到 d、往播放方向背景預先載入。build 拿（日期, DbContext, 取消）算任一天的結果，預先載入時也用它。
    /// 不共用使用者請求自己的計算：前端會取消過時的請求，共用的話一個請求被取消會連帶讓別的請求失敗
    /// （背景預先載入不會被取消，進行中的會讓同一區間的請求等它）。
    /// </summary>
    public async Task<T> GetOrAddAsync<T>(string kind, DateOnly d, WorldLineDbContext db,
        Func<DateOnly, WorldLineDbContext, CancellationToken, Task<T>> build, CancellationToken ct) where T : class
    {
        var points = await ChangePointsAsync(db, ct);
        var value = await GetOrAddAsync(kind, d, points, () => build(d, db, ct), EstimateBytes);
        SchedulePrefetch(kind, points, (day, ctx) => build(day, ctx, CancellationToken.None));
        return value;
    }

    /// <summary>
    /// 核心（不碰資料庫，單元測試直接用）：依已知變動點取值，並把視窗中心移到 d 所在區間（視窗外的丟掉）。
    /// </summary>
    public async Task<T> GetOrAddAsync<T>(string kind, DateOnly d, DateOnly[] points, Func<Task<T>> factory, Func<T, long> sizeOf) where T : class
    {
        var v = Version;
        var (index, start) = Locate(points, d);
        var key = (kind, v, start);
        Slide(index, v);
        if (TryGet(key, out var hit)) { Interlocked.Increment(ref _hits); return (T)hit; }
        // 背景預先載入正在算這一格：等它（它不會被取消）；失敗就自己算
        if (_inflight.TryGetValue(key, out var pending))
        {
            try { var pv = await pending; Interlocked.Increment(ref _hits); return (T)pv; }
            catch { /* 自己算 */ }
        }
        Interlocked.Increment(ref _misses);
        var value = await factory();
        if (Version == v) Add(key, index, value, Math.Max(1, sizeOf(value)));
        return value;
    }

    /// <summary>
    /// 背景預先載入：往目前播放方向補齊下 <see cref="PrefetchCount"/> 格（每種 kind 同時只跑一個工作者，逐格算；
    /// 每格算之前重新看視窗中心，使用者跳走了就跟著改目標；快取作廢就停）。
    /// </summary>
    public void SchedulePrefetch<T>(string kind, DateOnly[] points, Func<DateOnly, WorldLineDbContext, Task<T>> build) where T : class
    {
        if (PrefetchCount == 0 || ScopeFactory is not { } scopes) return;
        if (!_prefetchRunning.TryAdd(kind, 1)) return; // 已有工作者，它會自己看最新的視窗中心
        var v = Version;
        _ = Task.Run(async () =>
        {
            try
            {
                using var scope = scopes();
                var db = scope.ServiceProvider.GetRequiredService<WorldLineDbContext>();
                while (Version == v && NextPrefetchTarget(kind, points, v) is { } target)
                {
                    var key = (kind, v, target.Start);
                    var tcs = new TaskCompletionSource<object>(TaskCreationOptions.RunContinuationsAsynchronously);
                    if (!_inflight.TryAdd(key, tcs.Task)) break;
                    try
                    {
                        var value = await build(target.Start, db);
                        if (Version == v) Add(key, target.Index, value, Math.Max(1, EstimateBytes(value)));
                        Interlocked.Increment(ref _prefetched);
                        tcs.TrySetResult(value);
                    }
                    catch (Exception ex) { tcs.TrySetException(ex); break; }
                    finally { _inflight.TryRemove(key, out _); }
                }
            }
            catch { /* 背景預先載入失敗不影響服務 */ }
            finally { _prefetchRunning.TryRemove(kind, out _); }
        });
    }

    /// <summary>從目前視窗中心往播放方向，第一個還沒快取、也沒人在算的變動區間（在 PrefetchCount 格內）。</summary>
    internal (int Index, DateOnly Start)? NextPrefetchTarget(string kind, DateOnly[] points, long version)
    {
        lock (_lruLock)
        {
            if (_center == int.MinValue) return null;
            for (var k = 1; k <= PrefetchCount; k++)
            {
                var j = _center + _direction * k;
                if (j < 0 || j >= points.Length) break;
                var key = (kind, version, points[j]);
                if (!_entries.ContainsKey(key) && !_inflight.ContainsKey(key)) return (j, points[j]);
            }
            return null;
        }
    }

    /// <summary>kind 在 d 所在區間是否已在快取（不改變 LRU 順序與視窗）。</summary>
    public bool Contains(string kind, DateOnly d, DateOnly[] points)
    {
        lock (_lruLock) return _entries.ContainsKey((kind, Version, IntervalStart(points, d)));
    }

    /// <summary>d 所在區間：變動點索引（早於所有變動點時 -1）與區間起點。</summary>
    private static (int Index, DateOnly Start) Locate(DateOnly[] points, DateOnly d)
    {
        var i = Array.BinarySearch(points, d);
        if (i < 0) i = ~i - 1;
        return (i, i >= 0 ? points[i] : DateOnly.MinValue);
    }

    /// <summary>視窗中心移到 index：記下播放方向，丟掉視窗外的項目。</summary>
    private void Slide(int index, long version)
    {
        lock (_lruLock)
        {
            if (version != Version) return;
            if (_center != int.MinValue && index != _center) _direction = index > _center ? 1 : -1;
            if (index == _center) return;
            _center = index;
            for (var node = _lru.First; node is not null;)
            {
                var next = node.Next;
                if (Math.Abs(node.Value.Index - index) > WindowRadius) Remove(node);
                node = next;
            }
        }
    }

    private bool TryGet((string, long, DateOnly) key, out object value)
    {
        lock (_lruLock)
        {
            if (_entries.TryGetValue(key, out var node))
            {
                _lru.Remove(node);
                _lru.AddFirst(node); // 用過就移到最前
                value = node.Value.Value;
                return true;
            }
        }
        value = null!;
        return false;
    }

    private void Add((string Kind, long Version, DateOnly Key) key, int index, object value, long bytes)
    {
        // 單筆就超過上限：不快取（只回給這個請求），免得把其他項目全擠掉
        if (bytes > MaxBytes) return;
        lock (_lruLock)
        {
            if (key.Version != Version || _entries.ContainsKey(key)) return; // 期間被作廢，或別的請求先放了
            if (_center != int.MinValue && Math.Abs(index - _center) > WindowRadius) return; // 算好時視窗已經移走
            var node = _lru.AddFirst(new Entry(key, index, value, bytes));
            _entries[key] = node;
            _bytes += bytes;
            while (_bytes > MaxBytes && _lru.Last is { } last && last != node) Remove(last);
        }
    }

    private void Remove(LinkedListNode<Entry> node)
    {
        _lru.Remove(node);
        _entries.Remove(node.Value.Key);
        _bytes -= node.Value.Bytes;
        Interlocked.Increment(ref _evictions);
    }

    /// <summary>
    /// 估算快取值佔用的記憶體（位元組）。幾何是 <see cref="JsonElement"/>（各自一份 JsonDocument：UTF-8 原文＋每個 token 約 12 B 的索引），
    /// 以原文長度 × 2 計，屬性等其他欄位每筆約 2 KB。估不出的型別一律 <see cref="FallbackEntryBytes"/>。
    /// </summary>
    public static long EstimateBytes(object value) => value switch
    {
        IEnumerable<SovereigntyFeature> fs => 4096 + fs.Sum(f => 2048 + GeoJsonBytes(f.Geometry)),
        IEnumerable<ConflictFeature> fs => 4096 + fs.Sum(f => 1024 + GeoJsonBytes(f.Geometry)),
        _ => FallbackEntryBytes,
    };

    private static long GeoJsonBytes(JsonElement g) =>
        g.ValueKind == JsonValueKind.Undefined ? 0 : 2L * JsonMarshal.GetRawUtf8Value(g).Length;
}

/// <summary>/api/v1 底下非 GET／HEAD 的請求成功（2xx）後，讓 <see cref="DateIntervalCache"/> 作廢。</summary>
public sealed class BumpOnWriteMiddleware(RequestDelegate next, DateIntervalCache cache)
{
    public async Task InvokeAsync(HttpContext ctx)
    {
        await next(ctx);
        if (!HttpMethods.IsGet(ctx.Request.Method) && !HttpMethods.IsHead(ctx.Request.Method)
            && ctx.Request.Path.StartsWithSegments("/api/v1") && ctx.Response.StatusCode is >= 200 and < 300)
            cache.Invalidate();
    }
}
