/**
 * `ApiResponse.message` 代碼→中文顯示文字對照字典（任務 3.14a）。task 2.0 修訂後
 * `message` 回傳的是穩定代碼（例如 `YEAR_REQUIRED`），不是給人看的中文句子，前端要
 * 有一個集中的地方把代碼轉成顯示文字，不能讓各元件各自寫 `if (message === 'XXX')`
 * 散落各處——目前這個專案完全沒有任何 UI 會顯示 API 錯誤訊息（HTTP 失敗一律
 * `console.error` 帶過，見各元件的既有慣例），這個檔案先把「代碼→文字」的對照集中
 * 建好，之後真的要在畫面上顯示錯誤訊息時，呼叫端直接用 `messageCodeToText()`，不用
 * 重新設計這一層。
 *
 * **權威來源是後端 `api/Contracts/ApiMessageCodes.cs`**——這裡的代碼字串是手動抄過來
 * 的（TS 沒辦法直接 import C# 常數），新增/刪除代碼時要記得同步更新這份字典，避免
 * 前後端代碼集合漂移。分組方式（成功/通用錯誤/具體錯誤）也刻意對齊那份檔案的分組，
 * 方便日後對照。
 *
 * **字典結構跟查詢邏輯分開**（`API_MESSAGE_CODE_TEXT` 純資料 vs. `messageCodeToText()`
 * 查詢函式）：現階段只需要中文一種語言（多語系不是已拍板的產品目標，見 PRD §7），但
 * 呼叫端一律透過 `messageCodeToText()` 取得顯示文字，不直接索引這個物件——之後真的
 * 要加語言，只需要把這個物件換成依 locale 查表的結構，不用回頭改任何呼叫端程式碼。
 */
export const API_MESSAGE_CODE_TEXT: Readonly<Record<string, string>> = {
  // --- 成功 ---
  FETCH_SUCCESS: '查詢成功',
  CREATE_SUCCESS: '新增成功',

  // --- 通用錯誤（框架自動觸發，或沒有更具體代碼可用時的 fallback） ---
  VALIDATION_ERROR: '送出的資料格式不正確',
  NOT_FOUND: '找不到指定的資源',
  INTERNAL_ERROR: '系統發生錯誤，請稍後再試',
  UNAUTHORIZED: '未授權的操作',

  // --- 具體錯誤 ---
  YEAR_REQUIRED: '缺少年份參數',
  REGIME_NOT_FOUND: '找不到指定的政權',
  EVENT_NOT_FOUND: '找不到指定的事件',
  EVENT_ID_ALREADY_EXISTS: '這個事件 ID 已經存在',
  INVALID_EDTF: '日期格式不正確',
  EVENT_END_BEFORE_START: '結束時間不能早於開始時間',
  PARENT_EVENT_NOT_FOUND: '找不到指定的父事件',
  RELATION_SAME_REGIME: '關係的兩端不能是同一個政權',
  RELATION_OTHER_REGIME_NOT_FOUND: '找不到關係另一端的政權',
  RELATION_END_BEFORE_START: '結束年份必須晚於開始年份',
  LINEAGE_PRESET_NOT_FOUND: '找不到指定的史觀主線',
  OBSERVER_REGIME_NOT_FOUND: '找不到指定的代稱來源政權',
  INVALID_ALIAS_TYPE: '代稱類型不是合法的受控值',
  PERSPECTIVE_PARTY_REQUIRED: '視角至少要指定政權或觀察者類別其中一項',
  OBSERVER_CATEGORY_NOT_FOUND: '找不到指定的觀察者類別',
};

/** 查無對照的代碼時直接回傳原始代碼字串，不是空字串或泛用「發生錯誤」——後端加了新
    代碼但這份字典還沒同步更新時，畫面上至少看得到原始代碼可以查，比完全看不出是
    什麼問題更容易除錯，跟這個專案別處「查無資料時 fallback 顯示原始值」（例如
    `RegimeDirectoryService.nameOf()` 查無名稱時 fallback 回 regimeId）同一個原則。 */
export function messageCodeToText(code: string): string {
  return API_MESSAGE_CODE_TEXT[code] ?? code;
}
