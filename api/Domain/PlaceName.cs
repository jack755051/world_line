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
    /// <summary>此地名使用的年份區間（可為 null 表示未考據；有值時必須有上下界）。</summary>
    public NpgsqlRange<int>? ValidPeriod { get; set; }
    public Point? Geom { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}

/// <summary>
/// 年號（憲法 §9 多重紀年；PRD §5：自建查詢表，非曆法計算）。
/// 西元年 Y 在此年號下為「era_name + (Y - start_year + 1) 年」（元年 = start_year）。
/// 改元當年可能同時落在兩個年號，查詢會回傳兩筆。
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
    public int StartYear { get; set; }
    public int EndYear { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
