using System.Text.Json;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/events/{eventId}/perspectives` 的請求形狀（task 2.12）。
///
/// **`RegimeId`／`ObserverCategoryId` 應用層驗證至少擇一非 NULL**（PRD §6 原話），
/// 不是資料庫約束——`RegimeId` 是當事政權視角，`ObserverCategoryId` 是非政權主體
/// （國際第三者、後世史學界等，見 `ObserverCategory`）。兩者不是互斥，只是至少要有
/// 一個知道「這是誰的視角」，本身都有值也允許。
///
/// **`PrimarySources`/`ClaimedCasualties` 的 JSON schema（task 2.12 動工前拍板，
/// §12 TODO）**：這個專案目前唯一的正式史料是既有種子資料（赤壁之戰／漢禪魏／怛羅斯
/// 之戰已有的視角列），沿用那批資料已經在用的形狀當「最小 citation 欄位」定案，不是
/// 憑空另外設計一套：
/// - `primary_sources`：JSON 陣列，每筆 <c>{ "title": "...", "author": "...", "year":
///   數字 }</c>——`title`/`author` 必填，`year` 選填（史料本身可能無法確定成書年份）。
/// - `claimed_casualties`：JSON 物件，鍵名依史料實際記載彈性增減（例如
///   <c>{ "own_loss": "...", "enemy_loss": "..." }</c>），不強制固定欄位——這不是一份
///   「引用清單」，是「這個視角主張的一個數字/敘述」，套用跟 `primary_sources` 同一套
///   citation 欄位沒有意義。
///
/// 刻意不寫程式碼層級的 JSON Schema 驗證（跟 `historical_events.sections` 同一個既有
/// 慣例，見 task 2.10 的說明）——只在這份文件跟種子資料裡建立慣例，不是資料庫/應用層
/// 強制的結構，單人自用階段先求「有一致慣例可以依循」，不是「機器擋掉不符合的格式」。
/// </summary>
public class CreateEventPerspectiveRequest
{
    public Guid? RegimeId { get; init; }
    public int? ObserverCategoryId { get; init; }
    public required string LocalName { get; init; }
    public required string NarrativeSummary { get; init; }
    public string? OfficialJustification { get; init; }
    public JsonElement? PrimarySources { get; init; }
    public JsonElement? ClaimedCasualties { get; init; }
}
