using System.Text.Json;

namespace WorldLine.Api.Contracts;

/// <summary>
/// `POST /api/v1/events/{eventId}/controversies` 的請求形狀（task 2.13）。
///
/// **`Viewpoints` 的 JSON schema（task 2.13 動工前拍板，§12 TODO，跟 2.12 併案決定）**
/// ：沿用既有種子資料（曹操兵力爭議／正統性爭議／怛羅斯造紙術傳播爭議）已經在用的
/// 形狀——JSON 陣列，每筆 <c>{ "stance": "...", "source": "..." }</c>：`stance` 是這方
/// 主張的具體內容，`source` 是這個主張依據的史料/推論方式（自由文字，不強制拆成
/// title/author 等結構化欄位——`stance`+`source` 這兩個欄位本身就同時扮演「主張」跟
/// 「最小 citation」，不是另外疊加一層結構化引用清單，見既有種子資料範例）。同一個
/// 爭議點可以有兩個以上的立場（例如三方各自主張的正統性歸屬），不限二元對立。
///
/// 刻意不寫程式碼層級的 JSON Schema 驗證，理由同 `CreateEventPerspectiveRequest` 類別
/// 註解。
/// </summary>
public class CreateEventControversyRequest
{
    public required string Topic { get; init; }
    public required string NeutralDescription { get; init; }
    public JsonElement? Viewpoints { get; init; }
}
