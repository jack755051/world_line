using System.Text.RegularExpressions;
using NodaTime;

namespace WorldLine.Api.Domain;

public readonly record struct EdtfParseResult(bool IsValid, EdtfDate? Date, string? Reason)
{
    public static EdtfParseResult Success(EdtfDate date) => new(true, date, null);
    public static EdtfParseResult Failure(string reason) => new(false, null, reason);
}

public interface IEdtfService
{
    /// <summary>解析單一 EDTF 日期字串（用於 historical_events.start_edtf/end_edtf 各自欄位）。</summary>
    EdtfParseResult TryParse(string? edtf);
}

/// <summary>
/// task 2.2：憲法/PRD/notes 實際會用到的 EDTF 子集解析器——年／年-月／年-月-日、負年份（西元前）、
/// 尾綴 `?`/`~` 不確定標記。不追求完整 EDTF 規格覆蓋（季節、集合、遮罩精度等，見 PRD §5/§9
/// 「EDTF 時間解析」的停止條件記錄：.NET 生態沒有堪用的成熟套件，退回自訂簡化版）。
///
/// 語法解析自己寫（純字串處理，範圍小、風險低）；閏年/負年份的曆法數學交給 NodaTime（見
/// <see cref="EdtfDate.ToDecimalYear"/>），不自己刻——這是最容易犯錯的部分。
/// </summary>
public class EdtfService : IEdtfService
{
    // -?YYYY(-MM(-DD)?)?，尾綴 ? 或 ~ 已在呼叫前被 TryParse 剝離。
    private static readonly Regex Pattern = new(
        @"^(?<sign>-)?(?<year>\d{4})(-(?<month>\d{2})(-(?<day>\d{2}))?)?$",
        RegexOptions.Compiled);

    public EdtfParseResult TryParse(string? edtf)
    {
        if (string.IsNullOrWhiteSpace(edtf))
        {
            return EdtfParseResult.Failure("EDTF 字串不可為空");
        }

        var qualifier = EdtfQualifier.None;
        var working = edtf;

        if (working.EndsWith('?'))
        {
            qualifier = EdtfQualifier.Uncertain;
            working = working[..^1];
        }
        else if (working.EndsWith('~'))
        {
            qualifier = EdtfQualifier.Approximate;
            working = working[..^1];
        }

        var match = Pattern.Match(working);
        if (!match.Success)
        {
            return EdtfParseResult.Failure(
                $"「{edtf}」不符合支援的 EDTF 子集格式（僅支援 -?YYYY(-MM(-DD)?)? 加選用的尾綴 ?/~）");
        }

        // EDTF/ISO 8601 絕對紀年：西元 0 年＝西元前 1 年。字串裡的負號直接對應絕對紀年的負數，
        // 不需要額外 +1/-1 調整——這剛好跟 NodaTime LocalDate 的 year 參數是同一套慣例
        // （NodaTime 官方文件：「a value of 0 means 1 BC」），可以直接把解析出的 year 傳進去。
        var year = int.Parse(match.Groups["year"].ValueSpan);
        if (match.Groups["sign"].Success)
        {
            year = -year;
        }

        int? month = match.Groups["month"].Success ? int.Parse(match.Groups["month"].ValueSpan) : null;
        int? day = match.Groups["day"].Success ? int.Parse(match.Groups["day"].ValueSpan) : null;

        var precision = day.HasValue ? EdtfPrecision.Day : month.HasValue ? EdtfPrecision.Month : EdtfPrecision.Year;

        try
        {
            // 只為了借用 CalendarSystem.Iso 的驗證邏輯（月份 1-12、日期依月份與閏年正確範圍、
            // 支援西元前 9998 年到西元 9999 年）——建構成功即代表這是一個合法存在的日期。
            _ = new LocalDate(year, month ?? 1, day ?? 1, CalendarSystem.Iso);
        }
        catch (ArgumentOutOfRangeException ex)
        {
            return EdtfParseResult.Failure($"「{edtf}」不是合法存在的日期：{ex.Message}");
        }

        return EdtfParseResult.Success(new EdtfDate(year, month, day, precision, qualifier));
    }
}
