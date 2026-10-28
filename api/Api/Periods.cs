using System.Globalization;
using System.Text.RegularExpressions;
using NpgsqlTypes;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Api;

/// <summary>
/// API 用的「部分日期」：YYYY、YYYY-MM、YYYY-MM-DD（精度依寫法而定，I7）。
/// 作為起點時取最早一天，作為終點時取最後一天（例：迄「1945」= 1945-12-31）。
/// 限制：.NET DateOnly 只能表示西元 1–9999 年，西元前日期目前 API 不接受（資料庫 daterange 本身支援）。
/// </summary>
public sealed partial record PartialDate(int Year, int? Month, int? Day)
{
    [GeneratedRegex(@"^(?<y>\d{4})(?:-(?<m>\d{2})(?:-(?<d>\d{2}))?)?$")]
    private static partial Regex Pattern();

    public string Precision => Day is not null ? DatePrecision.Day : Month is not null ? DatePrecision.Month : DatePrecision.Year;

    public DateOnly Earliest => new(Year, Month ?? 1, Day ?? 1);

    public DateOnly Latest => Day is not null
        ? new DateOnly(Year, Month!.Value, Day.Value)
        : Month is not null
            ? new DateOnly(Year, Month.Value, DateTime.DaysInMonth(Year, Month.Value))
            : new DateOnly(Year, 12, 31);

    public static bool TryParse(string? input, out PartialDate? result, out string? error)
    {
        result = null;
        error = null;
        if (string.IsNullOrWhiteSpace(input)) { error = "日期不可為空"; return false; }
        var m = Pattern().Match(input.Trim());
        if (!m.Success)
        {
            error = $"「{input}」不是 YYYY、YYYY-MM 或 YYYY-MM-DD（西元前日期暫不支援）";
            return false;
        }
        var y = int.Parse(m.Groups["y"].Value, CultureInfo.InvariantCulture);
        int? mo = m.Groups["m"].Success ? int.Parse(m.Groups["m"].Value, CultureInfo.InvariantCulture) : null;
        int? d = m.Groups["d"].Success ? int.Parse(m.Groups["d"].Value, CultureInfo.InvariantCulture) : null;
        if (y < 1) { error = "年份必須介於 0001–9999（西元前日期暫不支援）"; return false; }
        if (mo is < 1 or > 12) { error = $"「{input}」月份不合法"; return false; }
        if (d is not null && (d < 1 || d > DateTime.DaysInMonth(y, mo!.Value))) { error = $"「{input}」日期不存在"; return false; }
        result = new PartialDate(y, mo, d);
        return true;
    }

    /// <summary>依精度輸出（I7：只知年就只輸出年）。</summary>
    public static string Format(DateOnly date, string precision) => precision switch
    {
        DatePrecision.Day => date.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        DatePrecision.Month => date.ToString("yyyy-MM", CultureInfo.InvariantCulture),
        _ => date.ToString("yyyy", CultureInfo.InvariantCulture),
    };
}

/// <summary>日期區間（daterange）換算與查詢視窗。</summary>
public static class Periods
{
    /// <summary>含頭含尾 [from, to]；to 為 null 代表無終點（仍存續／未記錄）。</summary>
    public static NpgsqlRange<DateOnly> Of(DateOnly from, DateOnly? to) =>
        to is null
            ? new NpgsqlRange<DateOnly>(from, true, false, default, false, true)
            : new NpgsqlRange<DateOnly>(from, true, to.Value, true);

    public static NpgsqlRange<DateOnly> Of(PartialDate from, PartialDate? to) => Of(from.Earliest, to?.Latest);

    /// <summary>便利寫法（seed／測試）：Of("1939-09-01", "1945")。</summary>
    public static (NpgsqlRange<DateOnly> Range, string FromPrecision, string? ToPrecision) Parse(string from, string? to)
    {
        if (!PartialDate.TryParse(from, out var f, out var e1)) throw new FormatException(e1);
        PartialDate? t = null;
        if (to is not null && !PartialDate.TryParse(to, out t, out var e2)) throw new FormatException(e2);
        return (Of(f!, t), f!.Precision, t?.Precision);
    }

    public static DateOnly Lower(NpgsqlRange<DateOnly> r) => r.LowerBoundIsInclusive ? r.LowerBound : r.LowerBound.AddDays(1);

    public static DateOnly? UpperInclusive(NpgsqlRange<DateOnly> r) =>
        r.UpperBoundInfinite ? null : r.UpperBoundIsInclusive ? r.UpperBound : r.UpperBound.AddDays(-1);

    public static string FromText(NpgsqlRange<DateOnly> r, string precision) => PartialDate.Format(Lower(r), precision);

    public static string? ToText(NpgsqlRange<DateOnly> r, string? precision) =>
        UpperInclusive(r) is { } to ? PartialDate.Format(to, precision ?? DatePrecision.Day) : null;

    /// <summary>同一段期間（不論是否已被 DB 正規化成 [起, 迄+1)）。</summary>
    public static bool SameSpan(NpgsqlRange<DateOnly> a, NpgsqlRange<DateOnly> b) =>
        Lower(a) == Lower(b) && UpperInclusive(a) == UpperInclusive(b);

    public static bool Within(NpgsqlRange<DateOnly> inner, NpgsqlRange<DateOnly> outer)
    {
        if (Lower(inner) < Lower(outer)) return false;
        var outerTo = UpperInclusive(outer);
        if (outerTo is null) return true;
        var innerTo = UpperInclusive(inner);
        return innerTo is not null && innerTo <= outerTo;
    }

    public static string Describe(NpgsqlRange<DateOnly> r) =>
        $"{Lower(r):yyyy-MM-dd}～{(UpperInclusive(r) is { } t ? t.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) : "迄今")}";

    /// <summary>
    /// 查詢視窗：date=YYYY-MM-DD（當天）或 year=YYYY（捷徑：該年任一天，區間有交集即納入）。
    /// 兩者都沒給時回傳 null（呼叫端決定必填與否）。
    /// </summary>
    public static bool TryWindow(DateOnly? date, int? year, out NpgsqlRange<DateOnly>? window, out Dictionary<string, string[]>? errors)
    {
        window = null;
        errors = null;
        if (date is not null && year is not null)
        {
            errors = new() { ["date"] = ["date 與 year 擇一提供"] };
            return false;
        }
        if (date is not null)
        {
            window = Of(date.Value, date.Value);
            return true;
        }
        if (year is not null)
        {
            if (year < 1 || year > 9999)
            {
                errors = new() { ["year"] = ["year 必須介於 1–9999（西元前查詢暫不支援）"] };
                return false;
            }
            window = Of(new DateOnly(year.Value, 1, 1), new DateOnly(year.Value, 12, 31));
            return true;
        }
        return true;
    }

    public static Dictionary<string, string[]> Required() =>
        new() { ["date"] = ["請提供 date（YYYY-MM-DD）或 year（捷徑：該年任一天）"] };
}

/// <summary>寫入端點共用的起訖輸入解析。</summary>
public static class PeriodInput
{
    public sealed record Parsed(PartialDate From, PartialDate? To)
    {
        public NpgsqlTypes.NpgsqlRange<DateOnly> Range => Periods.Of(From, To);
    }

    /// <summary>解析 from/to（YYYY｜YYYY-MM｜YYYY-MM-DD）。requireTo：I1／I6 要求有終點。</summary>
    public static Parsed? Parse(string? from, string? to, bool requireTo, string fromKey, string toKey, Dictionary<string, string[]> errors)
    {
        PartialDate? f = null, t = null;
        if (string.IsNullOrWhiteSpace(from)) errors[fromKey] = [$"{fromKey} 必填（YYYY、YYYY-MM 或 YYYY-MM-DD）"];
        else if (!PartialDate.TryParse(from, out f, out var e)) errors[fromKey] = [e!];
        if (string.IsNullOrWhiteSpace(to))
        {
            if (requireTo) errors[toKey] = [$"{toKey} 必填（必須有起訖日期）"];
        }
        else if (!PartialDate.TryParse(to, out t, out var e)) errors[toKey] = [e!];
        if (f is not null && t is not null && t.Latest < f.Earliest) errors[toKey] = ["結束日期不可早於起始日期"];
        return f is null || errors.ContainsKey(fromKey) || errors.ContainsKey(toKey) ? null : new Parsed(f, t);
    }
}
