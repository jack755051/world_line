#!/usr/bin/env python3
"""把網域歸類補進 run100/source-kind-overrides.json（寫庫腳本與 full/dryrun_full.py 共用）。可重跑：已存在且值相同就不動，值不同就中止。

依據：ARCHITECTURE §16 T1（A＝官方檔案、國家級傳記辭典、權威機構人名權威；B＝學術專書、具名作者／學術機構百科）。
歸類由 World Line 主管 2026-11-11 21:55 決定（Tai 授權範圍內）；之後新遇到的網域照同一原則加進 POLICY 並在報告列出；個人網站不收（值 null＝放棄）。
grade 不在 overrides（寫庫腳本取 seed citation 的 grade）；本腳本另輸出 domain-policy.json 供 dry-run 核對 seed grade 與政策是否一致。
用法：python3 -I data/seed/leaders/b3-trial/full/patch_source_kinds.py
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OVR = HERE.parent / "run100" / "source-kind-overrides.json"
POLICY = [  # (domain, source_kind, grade, 依據, 決定)
    ("lobid.org", "official_website", "A", "GND（德國國家圖書館人名權威檔）的官方鏡像；T1 權威機構人名權威", "主管 2026-11-11 21:55"),
    ("www.nids.mod.go.jp", "official_history", "A", "日本防衛省防衛研究所戰史研究中心（官方戰史）", "主管 2026-11-11 21:55"),
    ("www.dhm.de", "encyclopedia", "B", "Deutsches Historisches Museum LeMO 傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("millercenter.org", "encyclopedia", "B", "Miller Center, University of Virginia 總統傳記（學術機構傳記）", "主管 2026-11-11 21:55"),
    ("ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（具名作者百科條目）", "主管 2026-11-11 21:55"),
    ("www.ebsco.com", "encyclopedia", "B", "EBSCO Research Starters（同上；batch003 來源用 www 主機名，寫庫腳本以完整主機名比對）", "主管 2026-11-11 21:55（同一網域補主機名）"),
]

def main():
    ovr = json.loads(OVR.read_text(encoding="utf-8"))
    added = []
    for dom, kind, grade, basis, dec in POLICY:
        if dom in ovr:
            if ovr[dom] != kind:
                sys.exit(f"{dom} 已存在且值不同：{ovr[dom]!r} ≠ {kind!r}")
            continue
        ovr[dom] = kind; added.append(dom)
    OVR.write_text(json.dumps(dict(sorted(ovr.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "domain-policy.json").write_text(json.dumps([{"domain": d, "source_kind": k, "grade": g, "basis": b, "decision": x} for d, k, g, b, x in POLICY],
                                                      ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print("added:", added or "none", "total overrides:", len(ovr))

if __name__ == "__main__":
    main()
