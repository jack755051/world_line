using NpgsqlTypes;
using WorldLine.Api.Api;
using WorldLine.Api.Edtf;

namespace WorldLine.Api.Tests;

/// <summary>不需資料庫的純邏輯測試：EDTF 解析、日期區間與精度換算、年號數字、API Key 比對。</summary>
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

public class PeriodsTests
{
    [Theory]
    [InlineData("1945", "year", "1945-01-01", "1945-12-31")]
    [InlineData("1944-02", "month", "1944-02-01", "1944-02-29")]
    [InlineData("1941-12-07", "day", "1941-12-07", "1941-12-07")]
    public void Partial_date_precision_follows_written_form(string input, string precision, string earliest, string latest)
    {
        Assert.True(PartialDate.TryParse(input, out var d, out _));
        Assert.Equal(precision, d!.Precision);
        Assert.Equal(DateOnly.ParseExact(earliest, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture), d.Earliest);
        Assert.Equal(DateOnly.ParseExact(latest, "yyyy-MM-dd", System.Globalization.CultureInfo.InvariantCulture), d.Latest);
    }

    [Theory]
    [InlineData("1943-13")]
    [InlineData("1943-02-29")]
    [InlineData("0000")]
    [InlineData("-0201")]
    [InlineData("1943/09/08")]
    [InlineData("")]
    public void Invalid_or_bce_partial_dates_are_rejected(string input) =>
        Assert.False(PartialDate.TryParse(input, out _, out _));

    [Fact]
    public void Output_is_formatted_by_precision()
    {
        var d = new DateOnly(1868, 1, 1);
        Assert.Equal("1868", PartialDate.Format(d, "year"));
        Assert.Equal("1868-01", PartialDate.Format(d, "month"));
        Assert.Equal("1868-01-01", PartialDate.Format(d, "day"));
    }

    [Fact]
    public void Db_normalized_range_is_read_back_inclusive()
    {
        // PostgreSQL 把 [1940-07-10,1944-08-20] 正規化成 [1940-07-10,1944-08-21)
        var r = new NpgsqlRange<DateOnly>(new DateOnly(1940, 7, 10), true, new DateOnly(1944, 8, 21), false);
        Assert.Equal(new DateOnly(1940, 7, 10), Periods.Lower(r));
        Assert.Equal(new DateOnly(1944, 8, 20), Periods.UpperInclusive(r));
        Assert.True(Periods.SameSpan(r, Periods.Parse("1940-07-10", "1944-08-20").Range));
        Assert.Equal("1944-08-20", Periods.ToText(r, "day"));
    }

    [Fact]
    public void Open_upper_bound_means_still_existing()
    {
        var (r, fp, tp) = Periods.Parse("1942-01-01", null);
        Assert.True(r.UpperBoundInfinite);
        Assert.Null(Periods.UpperInclusive(r));
        Assert.Equal("day", fp);
        Assert.Null(tp);
        Assert.True(Periods.Within(Periods.Parse("1943-10-13", null).Range, r));
        Assert.False(Periods.Within(r, Periods.Parse("1942", "1945").Range));
    }

    [Fact]
    public void Query_window_is_single_day_or_whole_year()
    {
        Assert.True(Periods.TryWindow(new DateOnly(1942, 6, 1), null, out var day, out _));
        Assert.Equal(new DateOnly(1942, 6, 1), Periods.Lower(day!.Value));
        Assert.Equal(new DateOnly(1942, 6, 1), Periods.UpperInclusive(day.Value));
        Assert.True(Periods.TryWindow(null, 1943, out var year, out _));
        Assert.Equal(new DateOnly(1943, 12, 31), Periods.UpperInclusive(year!.Value));
        Assert.False(Periods.TryWindow(new DateOnly(1942, 6, 1), 1942, out _, out var errors));
        Assert.NotNull(errors);
        Assert.False(Periods.TryWindow(null, 0, out _, out _));
    }

    [Theory]
    [InlineData(1, "元")]
    [InlineData(9, "九")]
    [InlineData(10, "十")]
    [InlineData(17, "十七")]
    [InlineData(31, "三十一")]
    [InlineData(64, "六十四")]
    [InlineData(100, "一百")]
    [InlineData(105, "一百〇五")]
    public void Era_year_uses_chinese_numerals(int n, string expected) =>
        Assert.Equal(expected, QueryEndpoints.EraNumber(n));
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
