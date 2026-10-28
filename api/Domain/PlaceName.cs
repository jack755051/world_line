using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>地名雙軌顯示（憲法 §6：古地名為主，括號附現代地名）。</summary>
public class PlaceName
{
    public Guid Id { get; set; }
    /// <summary>例：長安。</summary>
    public string HistoricalName { get; set; } = null!;
    /// <summary>例：西安；古今同名可為 null。</summary>
    public string? ModernName { get; set; }
    /// <summary>
    /// 此地名使用的日期區間（可為 null 表示未考據；有值時必須有上下界與精度）。
    /// ⚠️ 資料庫可存西元前日期，但 .NET DateOnly 無法表示西元前，西元前資料目前不可經 EF 讀出（API 尚無地名端點）。
    /// </summary>
    public NpgsqlRange<DateOnly>? ValidPeriod { get; set; }
    public string? ValidFromPrecision { get; set; }
    public string? ValidToPrecision { get; set; }
    public Point? Geom { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 年號（憲法 §9 多重紀年；PRD §5：自建查詢表，非曆法計算）。
/// 西元年 Y 在此年號下為「era_name + (Y - 起始日的年份 + 1) 年」（元年 = 起始日所在的西元年，例：昭和元年 = 1926）。
/// 改元當年可能同時落在兩個年號，查詢會回傳兩筆。起訖為日期（例：昭和 1926-12-25 起），迄日 null 代表仍在使用或未記錄（例：民國紀年）。
/// </summary>
public class ReignEra
{
    public Guid Id { get; set; }
    public Guid RegimeId { get; set; }
    public Regime Regime { get; set; } = null!;
    /// <summary>例：開元。</summary>
    public string EraName { get; set; } = null!;
    /// <summary>例：唐玄宗（廟號／帝號，可為 null）。</summary>
    public string? MonarchName { get; set; }
    public DateOnly StartDate { get; set; }
    public string StartPrecision { get; set; } = DatePrecision.Day;
    public DateOnly? EndDate { get; set; }
    public string? EndPrecision { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
