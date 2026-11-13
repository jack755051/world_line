"""shanghai_1937 主管裁示（2026-11-13 16:14）寫入 battle.config.json "rulings"。
用法：python3 -I tools/battles/builders/shanghai_1937_rulings.py shanghai_1937（可重跑）
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_rulings.py shanghai_1937")
p = REPO / "data/seed/battles/shanghai_1937/battle.config.json"
c = json.loads(p.read_text())
c["rulings"] = {"2026-11-13 16:14": {
  "Q1": "tw-roc（su2015、chang2016、mnd2017）維持一族，不拆",
  "Q2": "JM-179／JM-70 評 B、JACAR 評 A（sources.json 已如此）",
  "Q3": "mnd2017 表三／表四（圖片表格）只作判讀與候選線索，不得作引文；經查目前無任何引文出自表三／表四",
  "Q5": "白茆口登陸日欄位留空，11/13 只作候選，欄內標 OCR「]Jth」讀值不確定",
  "Q6": "大場失守日精度記十月下旬，10/26 只作候選，不再找來源",
  "Q7": "jm179-map1 不重讀"},
 "2026-11-13 21:24": {
  "a": "大場鎮失守日改記 1937-10-26；只有 FRUS（us-frus）載明（JACAR 未載鎮陷落日），標待查證／單一來源；註記保留「十月下旬」",
  "b": "閘北守軍（八百壯士）止日維持：10/30 只作候選，寫入 conflict，欄位留空",
  "c": "波蘭 P1 9/1 標籤不處理（9/1＝戰前國界，已列缺口）",
  "overrides": [
   {"file": "r6-site-control.json", "match": {"placeAsInSource": "大場鎮"},
    "set": {"date": "1937-10-26", "datePrecision": "day", "dateCandidate": None,
            "dateNote": "主管 2026-11-13 21:24 (a)：日期改記 10/26，唯一出處 FRUS 1937 Vol. III Doc. 698（10/27 正午電「yesterday morning」攻占大場），JACAR 只到「十月下旬」（同月下旬）、歩34 戦闘詳報未載鎮陷落日 → 待查證、單一來源；原精度「十月下旬」保留於 dateRange",
            "confidenceRuling": {"basisFamilies": ["us-frus"], "why": "日期只由 FRUS 支持（主管 2026-11-13 21:24 (a)）"}}},
   {"file": "r5-engagements.json", "match": {"key": "zhabei-800"},
    "set": {"conflict": "止日：FRUS 1937 Vol. III Doc. 709（11/1 電）稱 30 日夜守軍被逐、300 人退入英軍防線 → 10/30；su2015 未載止日，與通說不一。依主管 2026-11-13 21:24 (b)：10/30 只作候選（endCandidate），period.end 留空"}}]}}
p.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n"); print("ok")
