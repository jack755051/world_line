"""poland_1939 R1／R7 相關 gaps 條目（只追加，不刪）的建置腳本（由 .dev/battle/poland/build/gaps_r1r7.py 複製；引文經 tools/battles/citelib.py 逐字定位）。
用法：python3 -I tools/battles/builders/poland_1939_gaps_r1r7.py poland_1939（可重跑；重跑後須再跑 verify_quotes／crosscheck／mark_fields --apply）
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citelib import Cites, REPO
if len(sys.argv) < 2 or sys.argv[1] != "poland_1939":
    raise SystemExit("用法：python3 -I tools/battles/builders/poland_1939_gaps_r1r7.py poland_1939（本 builder 內含 poland_1939 的研究資料，只接受此戰役代碼）")
BATTLE = sys.argv[1]
_C = Cites(BATTLE)
K, L, P, BP = (_C.short(k) for k in ("kennedy-dapam-20-255", "lemo-scriba-polen-1939", "ipn-suleja-wrzesien-1939", "bpb-vogel-lieb-blitzkriege"))
B = REPO
import json
p = B / "data/seed/battles/poland_1939/gaps.json"; g = json.loads(p.read_text())
L = g if isinstance(g, list) else g["gaps"]
new = [
 ("r1:sk-field-army", "unit_no_ab_source", "斯洛伐克野戰集團軍（Bernolák，Čatloš）：Kennedy 只提「Several Slovak battalions」，bpb／LeMO／IPN 未載編制；無 A/B 出處，不列 R1，Čatloš 主檔存在但不連結"),
 ("r1:su-armies", "unit_designation_conflict", "Kennedy p.124–125 依德方情報列白俄羅斯方面軍 Third/Eleventh Armies、烏克蘭方面軍 First/Tenth Armies；與一般所知蘇方番號不符，且無第二來源家族，本輪不列 R1 集團軍級，只列兩個方面軍"),
 ("r1:pl-armia-prusy:commander", "commander_no_source", "Armia Prusy 指揮官（Dąb-Biernacki）在已取得的 A/B 出處中未載，R7 不列"),
 ("r1:brigades", "scope", "R1 最細到師；騎兵旅（Wołyńska、Pomorska、Mazowiecka、Wielkopolska、Podlaska、Krakowska 等）、Brigade Eberhard、Kavallerie-Brigade 1 只出現在引文內，未建單位"),
 ("r1:de-divisions", "partial_roster", "Kennedy 德軍戰鬥序列 Chart 4 為圖片，文字只點名少數師；德軍步兵師未全列（55 師中列 11 個師級單位）"),
 ("r7:pl-obrona-warszawy:czuma", "commander_partial", "Walerian Czuma（華沙防衛初期指揮）僅 IPN 一句提及「z rąk gen. Waleriana Czumy」，未建 R7 任期，列待補"),
 ("r7:corps-commanders", "commander_no_source", "德軍各軍軍長（除 Guderian）在 Kennedy 文字中未點名；不填"),
]
have = {x.get("target") for x in L}
for t, k, n in new:
    if t not in have: L.append({"target": t, "kind": k, "note": n, "checkedOn": "2026-11-13"})
p.write_text(json.dumps(g, ensure_ascii=False, indent=1) + "\n"); print(len(L))
