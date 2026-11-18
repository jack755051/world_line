"""poland_1939 戰役名 name.json的建置腳本（由 .dev/battle/poland/build/name.py 複製；引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/poland_1939_name.py poland_1939（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "poland_1939":
    raise SystemExit("用法：python3 -I tools/battles/builders/poland_1939_name.py poland_1939（本 builder 內含 poland_1939 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
K, L, P, BP = (_C.short(k) for k in ("kennedy-dapam-20-255", "lemo-scriba-polen-1939", "ipn-suleja-wrzesien-1939", "bpb-vogel-lieb-blitzkriege"))
B = REPO
import json
d = {"nameEn": "The German Campaign in Poland (1939)", "nameZh": "波蘭戰役（1939 年九月戰役）",
     "nameDe": "Überfall auf Polen 1939", "namePl": "kampania wrześniowa (Wrzesień 1939)",
     "basis": "英文取 Kennedy DA Pam 20-255 書名（美國陸軍）；德文取 LeMO 專文標題；波文取 IPN Suleja 內文「kampanii wrześniowej」。三方立場不同：德方學術用 Überfall（入侵），波方稱九月戰役／防衛戰。中文名為執行者譯名，待審。",
     "citations": [K("The German Campaign in Poland (1939)"), L("Überfall auf Polen 1939"), P("Ostatnią bitwę kampanii wrześniowej stoczyły")],
     "nameZhStatus": "unreviewed"}
(B / "data/seed/battles/poland_1939/name.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n"); print("ok")
