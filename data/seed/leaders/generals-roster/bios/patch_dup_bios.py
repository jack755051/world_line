"""寫庫後修正（2026-11-13，Tai 11:05 寫入開發庫授權內；只動本次 write_generals_bios 新建的 bio）。

1. 研究檔裡同一人被研究兩次（名冊重複列），寫庫建出 4 組重複 bio。I5 不可刪除，改用軟撤回：
   重複那筆 bio 設 retracted_at／retraction_reason／superseded_by＝保留那筆，其段落、任期、角色、待查證一併撤回。
2. 7 位華人將領 research.json 的 name 是「待查證」，寫成 bio.name；華人的原文名就是中文名，改為 name_zh。
   伏見宮博恭王 name 含簡體「见」與羅馬拼音，改為原文名 伏見宮博恭王。

用法：python3 -I patch_dup_bios.py            # dry-run，印 SQL
      python3 -I patch_dup_bios.py --apply    # 單一交易寫入 5442 開發庫
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RES = HERE / "bios-written-20261113.json"  # 本次寫庫結果（key→新 bio id）
# (撤回的 key, 保留的 key)
DUPS = [("williamdleahy", "williamdanielleahy"), ("何应钦", "heyingqin"), ("孙立人", "sunli-jen"), ("陈诚", "chencheng")]
REASON = "重複人物：研究檔同一人列兩次（%s／%s），保留 %s（2026-11-13 寫庫後修正）"
FIX_NAME = {"伏见宫博恭王": "伏見宮博恭王"}


def lit(s):
    return "NULL" if s is None else "'" + str(s).replace("'", "''") + "'"


def main():
    nb = {b["key"]: b for b in json.loads(RES.read_text())["new_bios"]}
    sql = ["BEGIN;"]
    for drop, keep in DUPS:
        d, k = nb[drop]["id"], nb[keep]["id"]
        r = lit(REASON % (drop, keep, keep))
        sql.append(f"UPDATE leader_bios SET retracted_at=now(), retraction_reason={r}, superseded_by='{k}', version=version+1 WHERE id='{d}' AND retracted_at IS NULL;")
        for t in ("leader_bio_paragraphs", "person_positions", "person_roles", "leader_bio_gaps"):
            sql.append(f"UPDATE {t} SET retracted_at=now(), retraction_reason={r} WHERE bio_id='{d}' AND retracted_at IS NULL;")
    for key, b in nb.items():
        if b["name"] == "待查證" and b["name_zh"]:
            sql.append(f"UPDATE leader_bios SET name={lit(b['name_zh'])}, version=version+1 WHERE id='{b['id']}' AND name='待查證';")
        if key in FIX_NAME:
            sql.append(f"UPDATE leader_bios SET name={lit(FIX_NAME[key])}, version=version+1 WHERE id='{b['id']}';")
    sql.append("COMMIT;")
    s = "\n".join(sql) + "\n"
    if "--apply" not in sys.argv:
        print(s); return
    p = subprocess.run(["docker", "exec", "-i", "worldline-borders-dev-db", "psql", "-U", "worldline", "-d", "worldline_borders_dev",
                        "-v", "ON_ERROR_STOP=1", "-1"], input=s, capture_output=True, text=True)
    print(p.stdout, p.stderr)
    if p.returncode: raise SystemExit(p.returncode)
    (HERE / "patch_dup_bios.applied.sql").write_text(s, encoding="utf-8")


if __name__ == "__main__":
    main()
