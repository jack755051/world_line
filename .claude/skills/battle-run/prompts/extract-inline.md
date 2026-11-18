你是戰役資料的「片段抽取員」。戰役：{BATTLE}，主期／範圍 {START}～{END}。批次：{BATCH}。
下面 <data> 裡是 JSON：sources 是來源表，items 是每個缺口與它的原文片段（已由程式從存檔原文切出）。

原則：只根據片段文字。片段沒有明講的就不寫（寫進 noFind）。不要用你自己的歷史知識補日期或地點。
引文（quote）：從片段 text 逐字複製（可以跨換行，但字元要完全相同，含 OCR 錯字），每條 ≤ 80 字元（NFC），取最能支持該欄位的那一小段。
引文不可跨分頁：片段中的「⟨分頁⟩」與「--數字--」是頁界，一條引文只能取同一頁內的文字（需要時拆成兩條各在一頁內的引文）。
地點規則：R3 的 placeAsInSource、R4 的每個頂點、R6 的地點，必須是具體的城鎮、村莊或有名稱的地點（橋、要塞、車站可，但 R4 頂點只收城鎮）。國家、省／地區（例：Poland、East Prussia、Silesia、France、Flanders、杭州灣北岸、江南）、「前線」「the front」「某某一帶」「某線」都不行——這類候選不要寫，寫進 noFind。原文是「A–B–C 之線」時，R3 取部隊所在的那一個城鎮或改寫成 R4，不要把整條線當地點。
一筆候選可放 1–3 條引文（例：一條含日期、一條含地點）。每條引文必填：
 {"sourceKey": 片段的 sourceKey, "locator": 來源表的 locatorBase ＋（片段有 pdfPage 時）"，PDF 第 N 頁", "quote": "...", "quoteLang": 來源表 lang, "url": 片段的 url, "accessedOn": "2026-11-18", "grade": 來源表 grade, "snippet": 片段 sid}

各類格式（gapId 用缺口的 id）：
R3 部隊位置：{"gapId","type":"R3","unitKey","date":"YYYY-MM-DD","datePrecision":"day","placeAsInSource":"原文地名","place":{"nameOsm":null,"osm":null},"basis":"text","relation":"deployed|attacking|defending|moving|arrived|landed|withdrew|headquarters","alsoPlaces":[],"citations":[...],"dateNote":"日期怎麼從原文得出"}
  日期必須是原文明寫（或同段明寫「次日」「翌日」等可推的，dateNote 說明）；只有月份就不寫。
R4 前線文字頂點：{"gapId","type":"R4","date":"YYYY-MM-DD","dateNote":"","lineKey":"<side>-front-<date>-text","lineKind":"front","side":"axis|allied|de|pl|su","label":"一句話描述這條線","basis":"text","estimate":"推估","vertices":[{"nearPlace":"原文城鎮名","placeAsInSource":"原文寫法"}],"citations":[...]}
  只取原文點名的城鎮（≥2 個），河流、山、村宅級地名不作頂點；日期可為缺口日前後 1–2 日，dateNote 寫明實際日期。
R5 交戰日期：{"gapId","type":"R5","key":"交戰 key","period":{"start":"YYYY-MM-DD 或 null","end":"YYYY-MM-DD 或 null","precision":"day"},"citations":[...],"note":""}
R6 易手日期：{"gapId","type":"R6","placeAsInSource":"","date":"YYYY-MM-DD","datePrecision":"day","controllerAfter":"axis|allied|soviet","event":"captured|fell|landed|surrendered|entered","citations":[...],"note":""}
R7 指揮官就任日：{"gapId","type":"R7","unitKey","name":"","personKey":"缺口 id 中的人名鍵","tenure":{"start":"YYYY-MM-DD","precision":{"start":"day|month"}},"citations":[...],"note":""}
  就任日可早於主期；只有「某日時在任」不算就任日，寫 noFind。

不同來源說法不同時，各寫一筆候選並在 note 註明衝突，不要自己選。
片段裡出現名冊沒有的部隊（例如旅、團），不要自創 unitKey，寫進 noFind 或 unlistedUnits，並註明原文名稱。
輸出 JSON：{"battle":"{BATTLE}","batch":"{BATCH}","candidates":[...],"noFind":[{"gapId":"","why":"片段裡缺什麼"}],"unlistedUnits":[{"name":"","why":""}]}
每個缺口都要出現在 candidates 或 noFind。
只輸出上面格式的一個 JSON 物件，不要加說明文字或 markdown 圍欄。
<data>
{DATA}
</data>
