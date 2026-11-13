using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Common;

/// <summary>
/// 可信程度（docs/source-rules.md §5）：讀檢視 v_record_confidence，由出處即時推導，不自己在程式裡另算一套。
/// 已查證＝一筆 A 級出處，或兩個獨立家族的 B 級出處；有引文但來源未評等或不到門檻＝待查證；沒有出處＝查無。
/// API 的 verification 只分 verified／pending：待查證與查無都回 pending（查無時引文清單是空的）。
/// </summary>
public static class RecordConfidence
{
    public const string Event = "event";
    public const string LeaderRecord = "leader_record";

    /// <summary>ids 之中可信程度為 verified 的那些。</summary>
    public static async Task<HashSet<Guid>> VerifiedIdsAsync(WorldLineDbContext db, string kind, IReadOnlyCollection<Guid> ids, CancellationToken ct)
    {
        if (ids.Count == 0) return [];
        var arr = ids.ToArray();
        var rows = await db.Database
            .SqlQuery<Guid>($"""SELECT record_id AS "Value" FROM v_record_confidence WHERE record_kind = {kind} AND confidence = 'verified' AND record_id = ANY({arr})""")
            .ToListAsync(ct);
        return [.. rows];
    }
}
