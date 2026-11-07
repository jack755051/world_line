#!/usr/bin/env python3
"""
無生平人物缺口清單（Tai 2026-11-07 14:09）：從開發庫重算「有效任期、但沒連生平」的人名群組，維護狀態，輸出 .dev/bio-gap-830.md。

  python3 gap_status.py refresh   # 唯讀查 DB 重算；已存在的狀態保留；新連上生平的群組自動改「已寫入」
  python3 gap_status.py set <key> <狀態> [備註]   # 狀態：待查｜已寫入｜staging 疑義｜查無來源｜合議體（不建）｜連結候選
  python3 gap_status.py md        # 只重寫 markdown

群組 key＝姓名去重音、小寫、壓空白（同一人多職位會併成一組）。別名、同名不同人由研究批次判斷後用 set 標記。
"""
import collections, csv, io, json, os, re, subprocess, sys, unicodedata
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
STATE = os.path.join(HERE, "status.json")
MD = os.path.join(REPO, ".dev", "bio-gap-830.md")
COLL = re.compile(r"(junta|consejo|council|directorio|triunvirat|regency|regencia|buró|buro|comit|committee|gobierno provisional|provisional government|presidium|collective|commission|comisión|、|vacant|vacante|interregnum)", re.I)


def norm(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[\s,.\-]+", " ", s.lower()).strip()


def q(sql):
    out = subprocess.run(["docker", "exec", "-i", "worldline-borders-dev-db", "psql", "-U", "worldline", "-d", "worldline_borders_dev",
                          "-At", "-F", "\t", "-c", sql], check=True, capture_output=True, text=True).stdout
    return list(csv.reader(io.StringIO(out), delimiter="\t"))


def load():
    return json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {"groups": {}, "history": []}


def save(st):
    json.dump(st, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def refresh(st):
    rows = q("select r.id, g.slug, r.name, coalesce(r.name_zh,''), lower(r.valid_period), coalesce(upper(r.valid_period)::text,''), coalesce(r.person_id::text,'') "
             "from leader_records r join regimes g on g.id=r.regime_id where r.retracted_at is null")
    bios = {norm(b[1]): b[0] for b in q("select id, name from leader_bios where retracted_at is null")}
    cur = collections.OrderedDict()
    for rid, slug, name, zh, s, e, pid in rows:
        k = norm(name)
        g = cur.setdefault(k, {"name": name, "zh": zh, "recs": []})
        g["recs"].append({"id": rid, "slug": slug, "start": s, "end": e, "pid": pid})
    groups = st["groups"]
    for k, g in cur.items():
        unl = [r for r in g["recs"] if not r["pid"]]
        old = groups.get(k)
        if not unl:
            if old and old["status"] != "已寫入":
                old.update(status="已寫入", records=0)
            continue
        days = sum(((date.fromisoformat(r["end"]) if r["end"] else date(1945, 10, 1)) - date.fromisoformat(r["start"])).days for r in unl)
        base = {"name": g["name"], "zh": g["zh"], "slugs": sorted({r["slug"] for r in unl}), "records": len(unl), "days": days,
                "recordIds": [r["id"] for r in unl], "first": min(r["start"] for r in unl)}
        if old:
            old.update(base)
        else:
            status, note = "待查", ""
            if COLL.search(g["name"]):
                status, note = "合議體（不建）", "名稱為合議體或多人；不建單人生平。若其中成員另有個人任期，於該成員處理"
            elif k in bios:
                status, note = "連結候選", f"與現有生平 {bios[k]} 同名；確認同一人後以 PATCH 連結"
            groups[k] = {**base, "status": status, "note": note}
    for k in list(groups):
        if k not in cur and groups[k]["status"] != "已寫入":
            groups[k].update(status="已寫入", records=0)


def counts(st):
    c = collections.Counter(g["status"] for g in st["groups"].values())
    return dict(sorted(c.items()))


def md(st):
    gs = sorted(st["groups"].items(), key=lambda kv: (-kv[1]["days"], kv[0]))
    L = ["# 無生平人物缺口清單（Tai 2026-11-07 14:09 選定）", "",
         "範圍：開發庫 `worldline_borders_dev` 有效任期（`leader_records.retracted_at IS NULL`）中 `person_id` 為空者，依姓名去重音／大小寫／空白併組（同一人多職位併成一組）。",
         "狀態由 `data/seed/leaders/gap-830/gap_status.py` 維護（`status.json`），本檔由它產生，請勿手改。", "",
         "## 統計", "", "| 狀態 | 群組數 |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in counts(st).items()]
    L += ["", "## 批次紀錄", ""] + [f"- {h}" for h in st["history"]] + ["",
          "## 名單（依未連結任期總天數排序）", "", "| # | 姓名（任期紀錄原文） | 政權 | 未連結任期 | 天數 | 狀態 | 備註 |", "|---|---|---|---|---|---|---|"]
    for i, (k, g) in enumerate(gs, 1):
        nm = g["name"].replace("|", "／")[:90]
        L.append(f"| {i} | {nm} | {', '.join(g['slugs'])} | {g['records']} | {g['days']} | {g['status']} | {g.get('note', '').replace('|', '／')[:160]} |")
    os.makedirs(os.path.dirname(MD), exist_ok=True)
    open(MD, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    st = load()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "md"
    if cmd == "refresh":
        refresh(st)
    elif cmd == "set":
        k = norm(sys.argv[2]) if norm(sys.argv[2]) in st["groups"] else sys.argv[2]
        st["groups"][k]["status"] = sys.argv[3]
        if len(sys.argv) > 4:
            st["groups"][k]["note"] = sys.argv[4]
    elif cmd == "log":
        st["history"].append(sys.argv[2])
    save(st)
    md(st)
    print(json.dumps(counts(st), ensure_ascii=False))
