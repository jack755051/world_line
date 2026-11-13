"""shanghai_1937：把兩件 JACAR 戰鬥詳報（C11111926900、C11111935000）加入 battle.config.json（texts.readable／cite、sourceFamilies.map）與 sources.json。
依主管 2026-11-13 20:56（Tai 恢復淞滬）。只引 JACAR 目錄頁「内容」欄翻刻文字；家族 jp-jacar，評 A（同既有 JACAR 條目）。
用法：python3 -I tools/battles/builders/shanghai_1937_jacar2.py shanghai_1937（可重跑；之後跑 fetch_readable、r356、verify_quotes、crosscheck、mark_fields）
"""
import sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[3]
if len(sys.argv) < 2 or sys.argv[1] != "shanghai_1937":
    raise SystemExit("用法：python3 -I tools/battles/builders/shanghai_1937_jacar2.py shanghai_1937")
D = REPO / "data/seed/battles/shanghai_1937"
NEW = {
 "jacar-c11111926900": {"title": "歩兵第３４連隊 大場鎮附近戦闘詳報（JACAR Ref.C11111926900）",
   "authors": ["歩兵第34連隊"], "publisher": "アジア歴史資料センター（所蔵：防衛省防衛研究所）"},
 "jacar-c11111935000": {"title": "歩兵第３８連隊 滸浦鎮附近戦闘詳報 第１号（JACAR Ref.C11111935000）",
   "authors": ["歩兵第38連隊"], "publisher": "アジア歴史資料センター（所蔵：防衛省防衛研究所）"},
}
cp = D / "battle.config.json"; c = json.loads(cp.read_text())
sp = D / "sources.json"; s = json.loads(sp.read_text())
for k, v in NEW.items():
    ref = k.split("-")[1].upper()
    url = f"https://www.jacar.archives.go.jp/das/meta/{ref}"
    c["texts"]["readable"][k] = url
    c["texts"]["cite"][k] = {"kind": "single", "file": f"rd/{k}.txt", "locator": f"JACAR {ref} 目錄頁「内容」欄", "lang": "ja"}
    c["sourceFamilies"]["map"][k] = "jp-jacar"
    s[k] = {**v, "url": url, "grade": "A", "gradeBasis": "日本陸軍原始檔案（戰鬥詳報，昭和12年作成）；只引「内容」欄翻刻文字",
            "family": "jp-jacar", "pageMethod": "JACAR 目錄頁 内容 欄"}
cp.write_text(json.dumps(c, ensure_ascii=False, indent=1) + "\n"); sp.write_text(json.dumps(s, ensure_ascii=False, indent=1) + "\n")
print("ok", list(NEW))
