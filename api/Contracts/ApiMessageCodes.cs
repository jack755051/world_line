namespace WorldLine.Api.Contracts;

/// <summary>
/// task 2.0（2026-08-29 修訂）：<see cref="ApiResponse{T}.Message"/> 放這裡定義的穩定代碼，
/// 不是給人看的中文句子——前端拿代碼查自己的翻譯字典決定顯示文字，之後改中文措辭不會動到
/// 前端邏輯，也才能真的做多語系。SCREAMING_SNAKE_CASE，是這個檔案唯一的權威清單，不另外
/// 在文件裡維護一份會漂移的複本。
///
/// 命名原則：成功代碼對應 HTTP 動詞語意（GET→FETCH、POST→CREATE、PATCH→UPDATE）；錯誤代碼
/// 盡量對應到具體違反的欄位/規則（例如 YEAR_REQUIRED），只有框架自動觸發、無法歸因到單一
/// 規則的情況才用通用代碼（VALIDATION_ERROR、NOT_FOUND、INTERNAL_ERROR）。
/// </summary>
public static class ApiMessageCodes
{
    // --- 成功 ---
    public const string FetchSuccess = "FETCH_SUCCESS";
    public const string CreateSuccess = "CREATE_SUCCESS"; // task 2.10：第一個真正落地的 POST 端點

    // --- 通用錯誤（框架自動觸發，或沒有更具體代碼可用時的 fallback） ---
    public const string ValidationError = "VALIDATION_ERROR"; // [ApiController] 自動 model-state 驗證失敗
    public const string NotFound = "NOT_FOUND";
    public const string InternalError = "INTERNAL_ERROR";
    public const string Unauthorized = "UNAUTHORIZED"; // task 2.14：寫入端點缺少/錯誤的 X-API-Key

    // --- 具體錯誤（依端點逐步擴充，見各 controller 使用處） ---
    public const string YearRequired = "YEAR_REQUIRED";
    public const string RegimeNotFound = "REGIME_NOT_FOUND";
    public const string EventNotFound = "EVENT_NOT_FOUND"; // task 2.10
    public const string EventIdAlreadyExists = "EVENT_ID_ALREADY_EXISTS"; // task 2.10：Id 是呼叫端指定的 slug，不是資料庫自動產生，會撞已存在的
    public const string InvalidEdtf = "INVALID_EDTF"; // task 2.10：start_edtf/end_edtf 不符合 EdtfService 支援的子集格式
    public const string EventEndBeforeStart = "EVENT_END_BEFORE_START"; // task 2.10：EdtfService.TryParse 只驗證單一字串合法性，這條是額外補的跨欄位檢查
    public const string ParentEventNotFound = "PARENT_EVENT_NOT_FOUND"; // task 2.10：parent_event_id 指到不存在的事件
    public const string RelationSameRegime = "RELATION_SAME_REGIME"; // task 2.9：regime_a_id 跟 regime_b_id 不能是同一個政權
    public const string RelationOtherRegimeNotFound = "RELATION_OTHER_REGIME_NOT_FOUND"; // task 2.9：關係另一端指到不存在的政權
    public const string RelationEndBeforeStart = "RELATION_END_BEFORE_START"; // task 2.9：valid_period 的結束年份沒有晚於開始年份
    public const string LineagePresetNotFound = "LINEAGE_PRESET_NOT_FOUND"; // task 2.8
}
