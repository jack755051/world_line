using NpgsqlTypes;
using WorldLine.Api.Api;
using WorldLine.Api.Edtf;

namespace WorldLine.Api.Tests;

/// <summary>不需資料庫的純邏輯測試：EDTF 解析、年份區間換算、API Key 比對。</summary>
public class EdtfDateTests
{
    [Theory]
    [InlineData("0751-07~", 751, 751, EdtfPrecision.Month, false, true, 751.496, 751.578)]
    [InlineData("0220", 220, 220, EdtfPrecision.Year, false, false, 220.000, 220.997)]
    [InlineData("0208?", 208, 208, EdtfPrecision.Year, true, false, 208.000, 208.997)]
    [InlineData("0280-05-01%", 280, 280, EdtfPrecision.Day, true, true, 280.331, 280.331)]
    [InlineData("-0201", -201, -201, EdtfPrecision.Year, false, false, -201.000, -200.003)]
    [InlineData("075X", 750, 759, EdtfPrecision.Year, false, false, 750.000, 759.997)]
    public void Parses_and_computes_decimal_range(string input, int earliest, int latest, EdtfPrecision precision,
        bool uncertain, bool approximate, double lo, double hi)
    {
        Assert.True(EdtfDate.TryParse(input, out var d, out var error), error);
        Assert.Equal(earliest, d!.EarliestYear);
        Assert.Equal(latest, d.LatestYear);
        Assert.Equal(precision, d.Precision);
        Assert.Equal(uncertain, d.Uncertain);
        Assert.Equal(approximate, d.Approximate);
        Assert.Equal((decimal)lo, d.EarliestDecimal);
        Assert.Equal((decimal)hi, d.LatestDecimal);
        Assert.True(d.EarliestDecimal <= d.LatestDecimal);
    }

    [Theory]
    [InlineData("")]
    [InlineData("751")]
    [InlineData("0751-13")]
    [InlineData("0751-02-30")]
    [InlineData("0750-02-29")]
    [InlineData("abcd")]
    [InlineData("0751/0752")]
    public void Rejects_invalid_or_unsupported(string input) =>
        Assert.False(EdtfDate.TryParse(input, out _, out _));

    [Theory]
    [InlineData(2000, true)]
    [InlineData(1900, false)]
    [InlineData(2024, true)]
    [InlineData(0, true)]    // 西元前 1 年（天文紀年 0）在預期格里曆中是閏年
    [InlineData(-4, true)]
    [InlineData(-1, false)]
    [InlineData(-100, false)]
    public void Proleptic_gregorian_leap_years(int year, bool leap) => Assert.Equal(leap, EdtfDate.IsLeapYear(year));

    [Fact]
    public void Leap_day_is_valid_in_leap_year() => Assert.True(EdtfDate.TryParse("0752-02-29", out _, out _));
}

public class RangesTests
{
    [Fact]
    public void Closed_range_round_trips_inclusive_years()
    {
        var r = Ranges.Closed(618, 907);
        Assert.Equal(618, Ranges.Lower(r));
        Assert.Equal(907, Ranges.UpperInclusive(r));
    }

    [Fact]
    public void Db_normalized_range_is_read_back_inclusive()
    {
        // PostgreSQL 會把 [618,907] 正規化成 [618,908)
        var r = new NpgsqlRange<int>(618, true, 908, false);
        Assert.Equal(618, Ranges.Lower(r));
        Assert.Equal(907, Ranges.UpperInclusive(r));
    }

    [Fact]
    public void Open_upper_bound_means_unknown_end()
    {
        var r = Ranges.From(750, null);
        Assert.True(r.UpperBoundInfinite);
        Assert.Null(Ranges.UpperInclusive(r));
        Assert.Equal(750, Ranges.Lower(r));
    }
}

public class ApiKeyTests
{
    [Theory]
    [InlineData("abc", "abc", true)]
    [InlineData("abc", "abd", false)]
    [InlineData("abc", "abcd", false)]
    [InlineData("", "abc", false)]
    public void Fixed_time_comparison(string a, string b, bool equal) =>
        Assert.Equal(equal, ApiKeyFilter.FixedTimeEquals(a, b));
}
