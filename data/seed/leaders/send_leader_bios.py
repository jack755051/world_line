#!/usr/bin/env python3
"""
領導人生平 batch1 v2（英國 12、德國 25）寫入開發庫 leader_bios，並把每人所有有效任期接上 person_id。

- 資料：data/seed/leaders/leader_bios_batch1.json（考證組 v2）。
- 只放 status=verified 的欄位值；status=不適用 照寫（值為考證組提供的「不適用…」）；待查證 欄位留空（null）。
- leader_bios 表無記錄狀態欄，改在 fieldSources 每欄標 status（verified／不適用／待查證）與出處，待查證欄只有 status+note。
- 任期對應：讀開發庫（docker exec worldline-borders-dev-db，唯讀 SELECT）中英國／德國政權的有效 leader_records，依姓名比對；
  再以 JSON 所列 db_uuid 交叉檢查。
- 寫入一律經 API（POST /leader-bios、PATCH /leader-records/{id}/person），不 DELETE；已接到其他 person 者（如希特勒的已撤回測試生平）改接新生平。
- 預設 dry-run；--send 才寫入。拒絕 5051。API key 讀 repo .env 的 WORLDLINE_API_KEY，不印出。
- 記帳：sent-bios.json（person_key → bio id），重跑冪等。
"""
import argparse, json, os, re, subprocess, sys, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = os.path.join(HERE, "leader_bios_batch1.json")
SENT = os.path.join(HERE, "sent-bios.json")
CONTAINER = "worldline-borders-dev-db"
REGIME_SLUGS = ["german-empire", "deutsches-reich", "united-kingdom", "united-kingdom-of-great-britain-and-ireland"]
FIELD_MAP = {"birth_date": "birthDate", "death_date": "deathDate", "birthplace": "birthPlace", "party": "party", "summary": "summary"}
URL_RE = re.compile(r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def api_key():
    for line in open(os.path.join(REPO, ".env"), encoding="utf-8"):
        if line.startswith("WORLDLINE_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    sys.exit("找不到 WORLDLINE_API_KEY")


def call(base, method, path, body, key):
    req = urllib.request.Request(base + path, method=method, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", "X-API-Key": key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]


def norm(s):
    return re.sub(r"\s+", " ", s.strip().rstrip(".")).lower()


def db_records():
    slugs = ",".join("'%s'" % s for s in REGIME_SLUGS)
    sql = ("select l.id, r.slug, l.name, coalesce(l.person_id::text,''), lower(l.valid_period), coalesce(upper(l.valid_period)::text,'') "
           "from leader_records l join regimes r on r.id=l.regime_id where l.retracted_at is null and r.slug in (%s) order by 2,5" % slugs)
    out = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "worldline", "-d", "worldline_borders_dev",
                          "-At", "-F", "\t", "-c", sql], check=True, capture_output=True, text=True).stdout
    return [dict(zip(["id", "slug", "name", "person_id", "start", "end"], l.split("\t"))) for l in out.splitlines() if l]


def build(p):
    body = {"name": p["name_original"].rstrip("."), "nameZh": p["name_zh"], "isTest": False}
    fs, pending = {}, []
    for k, v in p["fields"].items():
        api = FIELD_MAP[k]
        st = v["status"]
        ent = {"status": st}
        if st in ("verified", "不適用"):
            src = v.get("source") or ""
            if st == "verified" and not src:
                raise ValueError(f"{p['person_key']}.{k} verified 卻無出處")
            m = URL_RE.search(src)
            ent["source"] = src
            ent["url"] = m.group(0) if m else None
            if v.get("note"):
                ent["note"] = v["note"]
            val = v["value"]
            if api in ("birthDate", "deathDate"):
                if not DATE_RE.match(val or ""):
                    raise ValueError(f"{p['person_key']}.{k} 日期格式不對：{val}")
                body[api] = val
                if api == "birthDate":
                    body["birthDatePrecision"] = "day"
            else:
                body[api] = {"zh-Hant": val}
        elif st == "待查證":
            pending.append(api)
            if v.get("note") or p.get("note"):
                ent["note"] = v.get("note") or p["note"]
        else:
            raise ValueError(f"{p['person_key']}.{k} 未知 status {st}")
        fs[api] = ent
    body["fieldSources"] = fs
    return body, pending


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default="http://127.0.0.1:5052")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true")
    g.add_argument("--send", action="store_true")
    a = ap.parse_args()
    if ":5051" in a.base_url:
        sys.exit("拒絕：5051 是正式環境")
    data = json.load(open(DATA, encoding="utf-8"))
    people = data["people"]
    recs = db_records()
    sent = json.load(open(SENT, encoding="utf-8")) if os.path.exists(SENT) else {}
    by_name = {}
    for r in recs:
        by_name.setdefault(norm(r["name"]), []).append(r)
    plan, unmatched, warn = [], [], []
    used = set()
    for p in people:
        body, pending = build(p)
        mine = by_name.get(norm(p["name_original"]), [])
        used.update(r["id"] for r in mine)
        json_ids = {lr["db_uuid"] for lr in p["leader_records"] if lr.get("db_uuid")}
        active_ids = {r["id"] for r in recs}
        for j in json_ids & active_ids - {r["id"] for r in mine}:
            warn.append(f"{p['person_key']}: JSON 列的有效任期 {j} 未以姓名對上")
        if not mine:
            unmatched.append(p["person_key"])
        plan.append((p, body, pending, mine))
    leftover = [r for r in recs if r["id"] not in used]
    print(f"人數 {len(plan)}；有效任期（英德 4 政權）{len(recs)} 筆，對上 {len(used)} 筆，未對上 {len(leftover)} 筆")
    for r in leftover:
        print("  任期無生平：", r["slug"], r["name"], r["start"], r["end"])
    for w in warn:
        print("  警告：", w)
    print("無對應任期的人：", unmatched or "無")
    key = api_key() if a.send else None
    n_bio = n_skip = n_patch = n_same = fail = 0
    for p, body, pending, mine in plan:
        pk = p["person_key"]
        bid = sent.get(pk)
        tag = f"{pk:24s} {body['name']:32s} 待查證欄={','.join(pending) or '-'} 任期={len(mine)}"
        if bid:
            n_skip += 1
            print("跳過（已建）", tag)
        elif a.send:
            st, res = call(a.base_url, "POST", "/api/v1/leader-bios", body, key)
            if st != 201:
                fail += 1
                print("FAIL 建生平", tag, st, res)
                continue
            bid = (res.get("data") or res)["id"]
            sent[pk] = bid
            json.dump(sent, open(SENT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            n_bio += 1
            print("✓ 建生平", tag, bid)
        else:
            n_bio += 1
            print("[dry] 建生平", tag)
        for r in mine:
            if bid and r["person_id"] == bid:
                n_same += 1
                continue
            note = f"（原接 {r['person_id']}）" if r["person_id"] else ""
            if a.send:
                st, res = call(a.base_url, "PATCH", f"/api/v1/leader-records/{r['id']}/person", {"personId": bid}, key)
                if st != 200:
                    fail += 1
                    print("   FAIL PATCH", r["id"], st, res)
                    continue
                print("   ✓ PATCH", r["id"], r["slug"], r["start"], note)
            else:
                print("   [dry] PATCH", r["id"], r["slug"], r["start"], note)
            n_patch += 1
    mode = "寫入" if a.send else "dry-run"
    print(f"完成（{mode}）：建生平 {n_bio}，已建跳過 {n_skip}，PATCH {n_patch}，已接好 {n_same}，失敗 {fail}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
