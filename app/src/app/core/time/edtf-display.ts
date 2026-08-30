/**
 * 前端 EDTF 顯示格式化（任務 3.10，PRD Story 5「模糊/爭議年份的呈現與查詢」）。**只做
 * 顯示格式化，不做曆法計算**——年份換算成小數（`start_decimal`/`end_decimal`）、閏年
 * 天數這些真正需要曆法引擎的工作，後端已經用 `NodaTime` 算好了（見 `api/Domain/
 * EdtfService.cs`），這裡完全不重做，只解析原始 EDTF 字串本身的語法結構（年-月-日精度、
 * `?`/`~` 不確定標記）給 UI 用。
 *
 * **語法解析規則刻意跟後端 `EdtfService.TryParse()` 保持同一個子集**（`-?YYYY(-MM(-DD)?)?`
 * 加選用的尾綴 `?`/`~`）——不支援 EDTF 完整規格的世紀/年代/季節等（後端本來就沒實作，
 * 見 task 2.2 的停止條件記錄），這裡沒有理由支援後端不支援的語法，兩邊解析器對同一個
 * 字串的判斷結果必須一致，不然會出現「後端接受這個字串、前端卻顯示不出來」的落差。
 */

export type EdtfPrecision = 'year' | 'month' | 'day';
export type EdtfQualifier = 'certain' | 'uncertain' | 'approximate';

export interface ParsedEdtf {
  precision: EdtfPrecision;
  qualifier: EdtfQualifier;
  /** 絕對紀年（EDTF/ISO 8601 慣例：西元 0 年＝西元前 1 年），跟後端 `EdtfDate.Year`
      同一個慣例，不是「西元前年份直接取負號」，見 `formatEdtfYear()` 的換算。 */
  year: number;
  month?: number;
  day?: number;
}

const DATE_PATTERN = /^(?<sign>-)?(?<year>\d{4})(-(?<month>\d{2})(-(?<day>\d{2}))?)?$/;

/** 解析單一 EDTF 日期字串。回傳 `null` 代表不符合這個專案支援的子集——呼叫端（見
    `EdtfDateComponent`）遇到 `null` 時直接顯示原始字串，不是報錯或留空白，畢竟資料庫
    裡的字串本來就是後端 `EdtfService` 驗證過寫進去的，理論上不該解析失敗，這裡只是
    防禦性 fallback。 */
export function parseEdtf(raw: string): ParsedEdtf | null {
  let working = raw;
  let qualifier: EdtfQualifier = 'certain';

  if (working.endsWith('?')) {
    qualifier = 'uncertain';
    working = working.slice(0, -1);
  } else if (working.endsWith('~')) {
    qualifier = 'approximate';
    working = working.slice(0, -1);
  }

  const match = DATE_PATTERN.exec(working);
  if (!match?.groups) {
    return null;
  }

  const year = Number(match.groups['year']) * (match.groups['sign'] ? -1 : 1);
  const month = match.groups['month'] ? Number(match.groups['month']) : undefined;
  const day = match.groups['day'] ? Number(match.groups['day']) : undefined;
  const precision: EdtfPrecision = day !== undefined ? 'day' : month !== undefined ? 'month' : 'year';

  return { precision, qualifier, year, month, day };
}

/** 絕對紀年換算成人類慣用的「西元/西元前」講法——西元 0 年＝西元前 1 年，以此類推
    （跟後端 `EdtfDate`/`NodaTime.CalendarSystem.Iso` 同一個慣例，見該類別的說明）。 */
export function formatEdtfYear(year: number): string {
  return year <= 0 ? `西元前 ${1 - year} 年` : `西元 ${year} 年`;
}

/**
 * AC#1：日期標籤本身只顯示史料實際記載到的精度——年精度就只顯示到年，不會因為程式
 * 內部把月/日補成 1 月 1 日（`ToDecimalYear()` 換算用的預設值，純粹是數學計算需要，
 * 不代表史料真的記載到那個精度）就跟著顯示出「1月1日」這種偽造的精確度。
 */
export function formatEdtfDateLabel(parsed: ParsedEdtf): string {
  const yearLabel = formatEdtfYear(parsed.year);
  if (parsed.precision === 'year') {
    return yearLabel;
  }
  if (parsed.precision === 'month') {
    return `${yearLabel} ${parsed.month} 月`;
  }
  return `${yearLabel} ${parsed.month} 月 ${parsed.day} 日`;
}

/** AC#2：不確定標記的提示文字，`null` 代表沒有標記（一般精確記載的日期），呼叫端據此
    決定要不要額外顯示這段提示。 */
export function formatEdtfQualifierLabel(qualifier: EdtfQualifier): string | null {
  if (qualifier === 'uncertain') {
    return '推測年份';
  }
  if (qualifier === 'approximate') {
    return '約略年份';
  }
  return null;
}
