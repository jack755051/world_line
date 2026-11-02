using System.Collections.Concurrent;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Common;

/// <summary>
/// 依「變動區間」快取逐日查詢的結果（主權圖層、衝突）。
/// - 變動點＝主權紀錄、佔領歸屬、陣營、衝突紀錄、首都紀錄所有有效期間的起訖日；兩個相鄰變動點之間每天的結果都一樣，
///   所以播放時一週一格、連跳幾十天，只要還在同一區間就直接命中。
/// - 任何寫入（/api/v1 底下非 GET 且成功的請求，見 <see cref="BumpOnWriteMiddleware"/>）會讓版本 +1，整個快取作廢；
///   不會因為快取而讀到舊資料。
/// - 只放在本行程記憶體，上限 <see cref="MaxEntries"/> 筆，超過就清掉最舊的。
/// </summary>
public sealed class DateIntervalCache
{
    public const int MaxEntries = 400;
    private long _version;
    private (long Version, DateOnly[] Points)? _points;
    private readonly SemaphoreSlim _pointsLock = new(1, 1);
    private readonly ConcurrentDictionary<(string Kind, long Version, DateOnly Key), object> _entries = new();
    private readonly ConcurrentQueue<(string, long, DateOnly)> _order = new();

    public long Version => Interlocked.Read(ref _version);

    public void Invalidate()
    {
        Interlocked.Increment(ref _version);
        _entries.Clear();
        while (_order.TryDequeue(out _)) { }
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
    /// 取 kind 在 d 所在區間的結果；沒有就用這個請求自己的 DbContext 算一次再存。
    /// 不共用進行中的計算：前端會取消過時的請求，共用的話一個請求被取消會連帶讓別的請求失敗。
    /// </summary>
    public async Task<T> GetOrAddAsync<T>(string kind, DateOnly d, WorldLineDbContext db, Func<Task<T>> factory, CancellationToken ct) where T : class
    {
        var v = Version;
        var points = await ChangePointsAsync(db, ct);
        var key = (kind, v, IntervalStart(points, d));
        if (_entries.TryGetValue(key, out var hit)) return (T)hit;
        var value = await factory();
        if (Version == v && _entries.TryAdd(key, value)) { _order.Enqueue(key); Trim(); }
        return value;
    }

    private void Trim()
    {
        while (_entries.Count > MaxEntries && _order.TryDequeue(out var old)) _entries.TryRemove(old, out _);
    }
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
