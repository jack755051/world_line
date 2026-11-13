"""shanghai_1937：寫庫用設定寫入 battle.config.json "db"（write_battle_sql.py 讀）。陣營→政權：axis＝大日本帝國、allied＝中華民國（國民政府）。
用法：python3 -I tools/battles/builders/shanghai_1937_dbconfig.py shanghai_1937（可重跑）
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_dbconfig.py shanghai_1937")
p = REPO / "data/seed/battles/shanghai_1937/battle.config.json"
c = json.loads(p.read_text())
c["db"] = {"sideRegimes": {"axis": "empire-of-japan", "allied": "republic-of-china-nationalist"},
           "note": "寫庫前準備（主管 2026-11-13 21:24）：只做 dry-run，實寫待 Tai 另行同意"}
p.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n"); print("ok")
