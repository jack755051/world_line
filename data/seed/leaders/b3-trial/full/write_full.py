#!/usr/bin/env python3
"""B3 full 已研究批次寫入 5442（Tai 2026-11-14 同意先寫 full/ 已研究好的人；續跑其餘待 Tai 決定）。

沿用 run100/write_b3_paragraphs.py 的 plan()／build_sql()（同一套規則：來源以網址對帳、未歸類網域拒寫、X 不入庫、
無引文列不寫、庫內已有的段落／經歷／角色略過）。寫前請先跑 verify.py（含逐字比對）與 dryrun_full.py。
預設只產 SQL 並以 ROLLBACK 演練；--send --allow-write 才在單一交易寫入。寫前 pg_dump，只寫 5442。
用法（repo 根目錄）：python3 -I data/seed/leaders/b3-trial/full/write_full.py batch001 batch002 batch003 [--send --allow-write]
"""
import importlib.util, json, os, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
spec = importlib.util.spec_from_file_location("w3", HERE.parent / "run100" / "write_b3_paragraphs.py")
w3 = importlib.util.module_from_spec(spec); spec.loader.exec_module(w3)


def main():
    names = [a for a in sys.argv[1:] if not a.startswith("--")]
    send, allow = "--send" in sys.argv, "--allow-write" in sys.argv
    if not names:
        raise SystemExit("請指定批次（例：batch001 batch002）")
    batches = [(n, json.loads((HERE / n / "research.json").read_text(encoding="utf-8"))) for n in names]
    overrides = json.load(open(w3.OVERRIDES)) if os.path.exists(w3.OVERRIDES) else {}
    st = w3.db_state(None)
    P = w3.plan(batches, st, overrides)
    if P["unclassified"] or P["bad"] or P["bio_missing"]:
        raise SystemExit("有未歸類網域、驗證不過或庫內無 bio：%s" % json.dumps({"unclassified": list(P["unclassified"]), "bad": P["bad"], "bio_missing": P["bio_missing"]}, ensure_ascii=False))
    P["par"] = [r for r in P["par"] if r["cit"]]; P["pos"] = [r for r in P["pos"] if r["cit"]]; P["role_ok"] = [r for r in P["role_ok"] if r.get("cit")]
    sql = w3.build_sql(P)
    lines = sql.split("\n"); assert lines[0] == "BEGIN;" and lines[-1] == "COMMIT;"
    dev = REPO / ".dev" / "dbwrite"; dev.mkdir(parents=True, exist_ok=True)
    (dev / "b3full-write.sql").write_text(sql + "\n", encoding="utf-8")
    per = {}
    for b, d in batches:
        for p in d["people"]:
            per[p["key"]] = {"bio": p.get("bioId"), "paragraphs": sum(1 for r in P["par"] if r["bio"] == p.get("bioId")),
                             "positions": sum(1 for r in P["pos"] if r["bio"] == p.get("bioId")), "roles": sum(1 for r in P["role_ok"] if r["bio"] == p.get("bioId")),
                             "gaps": sum(1 for g in P["gaps"] if g["bio"] == p.get("bioId"))}
    summ = {"people": P["people"], "paragraphs": len(P["par"]), "positions": len(P["pos"]), "roles": len(P["role_ok"]), "gaps": len(P["gaps"]),
            "sources_new": len(P["sources_new"]), "already": P["already"], "per_person": per}
    print(json.dumps(summ, ensure_ascii=False, indent=1))
    run = lambda body: subprocess.run(["docker", "exec", "-i", w3.CONTAINER, "psql", "-U", w3.DBUSER, "-d", w3.DBNAME, "-v", "ON_ERROR_STOP=1", "-1", "-q"],
                                      input=body, capture_output=True, text=True)
    r = run("\n".join(lines[:-1] + ["ROLLBACK;"]) + "\n")
    if r.returncode:
        raise SystemExit("ROLLBACK 演練失敗：" + r.stderr[:800])
    print("ROLLBACK 演練通過。")
    if not send:
        print("（未寫庫；SQL 見 .dev/dbwrite/b3full-write.sql）"); return
    if not allow:
        raise SystemExit("需 --send --allow-write")
    r = run(sql + "\n")
    if r.returncode:
        raise SystemExit("寫入失敗（整筆交易回滾）：" + r.stderr[:800])
    (dev / "b3full-write-result.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1) + "\n")
    print("已寫入。")


if __name__ == "__main__":
    main()
