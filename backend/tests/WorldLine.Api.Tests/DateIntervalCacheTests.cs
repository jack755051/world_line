using WorldLine.Api.Common;

namespace WorldLine.Api.Tests;

public class DateIntervalCacheTests
{
    private static DateOnly D(string s) => DateOnly.Parse(s);

    [Fact]
    public void Interval_start_is_the_last_change_point_not_after_the_date()
    {
        var pts = new[] { D("1914-07-29"), D("1914-08-20"), D("1918-11-11") };
        Assert.Equal(DateOnly.MinValue, DateIntervalCache.IntervalStart(pts, D("1914-07-28")));
        Assert.Equal(D("1914-07-29"), DateIntervalCache.IntervalStart(pts, D("1914-07-29")));
        Assert.Equal(D("1914-07-29"), DateIntervalCache.IntervalStart(pts, D("1914-08-19")));
        // 半開區間：迄日當天已是新區間
        Assert.Equal(D("1914-08-20"), DateIntervalCache.IntervalStart(pts, D("1914-08-20")));
        Assert.Equal(D("1918-11-11"), DateIntervalCache.IntervalStart(pts, D("1945-01-01")));
        Assert.Equal(DateOnly.MinValue, DateIntervalCache.IntervalStart([], D("1945-01-01")));
    }

    private static readonly DateOnly[] Pts = [D("1908-01-01"), D("1914-07-28"), D("1918-11-11"), D("1924-01-01"), D("1939-09-01")];

    private static async Task<(string Value, bool Built)> Get(DateIntervalCache c, string kind, string date, long size)
    {
        var built = false;
        var v = await c.GetOrAddAsync(kind, D(date), Pts, () => { built = true; return Task.FromResult($"{kind}@{date}"); }, _ => size);
        return (v, built);
    }

    [Fact] // LRU（Tai 2026-11-04）：超過估算上限時淘汰最久沒用的，最近用過的留著；被淘汰的再要時按需重算
    public async Task Lru_evicts_least_recently_used_when_over_the_byte_limit()
    {
        var c = new DateIntervalCache(maxBytes: 300);
        Assert.True((await Get(c, "s", "1910-01-01", 100)).Built);
        Assert.True((await Get(c, "s", "1915-01-01", 100)).Built);
        Assert.True((await Get(c, "s", "1920-01-01", 100)).Built);
        Assert.Equal(300, c.EstimatedBytes);
        // 同一區間另一天直接命中，並把 1910 那筆變成最近用過
        Assert.False((await Get(c, "s", "1913-12-31", 100)).Built);
        // 加第 4 筆超過上限 → 淘汰最久沒用的 1915 區間（不是最早放進來的 1910）
        Assert.True((await Get(c, "s", "1930-01-01", 100)).Built);
        Assert.Equal(3, c.Count);
        Assert.Equal(300, c.EstimatedBytes);
        Assert.True(c.Contains("s", D("1910-01-01"), Pts));
        Assert.False(c.Contains("s", D("1915-01-01"), Pts));
        Assert.Equal(1, c.Stats.Evictions);
        // 被淘汰的按需重算後回來，值正確
        var again = await Get(c, "s", "1916-06-01", 100);
        Assert.True(again.Built);
        Assert.Equal("s@1916-06-01", again.Value);
        Assert.True(c.EstimatedBytes <= c.MaxBytes);
    }

    [Fact] // 單筆比上限還大：照樣回傳，但不進快取、不擠掉其他項目
    public async Task Entry_larger_than_the_limit_is_returned_but_not_cached()
    {
        var c = new DateIntervalCache(maxBytes: 300);
        await Get(c, "s", "1910-01-01", 100);
        var big = await Get(c, "fine", "1910-01-01", 301);
        Assert.Equal("fine@1910-01-01", big.Value);
        Assert.False(c.Contains("fine", D("1910-01-01"), Pts));
        Assert.True(c.Contains("s", D("1910-01-01"), Pts));
        Assert.Equal(100, c.EstimatedBytes);
    }

    [Fact] // 寫入作廢：清空快取與用量；作廢前開始計算的結果不會放回快取
    public async Task Invalidate_clears_entries_and_drops_results_computed_before_it()
    {
        var c = new DateIntervalCache(maxBytes: 1000);
        await Get(c, "s", "1910-01-01", 100);
        c.Invalidate();
        Assert.Equal(0, c.Count);
        Assert.Equal(0, c.EstimatedBytes);
        var v = await c.GetOrAddAsync("s", D("1920-01-01"), Pts, () => { c.Invalidate(); return Task.FromResult("stale"); }, _ => 100);
        Assert.Equal("stale", v);
        Assert.Equal(0, c.Count);
        Assert.True((await Get(c, "s", "1920-01-01", 100)).Built);
    }

    [Fact] // 種類（容差層、衝突）各自一筆，共用同一個上限
    public async Task Kinds_are_cached_separately_under_one_limit()
    {
        var c = new DateIntervalCache(maxBytes: 250);
        await Get(c, "sovereignty:0.010", "1940-07-15", 100);
        await Get(c, "conflicts", "1940-07-15", 100);
        Assert.Equal(2, c.Count);
        await Get(c, "sovereignty:0.002", "1940-07-15", 100);
        Assert.Equal(2, c.Count);
        Assert.False(c.Contains("sovereignty:0.010", D("1940-07-15"), Pts));
    }

    [Fact]
    public void Prewarm_date_parses_default_empty_and_bad_values()
    {
        Assert.Equal(D("1940-07-15"), Program.ParsePrewarmDate(null));
        Assert.Null(Program.ParsePrewarmDate(""));
        Assert.Null(Program.ParsePrewarmDate("bad"));
        Assert.Equal(D("1908-06-15"), Program.ParsePrewarmDate(" 1908-06-15 "));
    }

    [Fact]
    public void Production_only_runs_tiles_so_sovereignty_geojson_is_not_prewarmed()
    {
        Assert.False(Program.PrewarmSovereignty("Production", null));
        Assert.True(Program.PrewarmSovereignty("Development", null));
        Assert.False(Program.PrewarmSovereignty("Development", "tiles"));
        Assert.True(Program.PrewarmSovereignty("Production", "geojson"));
    }

    // 30 個變動點：1910-01-01 起每年一個
    private static readonly DateOnly[] Yearly = Enumerable.Range(0, 30).Select(i => new DateOnly(1910 + i, 1, 1)).ToArray();

    private static Task<string> At(DateIntervalCache c, string kind, int year, long size = 10) =>
        c.GetOrAddAsync(kind, new DateOnly(year, 6, 15), Yearly, () => Task.FromResult($"{kind}@{year}"), _ => size);

    [Fact] // 滑動視窗（Tai 2026-11-04）：只留目前查詢日期前後各 N 個區間，視窗外的直接丟掉
    public async Task Window_keeps_only_intervals_within_radius_of_the_current_date()
    {
        var c = new DateIntervalCache(maxBytes: 1_000_000, windowRadius: 2, prefetchCount: 1);
        foreach (var y in new[] { 1915, 1916, 1917 }) await At(c, "s", y);
        await At(c, "conflicts", 1917);
        Assert.Equal(4, c.Count);
        // 跳到 1919：中心 9，1915（5）、1916（6）在視窗外丟掉；1917（7）留著
        await At(c, "s", 1919);
        Assert.False(c.Contains("s", D("1915-06-15"), Yearly));
        Assert.False(c.Contains("s", D("1916-06-15"), Yearly));
        Assert.True(c.Contains("s", D("1917-06-15"), Yearly));
        Assert.True(c.Contains("conflicts", D("1917-06-15"), Yearly));
        Assert.Equal(3, c.Count);
        Assert.Equal(30, c.EstimatedBytes);
        // 大跳到 1935：整個視窗換掉
        await At(c, "s", 1935);
        Assert.Equal(1, c.Count);
        Assert.Equal((25, 1), c.Window);
    }

    [Fact] // 播放方向由前後兩次查詢判斷；預先載入往那個方向找第一個還沒快取的區間，最多 PrefetchCount 格
    public async Task Prefetch_targets_follow_the_playback_direction()
    {
        var c = new DateIntervalCache(maxBytes: 1_000_000, windowRadius: 5, prefetchCount: 3);
        Assert.Null(c.NextPrefetchTarget("s", Yearly, c.Version)); // 還沒有任何查詢
        await At(c, "s", 1919);
        await At(c, "s", 1920); // 往後播，中心 10
        Assert.Equal((11, D("1921-01-01")), c.NextPrefetchTarget("s", Yearly, c.Version));
        await At(c, "s", 1921); await At(c, "s", 1920); // 再往後一格又往回一格：中心 10、方向 -1
        Assert.Equal((10, -1), c.Window);
        // 往前播：1919（9）已快取，跳過，下一個是 1918（8）
        Assert.Equal((8, D("1918-01-01")), c.NextPrefetchTarget("s", Yearly, c.Version));
        // 別的 kind 自己算
        Assert.Equal((9, D("1919-01-01")), c.NextPrefetchTarget("conflicts", Yearly, c.Version));
        // 到頭了：中心 0 往前播沒有目標
        await At(c, "s", 1911); await At(c, "s", 1910);
        Assert.Null(c.NextPrefetchTarget("s", Yearly, c.Version));
    }

    [Fact] // 視窗外的結果（算好時使用者已跳走）不放進快取；作廢後視窗重設
    public async Task Results_outside_the_window_are_not_cached()
    {
        var c = new DateIntervalCache(maxBytes: 1_000_000, windowRadius: 2, prefetchCount: 1);
        await At(c, "s", 1920);
        var slow = new TaskCompletionSource<string>();
        // 同時：查 1921 的請求還在算，使用者已跳到 1930
        var pending = c.GetOrAddAsync("s", D("1921-06-15"), Yearly, () => slow.Task, _ => 10);
        await At(c, "s", 1930);
        slow.SetResult("late");
        Assert.Equal("late", await pending);
        // 1921 計算期間視窗中心被 1921 那次查詢移到 11、又被 1930 移到 20：1921 不在視窗內，不快取
        Assert.False(c.Contains("s", D("1921-06-15"), Yearly));
        c.Invalidate();
        Assert.Equal((int.MinValue, 1), c.Window);
    }

    [Fact]
    public void Window_settings_are_validated()
    {
        var c = new DateIntervalCache();
        Assert.Equal((10, 3), (c.WindowRadius, c.PrefetchCount));
        Assert.Throws<ArgumentOutOfRangeException>(() => new DateIntervalCache(1000, windowRadius: -1));
        Assert.Throws<ArgumentOutOfRangeException>(() => new DateIntervalCache(1000, windowRadius: 2, prefetchCount: 3));
    }

    [Fact]
    public void Default_limit_is_1_5_GB_and_must_be_positive()
    {
        Assert.Equal(1536L * 1024 * 1024, new DateIntervalCache().MaxBytes);
        Assert.Throws<ArgumentOutOfRangeException>(() => new DateIntervalCache(0));
    }
}
