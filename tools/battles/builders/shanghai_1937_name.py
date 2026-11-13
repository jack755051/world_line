"""shanghai_1937 戰役名 name.json 的建置腳本（引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/shanghai_1937_name.py shanghai_1937
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_name.py shanghai_1937")
C = Cites(sys.argv[1])
d = {"nameZh": "淞滬會戰", "nameEn": "Shanghai Operation", "nameJa": None,
     "basis": "中文取國史館館刊蘇聖雄文題「淞滬會戰」（中方通稱）；英文取 JM-179 章節名與 Map No. 1 圖題「Shanghai Operation」（前日軍軍官撰）。日方戰時稱「上海事変」等，本輪日方出處（JACAR 内容欄）未見戰役名，nameJa 留空記 gaps。",
     "citations": [C("su2015", "蔣中正對淞滬會戰之戰略再探"), C("jm179", "Shanghai Operation")],
     "field_sources": {"nameZh": {"basis": "source-text", "sourceKey": "su2015", "asInSource": "淞滬會戰"}},
     "nameZhStatus": "from-source"}
(REPO / "data/seed/battles/shanghai_1937/name.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n"); print("ok")
