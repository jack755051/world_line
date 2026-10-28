using System.Globalization;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Edtf;

/// <summary>EDTF 日期精度。</summary>
public enum EdtfPrecision { Year, Month, Day }

/// <summary>
/// EDTF（ISO 8601-2 Extended Date/Time Format）單一日期的最小實作，涵蓋 PRD 需要的部分：
/// - Level 0：YYYY、YYYY-MM、YYYY-MM-DD，負號年份（天文紀年：0000 = 西元前 1 年）
/// - Level 1：結尾限定符 ?（不確定）、~（約略）、%（兩者）；年份末位 X（未指定，如 19XX、075X）
/// 產出可計算的小數年份區間 [Earliest, Latest]：以預期格里曆計算當年天數（含閏年），
/// decimal = 年 + (日序 - 1) / 當年天數，四捨五入到小數三位（對應 NUMERIC(8,3)）。
/// 為何不用 npm `edtf`：PRD 原本寫 npm 套件，但寫入驗證與 decimal 推算由 .NET 後端負責
/// （EDTF 字串為 SSOT，後端是唯一寫入方），所以後端用等價的 C# 實作；前端顯示仍可用 npm `edtf`。
/// </summary>
public sealed partial record EdtfDate(
    string Source,
    int EarliestYear,
    int LatestYear,
    int? Month,
    int? Day,
    EdtfPrecision Precision,
    bool Uncertain,
    bool Approximate)
{
    [GeneratedRegex(@"^(?<sign>-)?(?<year>\d{2}[\dX]{2})(?:-(?<month>\d{2})(?:-(?<day>\d{2}))?)?(?<q>[?~%])?$")]
    private static partial Regex Pattern();

    public bool Unspecified => EarliestYear != LatestYear;

    public static bool TryParse(string? input, out EdtfDate? result, out string? error)
    {
        result = null;
        error = null;
        if (string.IsNullOrWhiteSpace(input))
        {
            error = "EDTF 不可為空";
            return false;
        }

        var m = Pattern().Match(input.Trim());
        if (!m.Success)
        {
            error = $"不支援的 EDTF 格式：{input}（支援 YYYY、YYYY-MM、YYYY-MM-DD、負號年份、結尾 ?/~/%、年份末位 X）";
            return false;
        }

        var yearText = m.Groups["year"].Value;
        var negative = m.Groups["sign"].Success;
        var hasX = yearText.Contains('X');
        var lowText = yearText.Replace('X', '0');
        var highText = yearText.Replace('X', '9');
        var low = int.Parse(lowText, CultureInfo.InvariantCulture);
        var high = int.Parse(highText, CultureInfo.InvariantCulture);
        if (negative)
        {
            (low, high) = (-high, -low);
        }

        int? month = m.Groups["month"].Success ? int.Parse(m.Groups["month"].Value, CultureInfo.InvariantCulture) : null;
        int? day = m.Groups["day"].Success ? int.Parse(m.Groups["day"].Value, CultureInfo.InvariantCulture) : null;

        if (hasX && month is not null)
        {
            error = "年份含 X 時不可再指定月日";
            return false;
        }
        if (month is < 1 or > 12)
        {
            error = $"月份不合法：{month}";
            return false;
        }
        if (day is not null && (day < 1 || day > DaysInMonth(low, month!.Value)))
        {
            error = $"日期不合法：{input}";
            return false;
        }

        var q = m.Groups["q"].Value;
        result = new EdtfDate(
            input.Trim(), low, high, month, day,
            day is not null ? EdtfPrecision.Day : month is not null ? EdtfPrecision.Month : EdtfPrecision.Year,
            Uncertain: q is "?" or "%",
            Approximate: q is "~" or "%");
        return true;
    }

    public static EdtfDate Parse(string input) =>
        TryParse(input, out var r, out var e) ? r! : throw new FormatException(e);

    /// <summary>此日期可能的最早時刻（小數年）。</summary>
    public decimal EarliestDecimal => ToDecimal(EarliestYear, DayOfYear(EarliestYear, Month ?? 1, Day ?? 1));

    /// <summary>此日期可能的最晚時刻（小數年，該精度最後一天的起點）。</summary>
    public decimal LatestDecimal
    {
        get
        {
            var m = Month ?? 12;
            var d = Day ?? DaysInMonth(LatestYear, m);
            return ToDecimal(LatestYear, DayOfYear(LatestYear, m, d));
        }
    }

    /// <summary>預期格里曆（天文紀年）閏年判斷，支援負數年份。</summary>
    public static bool IsLeapYear(int year) =>
        (year % 4 == 0 && year % 100 != 0) || year % 400 == 0;

    public static int DaysInYear(int year) => IsLeapYear(year) ? 366 : 365;

    public static int DaysInMonth(int year, int month) => month switch
    {
        2 => IsLeapYear(year) ? 29 : 28,
        4 or 6 or 9 or 11 => 30,
        _ => 31,
    };

    private static int DayOfYear(int year, int month, int day)
    {
        var doy = day;
        for (var mm = 1; mm < month; mm++) doy += DaysInMonth(year, mm);
        return doy;
    }

    private static decimal ToDecimal(int year, int dayOfYear) =>
        Math.Round(year + (decimal)(dayOfYear - 1) / DaysInYear(year), 3, MidpointRounding.AwayFromZero);
}
