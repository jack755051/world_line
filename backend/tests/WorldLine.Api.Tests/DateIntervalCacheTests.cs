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
}
