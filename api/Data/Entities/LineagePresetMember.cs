namespace WorldLine.Api.Data.Entities;

/// <summary>
/// Join row — a regime's ordered position within one lineage preset. Composite PK
/// (PresetId, RegimeId), no separate id column (matches PRD §6 SQL).
/// </summary>
public class LineagePresetMember
{
    public Guid PresetId { get; set; }
    public Guid RegimeId { get; set; }
    public int SortOrder { get; set; }
}
