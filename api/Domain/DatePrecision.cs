namespace WorldLine.Api.Domain;

/// <summary>
/// 時間精度（憲法 §9、I7：所有時間資料都必須標示精度，不可把只知年或月的資料呈現為精確日期）。
/// 期間一律存成 PostgreSQL daterange（含頭含尾的日期，DB 正規化為 [起, 迄+1)）；
/// 精度為 year 時起日必為 1/1、迄日必為 12/31；month 時起日必為 1 號、迄日必為月底（DB CHECK 驗證）。
/// </summary>
public static class DatePrecision
{
    public const string Year = "year";
    public const string Month = "month";
    public const string Day = "day";

    public static readonly IReadOnlyList<string> All = [Year, Month, Day];
}
