using NodaTime;

namespace WorldLine.Api.Domain;

/// <summary>
/// 解析後的單一 EDTF 日期值（historical_events.start_edtf/end_edtf 各自對應一筆，兩欄本來就
/// 分開存，不需要處理combined interval 字串）。<see cref="Year"/> 採 EDTF/ISO 8601 的「絕對紀年」
/// 慣例——西元 0 年＝西元前 1 年、-1＝西元前 2 年，以此類推（不是「西元前年份直接取負號」，
/// 兩者差一年，見 <see cref="ToDecimalYear"/> 的計算方式）。
/// </summary>
public readonly record struct EdtfDate(int Year, int? Month, int? Day, EdtfPrecision Precision, EdtfQualifier Qualifier)
{
    /// <summary>
    /// 換算成小數年份（notes §五公式：Year + DayOfYear/TotalDaysInYear），供時間拉桿/PostGIS
    /// 索引使用。年精度事件的小數年份等於整數年本身（1 月 1 日，對應既有 seed 資料寫法，
    /// 例如 208.000），不是把整年攤平成區間再取平均。
    ///
    /// 閏年判斷與負年份（西元前）的 day-of-year 計算交給 <see cref="CalendarSystem.Iso"/>
    /// （官方支援西元前 9998 年到西元 9999 年，且原始碼明確處理過負數 `%`/`>>` 運算子在 C#
    /// 裡跟正數行為不一致的坑）——這塊刻意不自己刻，task 2.2 決策記錄見 PRD §5。
    /// </summary>
    public decimal ToDecimalYear()
    {
        var date = new LocalDate(Year, Month ?? 1, Day ?? 1, CalendarSystem.Iso);
        var daysInYear = CalendarSystem.Iso.GetDaysInYear(Year);
        return Year + (decimal)(date.DayOfYear - 1) / daysInYear;
    }
}
