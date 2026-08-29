namespace WorldLine.Api.Data.Entities;

/// <summary>
/// 通用內容翻譯對照表（憲法 R4，PRD §6「多語言內容設計」）。只用來翻譯「中立事實內容」
/// （政權自稱名稱、他稱代稱、事件名稱、史觀 preset 名稱/說明、爭議點中立描述），立場性敘事
/// （historical_event_perspectives、viewpoints）不進這張表，靠既有多重視角機制各自用原語言寫
/// （見 PRD §6 核心設計原則）。
///
/// EntityId 統一存字串——大多數父表是 UUID 主鍵（轉字串存），`historical_events.id` 本身就是
/// 字串 slug。EntityType 決定 EntityId 指向哪張表，沒有真正的資料庫外鍵約束（polymorphic
/// association 是關聯式資料庫的已知取捨），父表資料被刪除時孤兒翻譯列的清理留給應用層處理。
/// </summary>
public class ContentTranslation
{
    public Guid Id { get; set; }
    public string EntityType { get; set; } = null!;
    public string EntityId { get; set; } = null!;
    public string FieldName { get; set; } = null!;
    public string Locale { get; set; } = null!;
    public string TranslatedText { get; set; } = null!;
    public DateTimeOffset CreatedAt { get; set; }
}
