using NetTopologySuite.Geometries;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `PATCH /api/v1/territories/{id}/correct` 的請求形狀（task 2.7，I5 版本鏈）。**要求
/// 完整的新版本內容，不是部分欄位差異**——修正是「用一筆新的正確快照取代舊快照」，不是
/// 「調整舊快照裡的某幾個欄位」，要求呼叫端把完整的正確版本送過來，避免「哪些欄位沿用
/// 舊值、哪些是新值」這種容易搞錯的隱性合併邏輯。`RegimeId` 不可修改——修正是同一筆
/// 疆域紀錄的更新版本，不是把它過戶給別的政權，那是另一個問題（刪掉重建），不是這個
/// 端點的範圍。
/// </summary>
public class CorrectRegimeTerritoryRequest
{
    public required int StartYear { get; init; }
    public required int EndYear { get; init; }
    public required MultiPolygon Geom { get; init; }
    public bool IsDisputed { get; init; }

    /// <summary>I5 要求：修正必須說明原因（`docs/data-governance.md`「填寫 correction
    /// reason、時間與支持來源」）——這裡先只收文字原因本身，「支持來源」屬於 PRD §12
    /// 尚未拍板的 citation/source model，不在這個欄位裡硬塞。</summary>
    public required string CorrectionReason { get; init; }
}
