# B3 full v3 batch085：加強搜尋重跑（Sonnet，新 session，勿 --resume）

授權：Tai 2026-11-11 22:02（未達最低標準者自動加強搜尋重跑一次；不寫庫、不 push、不 commit）。分支 feature/battle-demo-v2（不要切換分支）。

`data/seed/leaders/b3-trial/full/v3/batch085/research.json` 已由上一個 session 產出，但下列人物未達最低標準（中文 ≥3 段、合計 ≥300 字、每個職位有起迄日；見 `data/seed/leaders/b3-trial/full/v3/batch085/min-check.round1.json`）：
- 艾莫·卡揚德爾｜Aimo Kaarlo Cajander｜01a1b512-33a3-7a04-ab6b-8f41cadbc0ec｜republic-of-finland｜首任 1922-06-02｜中（離線推定）｜republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1922-06-02～1922-11-14（recordId 01a1aa4a-4c33-7fdd-84d5-7cb7ab8b6dc2）；republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1924-01-18～1924-05-31（recordId 01a1aa4a-4c34-73f2-952a-e985110c2284）；republic-of-finland head_of_government「Pääministeri / Senaatin (vara)puheenjohtaja（政府首腦）」1937-03-12～1939-12-01（recordId 01a1aa4a-4c35-7c88-868b-85337882db25）
- 雷菲克·塞達姆｜İbrahim Refik Saydam｜01a1b492-3f48-774e-8715-ef76bb35545d｜republic-of-turkey｜首任 1939-01-25｜中（離線推定）｜republic-of-turkey head_of_government「İcra Vekilleri Heyeti Reisi / Başvekil」1939-01-25～1939-04-03（recordId 01a1aa4a-66ab-7715-8733-12aca435ab9d）；republic-of-turkey head_of_government「İcra Vekilleri Heyeti Reisi / Başvekil」1939-04-03～1942-07-08（recordId 01a1aa4a-66ab-7adf-9e97-0d2d96d78975）
- 弗蘭斯·斯霍拉爾特｜Frans Schollaert｜01a1b512-33bd-7b65-afe6-7d78052ae411｜kingdom-of-belgium｜首任 1908-01-09｜薄（離線推定）｜kingdom-of-belgium head_of_government「Chef de cabinet（1918 前無 Premier 正式職稱）」1908-01-09～1911-06-17（recordId 01a1aa4a-59d2-768c-9043-0ecb3c455e40）

## 規則
- 完整規則見 `data/seed/leaders/b3-trial/full/v3/PROMPT_research.md`（以 `085`、`/Users/jack755051/wl-source-cache/b3full-v3/batch085/raw`、`data/seed/leaders/b3-trial/full/v3/batch085` 代入），全部照舊適用；先讀它與現有 research.json、searchLog。
- **只改上列人物**在 research.json 的條目（paragraphs／positions／roleCandidates／gaps／searchLog／sources 新增）；其他人一律不動。raw 存到 `/Users/jack755051/wl-source-cache/b3full-v3/batch085/raw`。
- **加強搜尋量（本 session 每人新增）**：至少 5 種來源類型、至少 15 次查詢（原文語言至少 4 次）、至少實際 curl 抓取 6 個新候選頁；searchLog 新增筆標 `"round": "retry"`。
- **優先改查 A 級來源**：英國人物查 UK Parliament Historic Hansard 人物頁（api.parliament.uk/historic-hansard/people/…）、London Gazette、GOV.UK；其他國家查國家級傳記辭典與議會／政府名錄，例如：Deutsche Biographie（NDB/ADB）、ÖBL、Treccani DBI、RAH DB~e、Nouvelle Biographie Nationale／Biographie nationale（Académie royale de Belgique）、Kansallisbiografia（Finland）、Svenskt biografiskt lexikon、Norsk biografisk leksikon、Dansk Biografisk Leksikon（lex.dk）、Alþingi 議員名錄（althingi.is）、Srpski biografski rečnik（Matica srpska）、Hrvatski biografski leksikon、Polski Słownik Biograficzny、Biografický slovník českých zemí、Magyar életrajzi lexikon／Országgyűlés 名錄、Dicționarul … ／Academia Română、Encyclopedia of Ukraine（CIUS，B）、各國總統府／國會歷任名錄、國家圖書館權威檔。可抓原文才可當出處（grade A／B），否則只能放 candidateCitations。
- 不可用無出處內容湊字數；每個事實子句都要有 citation。
- 補完後仍未達標 → 該人加（或更新）gap：target=`paragraph:length`、gapKind=not_found、note 以「篇幅不足：」開頭，寫目前段數／字數與本輪已查來源類型。缺任期者照「待查證：缺迄日／缺起日」規則寫 gap。
- 完成後跑 `python3 -I data/seed/leaders/b3-trial/verify.py data/seed/leaders/b3-trial/full/v3/batch085/research.json --report data/seed/leaders/b3-trial/full/v3/batch085/verify-report.json`，須 exit 0。
- 結尾回覆：每人新增段落／字數／任期補到幾筆、新增 searchLog 筆數、用到的新網域；最後單獨一行 `BATCH_RESULT=ok` 或 `BATCH_RESULT=fail`。不要 commit。


## 2026-11-15 追加（主 session；優先於上文）
- 現行來源規則（docs/source-rules.md）：禁用網域只看 data/source-policy.json（含 bannedHostLabels 與例外）；Wikipedia／Wikidata／任何 wiki 類（含 ruwiki、bre.ruwiki.ru）只當索引；第三方轉錄本原件 A 記 B；人物生平只收 A／B（C 只能放 gaps 候選）；個人網站與私人彙編（如 rulers.org、archontology.org、nepalresearch.com）是 X；合格出處與不合格出處不同時以合格出處為準，兩個合格出處不同才是說法衝突。
- 不繞過任何機器人驗證（Cloudflare、Anubis、403 一律放棄並記入 searchLog）；不用 Wayback 取代被擋頁面。
- 目前工作目錄在分支 feature/battle-demo-v2，另一個 session 也在此目錄工作：只寫你的 OUTDIR 與 RAWDIR；不 git add／commit／push；不寫庫；不呼叫 5052 API。
