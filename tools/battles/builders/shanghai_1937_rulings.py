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
  "Q7": "jm179-map1 不重讀"}}
p.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n"); print("ok")
