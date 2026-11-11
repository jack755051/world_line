# 一戰／二戰主要參戰國將領名單（roster，僅索引）

產出時間：2026-11-11（Asia/Taipei）。由 `build_roster.py` 產生；本檔、`roster.json`、`index_pages.json` 皆為腳本輸出。

## 1. 方法、限制與聲明

- **維基列表／分類頁只當索引，不是出處。** 每筆 `source_status="index_only"`，未以 A/B 來源查證，不得直接當作生平事實使用。
- Tai 22:51 增列索引頁 [第二次世界大戰各國指揮官列表](https://zh.wikipedia.org/zh-tw/%E7%AC%AC%E4%BA%8C%E6%AC%A1%E4%B8%96%E7%95%8C%E5%A4%A7%E6%88%B0%E5%90%84%E5%9C%8B%E6%8C%87%E6%8F%AE%E5%AE%98%E5%88%97%E8%A1%A8)：只取「军队指挥官」節之姓名欄（含 {{tsl}} 模板），戰役欄不收入。該頁各國將領至少 A，最高軍階（元帥／五星上將／特級上將等）升 S；與 fame_tiers 取較高者，不降級。純政治人物仍排除。中文維基沒有對應的「第一次世界大戰各國指揮官列表」，一戰未用同類名單頁補（英文 Allied leaders of World War I、Leaders of the Central Powers of World War I 是元首與將領混編，不當對應頁）。
- 抓取：MediaWiki API（`/w/api.php`），UA `WorldLineGeneralsRoster/0.1 (local research index; not a crawler of article prose)`，限速約 1.2 秒／請求、429 退避重試；未用 `curl -k`、未登入。原則上不抓個人傳記頁；Tai 23:11 例外：伊塔洛·巴爾博（Italo Balbo）的個人頁只取標題與 langlinks 當索引，不用正文當出處。
- 資料來源三類：(1) zh.wikipedia 列表頁（解析 wikitext 的列表／表格列，取每列第一個人名連結；德國起點 `德国大将` 在內）；(2) 分類頁成員（en 為主、經 langlinks 取中文標題；zh 分類取成員標題）；(3) 少數明示的個人頁（只取標題／langlinks）。zh 列表人名再以頁面標題／langlink 元資料解析成英文標題以便合併（只用標題元資料，不讀傳記內文）。Tai 23:11：原失敗 3 頁（`德國海軍元帥`、`德意志帝国海军将领`、`意大利元帅`）失敗結果不入 cache，每次重跑都會再打 API；若仍 missingtitle，另採現存對應頁 `Category:纳粹德国海军将领`、`Category:義大利元帥`、`Marshal of Italy`（帝國海軍將領主力仍由已採用的英文 admirals 分類覆蓋）。「蓋詩」確認為戈特（John Vereker, 6th Viscount Gort），已是 S，未改級。「董宗文」為筆誤，未列入任何清單；董其武維持 B。
- 合併鍵：英文標題正規化（去重音、去括號消歧）；僅有中文者用中文標題。同人跨多頁已合併，`index_urls` 列全部。
- **完整度聲明：本名單是「所採用之列表／分類頁上的將級人物索引」，不是全世界將官普查。** 分類頁對准將／少將不保證完整（例如未採用美國海軍陸戰隊、法國空軍、德國 Waffen-SS 專類、蘇聯一般將官等分類）；不宣稱收齊任何國家的准將／少將。
- **時期說明：** `window_status=category_scoped`（所在分類／列表已限 WWI/WWII 或 1908–1945 將級頁）共 4489 人；`unverified`（分類時期未限定，例如「Italian generals」「Imperial Russian Army generals」「Royal Air Force air marshals」「Warlords from the Republic of China」）共 3234 人，這些人可能完全在窗外（列表看不出者依規定仍列入，`war` 多為待查證），**進入生平階段前建議先人工篩一遍 unverified**。
- `branch` 使用英文枚舉：army / navy / air_force / unknown（全檔一致；unknown＝列表未標示軍種，含警察／黨衛軍／混合列表）。`highest_rank` 多數分類只能看出「將官」類別，無具體軍階時為「待查證」；有明確頁面軍階的（元帥、大將、一級上將、五星上將）才填。
- 排除（腳本規則）：
  - 列表所見卒年早於 1908：40 筆（例：马克西米利安·冯·魏克斯、普魯士的腓特烈·卡爾、卡爾·馮·比滕費爾德、卡尔·腓特烈·冯·史泰因梅茨、老赫尔穆特·冯·毛奇、阿爾布雷希特·馮·羅恩）
  - 非人物頁（List／Template）：27 筆（例：List of commanders of the British 1st Armoured Division、List of Royal Navy flag officers who died during the First World War、First marshal of the empire、List of Imperial Japanese Navy admirals、List of Japanese naval commanders、List of warlords and military cliques in the Warlord Era）
  - 外國君主／榮譽元帥（不當該國將領）：6 筆（例：Franz Joseph I、George V、Constantine I of Greece、Ferdinand I of Bulgaria、Mehmed V、George V）
  - 純政治人物：5 筆（例：Benito Mussolini、Joseph Stalin、Joseph Stalin、Benito Mussolini、Heinrich Himmler）
  - 晉升年早於 1895 之普魯士／帝國元帥（窗外）：3 筆（例：腓特烈三世、阿爾貝特、格奧爾格）
  - 純政治人物以固定清單排除（邱吉爾、希特勒、墨索里尼、希姆萊、戈培爾、海德里希、史達林）；僅在索引上看到才有實際排除。
  - 窗外判斷只用列表上明示的卒年（< 1908）與德意志帝國元帥列表的晉升年；其餘看不出者仍列入。

### 採用的列表／分類頁（完整明細見 `index_pages.json`）

成功 133 頁；失敗 3 頁。

| 頁面 | 語言 | 類型 | 國家／政權 | 軍種 | 取得筆數 |
|---|---|---|---|---|---|
| ✅ 德国大将 | zh | zhlist | 德國 | army | 155 |
| ✅ 德国陆军元帅列表 | zh | zhlist | 德國 | army | 67 |
| ✅ Category:German Army generals of World War I | en | cat | 德國 | army | 148 |
| ✅ Category:German Army generals of World War II | en | cat | 德國 | army | 509 |
| ✅ Category:Luftwaffe World War II generals | en | cat | 德國 | air_force | 146 |
| ✅ Category:Kriegsmarine admirals | en | cat | 德國 | navy | 3 |
| ✅ Category:Admirals of the Kriegsmarine | en | cat | 德國 | navy | 18 |
| ✅ Category:Counter admirals of the Kriegsmarine | en | cat | 德國 | navy | 20 |
| ✅ Category:General admirals of the Kriegsmarine | en | cat | 德國 | navy | 11 |
| ✅ Category:Grand admirals of the Kriegsmarine | en | cat | 德國 | navy | 2 |
| ✅ Category:Vice admirals of the Kriegsmarine | en | cat | 德國 | navy | 29 |
| ✅ Category:Field marshals of Nazi Germany | en | cat | 德國 | army | 1 |
| ✅ Category:British Army generals of World War I | en | cat | 英國 | army | 596 |
| ✅ Category:British Army generals of World War II | en | cat | 英國 | army | 371 |
| ✅ Category:Royal Navy admirals of World War I | en | cat | 英國 | navy | 131 |
| ✅ Category:Royal Navy admirals of World War II | en | cat | 英國 | navy | 143 |
| ✅ Category:Royal Air Force air marshals of World War II | en | cat | 英國 | air_force | 97 |
| ✅ Category:Royal Air Force air marshals | en | cat | 英國 | air_force | 171 |
| ✅ Category:French Army generals of World War I | en | cat | 法國 | army | 114 |
| ✅ Category:French Army generals of World War II | en | cat | 法國 | army | 58 |
| ✅ Category:French Navy admirals | en | cat | 法國 | navy | 238 |
| ✅ 意大利陆军元帅 | zh | zhlist | 義大利 | army | 13 |
| ✅ Category:Field marshals of Italy | en | cat | 義大利 | army | 16 |
| ✅ Category:Italian Army generals | en | cat | 義大利 | army | 339 |
| ✅ Category:Italian Air Force generals | en | cat | 義大利 | air_force | 43 |
| ✅ Category:Italian admirals | en | cat | 義大利 | navy | 151 |
| ✅ Category:Italian generals | en | cat | 義大利 | army | 34 |
| ✅ Category:United States Army generals of World War I | en | cat | 美國 | army | 432 |
| ✅ Category:United States Army generals of World War II | en | cat | 美國 | army | 564 |
| ✅ Category:United States Army Air Forces generals | en | cat | 美國 | air_force | 98 |
| ✅ Category:United States Navy World War I admirals | en | cat | 美國 | navy | 43 |
| ✅ Category:United States Navy World War II admirals | en | cat | 美國 | navy | 237 |
| ✅ Category:美国五星上将 | zh | cat | 美國 | unknown | 2 |
| ✅ Category:美国陆军五星上将 | zh | cat | 美國 | army | 4 |
| ✅ 日本陆军大将列表 | zh | zhlist | 日本 | army | 134 |
| ✅ 日本元帅 | zh | zhlist | 日本 | army | 31 |
| ✅ Category:Imperial Japanese Navy admirals | en | cat | 日本 | navy | 132 |
| ✅ Category:Imperial Japanese Navy marshal admirals | en | cat | 日本 | navy | 15 |
| ✅ Category:Japanese admirals of World War II | en | cat | 日本 | navy | 108 |
| ✅ Category:Japanese generals | en | cat | 日本 | army | 96 |
| ✅ Category:Marshals of Japan | en | cat | 日本 | unknown | 21 |
| ✅ Category:中華民國陸軍一級上將 | zh | cat | 中華民國-國民政府 | army | 39 |
| ✅ Category:国民革命军将领 | zh | cat | 中華民國-國民政府 | army | 277 |
| ✅ Category:中国远征军将领 | zh | cat | 中華民國-國民政府 | army | 12 |
| ✅ Category:National Revolutionary Army generals | en | cat | 中華民國-國民政府 | army | 6 |
| ✅ Category:National Revolutionary Army generals from Anhui | en | cat | 中華民國-國民政府 | army | 8 |
| ✅ Category:Chinese Expeditionary Force generals | en | cat | 中華民國-國民政府 | army | 9 |
| ✅ Category:National Revolutionary Army generals from Fujian | en | cat | 中華民國-國民政府 | army | 5 |
| ✅ Category:National Revolutionary Army generals from Gansu | en | cat | 中華民國-國民政府 | army | 25 |
| ✅ Category:National Revolutionary Army generals from Guangdong | en | cat | 中華民國-國民政府 | army | 22 |
| ✅ Category:National Revolutionary Army generals from Guangxi | en | cat | 中華民國-國民政府 | army | 9 |
| ✅ Category:National Revolutionary Army generals from Guizhou | en | cat | 中華民國-國民政府 | army | 1 |
| ✅ Category:National Revolutionary Army generals from Hebei | en | cat | 中華民國-國民政府 | army | 13 |
| ✅ Category:National Revolutionary Army generals from Heilongjiang | en | cat | 中華民國-國民政府 | army | 1 |
| ✅ Category:National Revolutionary Army generals from Henan | en | cat | 中華民國-國民政府 | army | 7 |
| ✅ Category:National Revolutionary Army generals from Hubei | en | cat | 中華民國-國民政府 | army | 6 |
| ✅ Category:National Revolutionary Army generals from Hunan | en | cat | 中華民國-國民政府 | army | 26 |
| ✅ Category:National Revolutionary Army generals from Inner Mongolia | en | cat | 中華民國-國民政府 | army | 1 |
| ✅ Category:National Revolutionary Army generals from Jiangsu | en | cat | 中華民國-國民政府 | army | 11 |
| ✅ Category:National Revolutionary Army generals from Jiangxi | en | cat | 中華民國-國民政府 | army | 9 |
| ✅ Category:National Revolutionary Army generals from Jilin | en | cat | 中華民國-國民政府 | army | 4 |
| ✅ Category:National Revolutionary Army generals from Liaoning | en | cat | 中華民國-國民政府 | army | 11 |
| ✅ Category:National Revolutionary Army generals from Qinghai | en | cat | 中華民國-國民政府 | army | 3 |
| ✅ Category:National Revolutionary Army generals from Shaanxi | en | cat | 中華民國-國民政府 | army | 12 |
| ✅ Category:National Revolutionary Army generals from Shandong | en | cat | 中華民國-國民政府 | army | 16 |
| ✅ Category:National Revolutionary Army generals from Shanxi | en | cat | 中華民國-國民政府 | army | 8 |
| ✅ Category:National Revolutionary Army generals from Sichuan | en | cat | 中華民國-國民政府 | army | 16 |
| ✅ Category:National Revolutionary Army generals from Tianjin | en | cat | 中華民國-國民政府 | army | 2 |
| ✅ Category:National Revolutionary Army generals from Xinjiang | en | cat | 中華民國-國民政府 | army | 1 |
| ✅ Category:National Revolutionary Army generals from Yunnan | en | cat | 中華民國-國民政府 | army | 7 |
| ✅ Category:National Revolutionary Army generals from Zhejiang | en | cat | 中華民國-國民政府 | army | 8 |
| ✅ Category:Republic of China Army generals | en | cat | 中華民國-國民政府 | army | 51 |
| ✅ Category:Warlords from the Republic of China (1912–1949) | en | cat | 中華民國-北洋 | army | 9 |
| ✅ Category:Beiyang Army personnel | en | cat | 中華民國-北洋 | army | 6 |
| ✅ Category:中华人民共和国元帅 | zh | cat | 中國共產黨 | army | 11 |
| ✅ Category:中国人民解放军大将 | zh | cat | 中國共產黨 | army | 12 |
| ✅ Category:八路军将领 | zh | cat | 中國共產黨 | army | 128 |
| ✅ Category:新四军将领 | zh | cat | 中國共產黨 | army | 68 |
| ✅ 苏联元帅 | zh | zhlist | 蘇聯 | army | 43 |
| ✅ Category:Marshals of the Soviet Union | en | cat | 蘇聯 | army | 43 |
| ✅ Category:Soviet marshals of the branch | en | cat | 蘇聯 | army | 2 |
| ✅ Category:Soviet admirals | en | cat | 蘇聯 | navy | 75 |
| ✅ Category:Admirals of the Fleet of the Soviet Union | en | cat | 蘇聯 | navy | 4 |
| ✅ Category:Soviet vice admirals | en | cat | 蘇聯 | navy | 6 |
| ✅ Category:Imperial Russian Army generals | en | cat | 俄羅斯帝國 | army | 447 |
| ✅ Category:Generals of the artillery (Russian Empire) | en | cat | 俄羅斯帝國 | army | 8 |
| ✅ Category:Generals of the cavalry (Russian Empire) | en | cat | 俄羅斯帝國 | army | 19 |
| ✅ Category:Generals of the infantry (Russian Empire) | en | cat | 俄羅斯帝國 | army | 48 |
| ✅ Category:Imperial Russian Navy admirals | en | cat | 俄羅斯帝國 | navy | 130 |
| ✅ Category:Austro-Hungarian generals | en | cat | 奧匈帝國 | army | 91 |
| ✅ Category:Austro-Hungarian admirals | en | cat | 奧匈帝國 | navy | 16 |
| ✅ Category:Ottoman Army generals | en | cat | 鄂圖曼帝國 | army | 65 |
| ✅ Category:Polish generals of the Second Polish Republic | en | cat | 波蘭 | army | 24 |
| ✅ Category:Polish Air Force generals | en | cat | 波蘭 | air_force | 5 |
| ✅ Category:Romanian generals | en | cat | 羅馬尼亞 | army | 17 |
| ✅ Category:Romanian Army World War I generals | en | cat | 羅馬尼亞 | army | 35 |
| ✅ Category:Romanian Air Force generals | en | cat | 羅馬尼亞 | air_force | 8 |
| ✅ Category:Finnish generals | en | cat | 芬蘭 | army | 43 |
| ✅ Category:Field marshals of Finland | en | cat | 芬蘭 | army | 3 |
| ✅ Category:Finnish lieutenant generals | en | cat | 芬蘭 | army | 18 |
| ✅ Category:Finnish major generals | en | cat | 芬蘭 | army | 13 |
| ✅ Category:Canadian generals | en | cat | 加拿大 | army | 76 |
| ✅ Category:Australian generals | en | cat | 澳洲 | army | 241 |
| ✅ Category:British field marshals | en | cat | 英國 | army | 130 |
| ✅ Category:Field marshals of the United Kingdom | en | cat | 英國 | army | 0 |
| ✅ Category:Marshals of the Royal Air Force | en | cat | 英國 | air_force | 28 |
| ✅ Category:Admirals of the Fleet of the Royal Navy | en | cat | 英國 | navy | 0 |
| ✅ Category:Admirals of the Fleet (Royal Navy) | en | cat | 英國 | navy | 0 |
| ✅ Category:Royal Navy admirals of the fleet | en | cat | 英國 | navy | 123 |
| ✅ List of British field marshals | en | zhlist | 英國 | army | 161 |
| ✅ List of field marshals of the British Army | en | zhlist | 英國 | army | 161 |
| ✅ 英國陸軍元帥列表 | zh | zhlist | 英國 | army | 144 |
| ✅ Field marshal (United Kingdom) | en | zhlist | 英國 | army | 145 |
| ✅ Category:Imperial German Navy admirals | en | cat | 德國 | navy | 1 |
| ✅ Category:Admirals of the Imperial German Navy | en | cat | 德國 | navy | 21 |
| ✅ Category:Counter admirals of the Imperial German Navy | en | cat | 德國 | navy | 6 |
| ✅ Category:Grand admirals of the Imperial German Navy | en | cat | 德國 | navy | 4 |
| ✅ Category:Vice admirals of the Imperial German Navy | en | cat | 德國 | navy | 21 |
| ✅ Category:Imperial German Navy admirals of World War I | en | cat | 德國 | navy | 29 |
| ✅ Category:German admirals of World War I | en | cat | 德國 | navy | 0 |
| ✅ Category:Grand admirals of Germany | en | cat | 德國 | navy | 0 |
| ✅ Category:Grand admirals of the German Empire | en | cat | 德國 | navy | 0 |
| ❌ 德國海軍元帥 | zh | zhlist | 德國 | navy | — |
| ❌ 德意志帝国海军将领 | zh | zhlist | 德國 | navy | — |
| ❌ 意大利元帅 | zh | zhlist | 義大利 | army | — |
| ✅ Category:纳粹德国海军将领 | zh | cat | 德國 | navy | 2 |
| ✅ Category:義大利元帥 | zh | cat | 義大利 | unknown | 12 |
| ✅ Marshal of Italy | en | zhlist | 義大利 | army | 17 |
| ✅ Category:Marshals of Italy | en | cat | 義大利 | unknown | 0 |
| ✅ Category:Marshals of the Air of Italy | en | cat | 義大利 | air_force | 0 |
| ✅ Category:Italian Air Force marshals | en | cat | 義大利 | air_force | 0 |
| ✅ 伊塔洛·巴尔博 | zh | person | 義大利 | air_force | 1 |
| ✅ Category:Marshals of Poland | en | cat | 波蘭 | army | 8 |
| ✅ Category:Polish field marshals | en | cat | 波蘭 | army | 0 |
| ✅ Category:Chiefs of the General Staff of the Austro-Hungarian Army | en | cat | 奧匈帝國 | army | 0 |
| ✅ 第二次世界大戰各國指揮官列表 | zh | cmdlist | None | unknown | 162 |

**失敗頁：**
- 德國海軍元帥（zh）：HTTP 200；{"code": "missingtitle", "info": "The page you specified doesn't exist.", "docref": "See https://zh.wikipedia.org/w/api.php for API usage. Subscribe to the mediawiki-api-announce mailing list at &lt;h
- 德意志帝国海军将领（zh）：HTTP 200；{"code": "missingtitle", "info": "The page you specified doesn't exist.", "docref": "See https://zh.wikipedia.org/w/api.php for API usage. Subscribe to the mediawiki-api-announce mailing list at &lt;h
- 意大利元帅（zh）：HTTP 200；{"code": "missingtitle", "info": "The page you specified doesn't exist.", "docref": "See https://zh.wikipedia.org/w/api.php for API usage. Subscribe to the mediawiki-api-announce mailing list at &lt;h

未做／跳過：Waffen-SS 專類、美國海軍陸戰隊、法國空軍、波蘭／加拿大／澳洲／芬蘭等僅採分類頁（未逐子分類展開，除非在上表）；比利時、塞爾維亞、保加利亞等未另建專類；荷蘭、希臘、泰國、加拿大、紐西蘭等若出現在二戰指揮官列表則已收入。zh 德國元帥衍生頁（`德国元帅衔大将`）因列首為頭銜連結、易誤抓，未採用。

## 2. 人數

**總人數 7723**；`in_leader_bios=true` **38** 人（比對快照 924 人：name 或 name_zh 正規化全等＋少量別名；繁簡字差異可能漏判，見第 5 節）。

全體：S **103**／A **262**／B **7358**，S+A 合計 **365**（Tai 23:11 門檻 375：超過則生平先不跑，回報人數與新增者；未超過則 commit 後開跑 S／A 生平）。war：待查證 3562、WWII 2625、WWI 1488、both 48。branch：army 5532、navy 1606、air_force 581、unknown 4。

| 國家／政權 | 人數 | S | A | B |
|---|---|---|---|---|
| 英國 | 1737 | 14 | 28 | 1695 |
| 美國 | 1358 | 12 | 26 | 1320 |
| 德國 | 1033 | 26 | 26 | 981 |
| 俄羅斯帝國 | 644 | 2 | 8 | 634 |
| 義大利 | 581 | 7 | 4 | 570 |
| 中華民國-國民政府 | 543 | 3 | 41 | 499 |
| 法國 | 407 | 6 | 10 | 391 |
| 日本 | 398 | 12 | 25 | 361 |
| 澳洲 | 221 | 0 | 14 | 207 |
| 中國共產黨 | 208 | 3 | 12 | 193 |
| 蘇聯 | 137 | 8 | 12 | 117 |
| 奧匈帝國 | 121 | 1 | 4 | 116 |
| 加拿大 | 77 | 0 | 3 | 74 |
| 芬蘭 | 65 | 1 | 12 | 52 |
| 鄂圖曼帝國 | 64 | 1 | 5 | 58 |
| 羅馬尼亞 | 59 | 1 | 4 | 54 |
| 波蘭 | 37 | 3 | 4 | 30 |
| 中華民國-北洋 | 7 | 0 | 1 | 6 |
| 紐西蘭 | 4 | 0 | 4 | 0 |
| 希臘 | 4 | 0 | 4 | 0 |
| 荷蘭 | 4 | 0 | 4 | 0 |
| 自由印度臨時政府 | 4 | 0 | 4 | 0 |
| 南斯拉夫 | 2 | 1 | 1 | 0 |
| 捷克斯洛伐克 | 2 | 0 | 2 | 0 |
| 南非 | 1 | 1 | 0 | 0 |
| 泰國 | 1 | 1 | 0 | 0 |
| 斯洛伐克 | 1 | 0 | 1 | 0 |
| 緬甸 | 1 | 0 | 1 | 0 |
| 瑞士 | 1 | 0 | 1 | 0 |
| 烏克蘭反抗軍 | 1 | 0 | 1 | 0 |
| **合計** | **7723** | 103 | 262 | 7358 |

中國三欄：中華民國-北洋、中華民國-國民政府、中國共產黨 分列如上（北洋欄為「Beiyang Army personnel」＋「軍閥」分類，政權歸屬未逐人核實，含後來投入國民政府者；共軍欄僅含元帥、大將與八路軍／新四軍將領分類，未含 1955 年後授銜者的省分類）。

### 分級標準（編輯判斷，非出處）

- **S**：跨國家喻戶曉的將領／艦隊司令／兼元首的將領（手工清單 `fame_tiers.json`，宜精）。
- **A**：參謀總長、軍種總司令、集團軍／方面軍／戰區司令、艦隊司令、知名戰役主要指揮（手工清單，未達家喻戶曉）。
- **B**：其餘列表上的將級人物（預設）。
- 分級只對真實進 roster 者生效；`fame_tiers.json` 中未命中索引者共 91 個鍵（多為該人不在所採分類或標題寫法不同；不是補人，只是未使用）。

## 3. 生平費用與時間估價

依 v3 最低標準（≥3 段、≥300 字、職位要有任期）。**單價採實測**：B3 full batches 001–003（15 人，Sonnet 研究＋Opus 審查，未寫庫）合計 **$7.7597**（`.dev/cc-b3full-b00[123]-*.json` 的 `total_cost_usd` 之和）＝ **約 $0.517／人**；牆上時間約 26 分鐘／15 人 ≈ 1.7 分／人（每批 5 人約 7–11 分鐘；API duration_api_ms 合計約 25.3 分鐘）。
v3 樣本沒有可用成本數據；v3 因要求更高，**假設**單價為實測的 1.5×（主估 ≈ **$0.78／人、≈ 2.6 分／人**），區間假設 1.3×–1.8×（$0.67–$0.93／人）。以下以既有「5 人一批、Sonnet＋Opus 迴圈」循序執行為前提；若併行則時間可縮短，費用不變。

| 檔位 | 人數 | 主估費用（1.5×） | 區間（1.3×–1.8×） | 牆上時間（主估；區間） |
|---|---|---|---|---|
| 只做 S | 103 | $80（$53 為未加成基準） | $69–$96 | 約 4.5 小時（3.9–5.4） |
| S + A | 365 | $283（$189 為未加成基準） | $245–$340 | 約 15.8 小時（13.7–19.0） |
| 全部（含 unverified） | 7723 | $5,993（$3,995 為未加成基準） | $5,194–$7,191 | 約 334.7 小時（290.0–401.6） |
| 全部（僅 category_scoped，已排除時期未驗者） | 4489 | $3,483（$2,322 為未加成基準） | $3,019–$4,180 | 約 194.5 小時（168.6–233.4） |

註：「全部」含 3234 位 `unverified`（時期未驗）人物；若先人工篩掉窗外者，實際人數與費用會顯著下降。已在庫（`in_leader_bios=true`）38 人若沿用既有生平可免做，上表未扣除。

## 4. 將領入庫 schema 提案（僅提案；未改任何程式、資料或 ARCHITECTURE.md）

### 現況（已對照 repo）
- `leader_records.role` CHECK 只有 `head_of_state`／`head_of_government`，且必有 `regime_id`：是地圖／時間軸上「誰統治這個政權」的名簿。
- `leader_bios` 是人物卡生平（約 924 人，幾乎都是元首／首腦）。
- `person_positions.position_kind` 已含 `military_command`（另有 military_education 等；見 ARCHITECTURE §16.3、`BioParagraphsPositionsRolesTests.cs`）。
- `person_roles.role_kind` 目前僅 `head_of_state`／`head_of_government`／`de_facto_leader`／`cabinet_minister`；`military_commander` 在 `.dev/person-role-kind.md` 草案列為 P2、ARCHITECTURE §16.3.1／§19.3.2 已訂其收錄條件（G5：國家最高軍職固定清單，或 verified 戰役 `commander`／`staff` 參與），但**尚未進 CHECK**。

| 方案 | 做法 | 優點 | 缺點 |
|---|---|---|---|
| **一（建議）** | 不擴大 `leader_records`；生平沿用 `leader_bios`；任期職位用 `person_positions`（`military_command`）；`person_roles.role_kind` 增列 `military_commander`（對齊草案 P2／G5）。已是元首的將領（蔣、曼納海姆、東條）維持一張人物卡、多角色。 | 不碰地圖元首邏輯；與既有三層（人物／角色／經歷）一致；只需一個 CHECK 值＋寫入層 G5 檢查；一人多角色自然成立 | 需先決定 `leader_bios` 是否更名；G5 門檻（固定職位清單）要 Tai 確認，Tier B 將領多半只進「經歷」不出卡 |
| 二 | 放寬 `leader_records.role` 加入軍職 | 表少、查詢單一 | 該表綁 `regime_id` 並用於「誰在統治這個政權」；戰場指揮官常對不到單一政權列，會污染地圖元首邏輯與既有查詢／測試 |
| 三 | 新建 `military_commands` 專表 | 軍職欄位可客製（戰區、部隊、軍階） | 與已有 `person_positions.military_command` 重複；遷移與雙寫成本高；與 T11「角色分表」決議重疊 |

**建議方案一。** 門檻沿用草案：國家級最高軍職，或有出處的戰役 participant 連結（G5）；本 roster 的 S／A 即為首批候選，B 級先只做「經歷」層。

## 5. 注意事項

- 失敗頁：3（德國海軍元帥；德意志帝国海军将领；意大利元帅）。Tai 23:11 已重試原 3 個 zh 標題（失敗結果不入 cache）；仍 missingtitle 者見上，並已改採現存對應頁。
- Tai 23:11 名單更正：「蓋詩」即戈特（John Vereker, 6th Viscount Gort），維持 S；「董宗文」為筆誤，未寫入 fame_tiers 或 roster，董其武維持 B；伊塔洛·巴爾博（Italo Balbo）以個人維基頁當索引列入，S 級。
- 中文名缺失：`name_zh="待查證"` 共 5646 人（en 分類成員無 zh langlink）；`name_original=null` 共 555 人（zh 列表人名無對應 en 連結）。
- 同名風險：合併靠標題正規化；同英文標題（去括號後）不同人（如多位 John Smith）會被誤併，反之同一人在 zh／en 標題寫法不同可能重複列兩筆。未逐筆查重，建議入庫前以 name_zh＋生卒年人工核對。
- 別名不確定：`in_leader_bios` 以 name／name_zh 正規化全等＋少量別名（蔣介石→蔣中正、東條英機等）；快照名稱簡繁混用，簡繁字差異（如「蒋／蔣」）可能漏判。抽查：曼納海姆、蔣中正、東條英機應為 true；貝當、戴高樂、孫中山、袁世凱應為 false（見下）。
  - 抽查結果：Carl Gustaf Emil Mannerheim=True；Chiang Kai-shek=True；Hideki Tojo=True；Philippe Pétain=False；Charles de Gaulle=False；Sun Yat-sen=未在名單；Yuan Shikai=未在名單；Winston Churchill=未在名單。
- 預算：本任務使用 MediaWiki API 無費用；session 預算未用盡。
- 重跑：`python3 data/seed/leaders/generals-roster/build_roster.py`（有 `cache/` 時不再打 API、排序固定；刪除 `cache/` 則重抓）。
