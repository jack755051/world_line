#!/usr/bin/env python3
"""補回先前撤回的舊格式人物欄位：瀏覽器與 VLE 補查到合格出處（Tai 2026-11-14「用瀏覽器補查被擋的網站」；source-rules §5 補充 5「補到合格出處再寫回」）。

每筆：seed 從 unverified 移回欄位（或姓名欄補出處），庫內欄位值寫回、version+1、新增引文、field_sources 標 verified。
Petrulis 黨籍依合格出處（VLE 具名條目）改為基督教民主黨（§5 補充 4）。
原文存檔：~/wl-source-cache/old-format-restore/（manifest 記 sha256）。預設 dry-run；--apply 改 seed；--send --allow-write 寫開發庫。
用法（repo 根目錄）：python3 -I data/seed/leaders/gap-830/restore_fields_20261114.py <raw 資料夾> [--apply] [--send --allow-write]
"""
import json, sys, subprocess, hashlib, shutil, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
CACHE = Path.home() / "wl-source-cache" / "old-format-restore"
CONTAINER, DBUSER, DBNAME = "worldline-borders-dev-db", "worldline", "worldline_borders_dev"
RUN = "restore-fields-2026-11-14"
COL = {"name": "name", "party": "party", "summary": "summary"}

RAH = {"publisher": "Real Academia de la Historia（Diccionario Biográfico Español／Historia Hispánica）", "sourceKind": "official_history", "grade": "A",
       "gradeBasis": "西班牙皇家歷史學院《Diccionario Biográfico Español》（國家級傳記辭典；以 Chrome 讀取公開頁）"}
VLE = {"publisher": "Visuotinė lietuvių enciklopedija（Mokslo ir enciklopedijų leidybos centras）", "sourceKind": "official_history", "grade": "B",
       "gradeBasis": "VLE 具名作者條目（Mindaugas Tamošaitis）→ B"}
ITEMS = [
    ("es-antonio-maura", "party", {"zh-Hant": "保守黨", "en": "Conservative Party"}, [dict(RAH, title="Antonio Maura y Montaner",
        url="https://historia-hispanica.rah.es/biografias/29034-antonio-maura-y-montaner", locator="Biografía, párrafo 2",
        evidence="El futuro líder conservador", archive="rah-maura.txt")]),
    ("es-moret", "party", {"zh-Hant": "自由黨", "en": "Liberal Party"}, [dict(RAH, title="Segismundo Moret y Prendergast",
        url="https://historia-hispanica.rah.es/biografias/32175-segismundo-moret-y-prendergast", locator="Hechos, 1903 4/i",
        evidence="en el seno del Partido Liberal por su presidencia, entre Montero Ríos y Moret", archive="rah-moret.txt")]),
    ("lt-antanas-tumenas", "party", {"zh-Hant": "立陶宛基督教民主黨", "en": "Lithuanian Christian Democratic Party"}, [dict(VLE,
        title="Vytauto Petrulio vadovaujama Vyriausybė 1925", url="https://www.vle.lt/straipsnis/vytauto-petrulio-vadovaujama-vyriausybe-1925/",
        locator="Pirma pastraipa", evidence="krikščionių demokratų ministrui pirmininkui A. Tumėnui", archive="vle-petrulis-gov.txt")]),
    ("lt-antanas-tumenas", "summary", {"zh-Hant": "立陶宛法學家與基督教民主黨政治人物，1924 年 6 月至 1925 年 2 月任總理。",
                                       "en": "Lithuanian lawyer and Christian Democrat; he was prime minister from June 1924 to February 1925."},
        [dict(VLE, title="Antano Tumėno vadovaujama Vyriausybė 1924–1925", url="https://www.vle.lt/straipsnis/antano-tumeno-vadovaujama-vyriausybe-1924-1925/",
              locator="Pirma pastraipa", evidence="1924 06 18–1925 02 04 dirbusi Lietuvos Valstybės Vyriausybė", archive="vle-tumenas-gov.txt"),
         dict(VLE, title="Antano Tumėno vadovaujama Vyriausybė 1924–1925", url="https://www.vle.lt/straipsnis/antano-tumeno-vadovaujama-vyriausybe-1924-1925/",
              locator="Pirma pastraipa (2)", evidence="A. Tumėnas buvo pasirinktas ministru pirmininku kaip žinomas teisininkas", archive="vle-tumenas-gov.txt")]),
    ("lt-antanas-tumenas", "name", None, [dict(VLE, title="Antano Tumėno vadovaujama Vyriausybė 1924–1925",
        url="https://www.vle.lt/straipsnis/antano-tumeno-vadovaujama-vyriausybe-1924-1925/", locator="Antraštė ir pirma pastraipa",
        evidence="vadovaujama Antano Tumėno", archive="vle-tumenas-gov.txt")]),
    ("lt-vytautas-petrulis", "party", {"zh-Hant": "立陶宛基督教民主黨", "en": "Lithuanian Christian Democratic Party"}, [dict(VLE,
        title="Vytauto Petrulio vadovaujama Vyriausybė 1925", url="https://www.vle.lt/straipsnis/vytauto-petrulio-vadovaujama-vyriausybe-1925/",
        locator="Pirma pastraipa（同句受詞為「V. Petruliui」）", evidence="pasiūlyta kitam Lietuvių krikščionių demokratų partijos nariui",
        archive="vle-petrulis-gov.txt")]),
]
NOTE = {("lt-vytautas-petrulis", "party"): "合格出處優先（§5 補充 4）：VLE 具名條目記其為立陶宛基督教民主黨黨員；原值「立陶宛農民聯盟」只有不合格出處",
        ("lt-antanas-tumenas", "summary"): "原摘要的「主持 1922 年憲法起草委員會」「兼司法部長」未見合格出處，刪除"}


def lit(v):
    return "NULL" if v is None else "'" + str(v).replace("'", "''") + "'"


def main():
    raw_dir = Path([a for a in sys.argv[1:] if not a.startswith("--")][0])
    apply, send, allow = "--apply" in sys.argv, "--send" in sys.argv, "--allow-write" in sys.argv
    for _, _, _, srcs in ITEMS:  # 逐字核對
        for s in srcs:
            t = (raw_dir / s["archive"]).read_text()
            assert s["evidence"] in t and len(unicodedata.normalize("NFC", s["evidence"])) <= 80, s["evidence"]
    seeds = {}
    for d in sorted(HERE.glob("b[0-9][0-9]")):
        f = d / "research.json"; doc = json.loads(f.read_text())
        bios = json.loads((d / "sent.5052.json").read_text()).get("bios") or {}
        for p in doc["people"]:
            seeds[p["key"]] = (f, doc, p, bios.get(p["key"]))
    q = ["BEGIN;"]; touched = set()
    for key, field, value, srcs in ITEMS:
        f, doc, p, bio = seeds[key]
        objs = [{k: s.get(k) for k in ("title", "publisher", "url", "sourceKind", "locator", "evidence", "grade", "gradeBasis")} | {"licenseCode": None, "accessedOn": "2026-11-14"} for s in srcs]
        for o in objs: o["gradeBasis"] += "（%s）" % RUN
        note = NOTE.get((key, field), "補查到合格出處，依 source-rules §5 補充 5 寫回") + "（%s）" % RUN
        if field == "name":
            p["name"]["sources"] = [s for s in p["name"].get("sources", []) if s.get("grade") in ("A", "B")] + objs
            p["name"]["note"] = note
        else:
            p["unverified"] = [u for u in p.get("unverified", []) if u.get("field") != field]
            p[field] = {"value": value, "sources": objs, "note": note}
            val = lit(json.dumps(value, ensure_ascii=False)) + "::jsonb"
            q.append("UPDATE leader_bios SET %s=%s, version=version+1 WHERE id=%s AND retracted_at IS NULL;" % (COL[field], val, lit(bio)))
        for o in objs:
            q.append("INSERT INTO sources (id,source_kind,title,publisher,url) SELECT gen_random_uuid(),%s,%s,%s,%s WHERE NOT EXISTS (SELECT 1 FROM sources WHERE url=%s);"
                     % (lit(o["sourceKind"]), lit(o["title"]), lit(o["publisher"]), lit(o["url"]), lit(o["url"])))
            q.append("INSERT INTO leader_bio_field_citations (bio_id,field,source_id,locator,evidence_note,accessed_on,grade,quote,policy_version) "
                     "SELECT %s,%s,(SELECT id FROM sources WHERE url=%s ORDER BY created_at LIMIT 1),%s,%s,'2026-11-14',%s,%s,'source-2026-11-13' "
                     "WHERE NOT EXISTS (SELECT 1 FROM leader_bio_field_citations c JOIN sources s ON s.id=c.source_id WHERE c.bio_id=%s AND c.field=%s AND s.url=%s AND c.locator=%s AND c.retracted_at IS NULL);"
                     % (lit(bio), lit(field), lit(o["url"]), lit(o["locator"]), lit(o["evidence"]), lit(o["grade"]), lit(o["evidence"]),
                        lit(bio), lit(field), lit(o["url"]), lit(o["locator"])))
        q.append("UPDATE leader_bios SET field_sources = jsonb_set(coalesce(field_sources,'{}'::jsonb), %s, %s::jsonb) WHERE id=%s AND retracted_at IS NULL;"
                 % (lit("{%s}" % field), lit(json.dumps({"status": "verified", "note": note}, ensure_ascii=False)), lit(bio)))
        touched.add(f)
    q.append("COMMIT;")
    if apply:
        for f in touched:
            doc = next(v[1] for v in seeds.values() if v[0] == f); raw = f.read_text()
            f.write_text(json.dumps(doc, ensure_ascii=False, indent=2 if raw.startswith("{\n  ") else 1) + ("\n" if raw.endswith("\n") else ""))
        CACHE.mkdir(parents=True, exist_ok=True)
        with open(CACHE / "manifest.jsonl", "a") as m:
            for a in sorted({s["archive"] for _, _, _, ss in ITEMS for s in ss}):
                dst = CACHE / a; shutil.copyfile(raw_dir / a, dst)
                m.write(json.dumps({"txt": str(dst), "sha256": hashlib.sha256(dst.read_bytes()).hexdigest(), "run": RUN}) + "\n")
    (REPO / ".dev" / "dbwrite").mkdir(parents=True, exist_ok=True)
    (REPO / ".dev" / "dbwrite" / "restore-fields.sql").write_text("\n".join(q) + "\n")
    print(json.dumps({"apply_seed": apply, "fields": len(ITEMS), "seed_files": len(touched), "sql_lines": len(q)}, ensure_ascii=False))
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/restore-fields.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", DBUSER, "-d", DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                       input="\n".join(q) + "\n", capture_output=True, text=True)
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    print("已寫入。")


if __name__ == "__main__":
    main()
