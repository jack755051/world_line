using NetTopologySuite.Geometries;
using NpgsqlTypes;

namespace WorldLine.Api.Domain;

/// <summary>
/// 政權疆域版本記錄。
/// I1：時間區間必填（有上下界、非空）。I3：同政權、同時間不可有兩筆「現行且非爭議」的正式版本。
/// I5：修正時新增一筆新版本，舊版本以 SupersededBy 指向新版本並記錄原因與時間，不覆蓋、不刪除。
/// </summary>
public class RegimeTerritory
{
    public Guid Id { get; set; }

    public Guid RegimeId { get; set; }
    public Regime Regime { get; set; } = null!;

    /// <summary>西元年區間（負數為西元前），例：[618,907]。</summary>
    public NpgsqlRange<int> ValidPeriod { get; set; }

    public MultiPolygon Geom { get; set; } = null!;

    /// <summary>I3：明確標記為爭議並存時，允許與正式版本時間重疊。</summary>
    public bool IsDisputed { get; set; }

    /// <summary>是否為粗略示意多邊形（非史料考據），前端應明確標示「示意」。</summary>
    public bool IsIllustrative { get; set; }

    /// <summary>資料來源／說明（例：OpenHistoricalMap 版本、文獻、或「示意多邊形」）。</summary>
    public string? Source { get; set; }

    /// <summary>I5：指向修正後的新版本；null 代表目前現行版本。</summary>
    public Guid? SupersededBy { get; set; }
    public RegimeTerritory? SupersededByTerritory { get; set; }

    public string? CorrectionReason { get; set; }
    public DateTimeOffset? CorrectedAt { get; set; }

    public DateTimeOffset CreatedAt { get; set; }
    public int Version { get; set; }
}
