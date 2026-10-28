namespace WorldLine.Api.Domain;

/// <summary>史觀主線 preset（方案 D）：把「正式朝代」這種史觀立場從核心政權圖中獨立出來。</summary>
public class LineagePreset
{
    public Guid Id { get; set; }

    /// <summary>例：「傳統教科書史觀」「蜀漢正統論史觀」。唯一。</summary>
    public string PresetName { get; set; } = null!;

    public string? Description { get; set; }

    /// <summary>未指定史觀時使用的預設主線（Story 4）；全表最多一筆為 true。</summary>
    public bool IsDefault { get; set; }

    public DateTimeOffset CreatedAt { get; set; }

    public List<LineagePresetMember> Members { get; set; } = [];
}

public class LineagePresetMember
{
    public Guid PresetId { get; set; }
    public LineagePreset Preset { get; set; } = null!;

    public Guid RegimeId { get; set; }
    public Regime Regime { get; set; } = null!;

    /// <summary>在此 preset 序列中的順序；同一 preset 內唯一。</summary>
    public int SortOrder { get; set; }
}
