"""控制點組裝：人工判讀的城鎮圓點像素（種子）＋ ringfind 自動偵測的圓心精修＋ osm-places.json 經緯度 → readings.json 的 control_points。
用法：python3 -I tools/battles/cp_refine.py <battle> <seeds.json> <rings.json> [--win 7] [--require-ring]
--require-ring：種子不是在本圖上目視讀得（例如由同底圖另一張圖位移而來）時使用；找不到圓的點直接捨棄，不寫入。
seeds.json：{"mapKey", "meta": {...寫入 readings.json 的頂層欄位...}, "seedNote", "points": {圖上地名: {"px":[x,y], "osm": "osm-places.json results 的鍵", "note"?}}}
規則：在種子 ±win px 內取 score 最高的偵測圓；找不到則保留人工像素並註記。經緯度取 osm-places 結果第一筆（cp:… 鍵）。
已存在的 readings.json 只覆寫 control_points 與 meta 欄位，features／lines 保留。
"""
import json, math, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def main():
    battle, seeds_p, rings_p = sys.argv[1:4]
    win = float(sys.argv[sys.argv.index("--win") + 1]) if "--win" in sys.argv else 7.0
    S = json.loads(Path(seeds_p).read_text()); rings = json.loads(Path(rings_p).read_text())
    D = REPO / "data/seed/battles" / battle
    osm = json.loads((D / "osm-places.json").read_text())["results"]
    out = D / "digitized" / f"{S['mapKey']}.readings.json"
    R = json.loads(out.read_text()) if out.exists() else {"mapKey": S["mapKey"], "features": [], "lines": []}
    R.update(S.get("meta", {}))
    req = "--require-ring" in sys.argv
    cps, moved, dropped = {}, [], []
    for name, s in S["points"].items():
        sx, sy = s["px"]
        near = [r for r in rings if abs(r["px"][0] - sx) <= win and abs(r["px"][1] - sy) <= win]
        res = osm.get(s["osm"]) or []
        if not res:
            print("無 OSM 結果，略過：", name); continue
        o = res[0]
        cp = {"px": [float(sx), float(sy)], "lonlat": [round(o["lon"], 5), round(o["lat"], 5)],
              "osm": {"type": o["type"], "id": o["id"]}, "nameOsm": o["name"][:60]}
        if near:
            b = max(near, key=lambda r: r["score"])
            cp["px"] = [float(b["px"][0]), float(b["px"][1])]
            cp["pxManual"] = [float(sx), float(sy)]
            cp["note"] = f"圖上地名 {name}；圓心由 ringfind 於人工種子 ±{win:g} px 內精修（score {b['score']}，位移 {math.hypot(b['px'][0]-sx, b['px'][1]-sy):.1f} px）；lonlat 取 OSM Nominatim「{s['osm'][3:]}」"
            moved.append(math.hypot(b["px"][0] - sx, b["px"][1] - sy))
        elif req:
            dropped.append(name); continue
        else:
            cp["note"] = f"圖上地名 {name}；ringfind 在 ±{win:g} px 內未找到圓，保留人工判讀像素；lonlat 取 OSM Nominatim「{s['osm'][3:]}」"
        if s.get("note"): cp["note"] += "；" + s["note"]
        cps[name] = cp
    R["control_points"] = cps
    if dropped: R["control_points_dropped"] = {"names": dropped, "reason": f"--require-ring：種子 ±{win:g} px 內無偵測圓（本圖可能未繪此城鎮），不作控制點"}
    elif "control_points_dropped" in R: R.pop("control_points_dropped")
    out.write_text(json.dumps(R, ensure_ascii=False, indent=1) + "\n")
    moved.sort()
    print(f"{S['mapKey']}: 控制點 {len(cps)}；精修 {len(moved)}；人工與精修位移中位 {moved[len(moved)//2] if moved else 0:.1f} px，最大 {max(moved) if moved else 0:.1f} px；捨棄 {len(dropped)} {dropped}")


if __name__ == "__main__":
    main()
