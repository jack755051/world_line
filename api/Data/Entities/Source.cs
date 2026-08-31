namespace WorldLine.Api.Data.Entities;

/// <summary>
/// PRD §12「source/citation model」TODO——一筆可重複引用的來源紀錄（一份資料集、一本
/// 書、一篇論文⋯），對應 `docs/data-governance.md`「最低來源紀錄」表格前六欄
/// （Title/Author-Publisher/Version-Published-at/Locator/License/Accessed-at）。
/// **刻意不含「Evidence note」**——那一欄在該文件的表格裡雖然跟這六欄放在一起，但語意
/// 是「此來源支持哪個具體結論」，屬於某一次引用的使用情境，不是來源本身的固定屬性：
/// 同一份 CHGIS 資料集可以被十幾筆不同的疆域/事件各自引用，每次引用支持的具體結論
/// 都不一樣，所以 evidence note 放在各自的 `*Citation` join 表上，不放在這裡——不然
/// 同一個 `Source` 列會被迫塞進互相矛盾的多個 evidence note，沒有單一正確答案。
/// </summary>
public class Source
{
    public Guid Id { get; set; }
    public string Title { get; set; } = null!;
    public string? AuthorOrPublisher { get; set; }
    public string? VersionOrPublishedAt { get; set; }
    public string? Locator { get; set; }
    public string? License { get; set; }
    public DateOnly? AccessedAt { get; set; }
    public DateTimeOffset CreatedAt { get; set; }
}
