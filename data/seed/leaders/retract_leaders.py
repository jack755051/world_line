#!/usr/bin/env python3
"""
撤回 leaders_batch2 的舊領導人記錄（改記錄＝撤回＋新增；新版由 send_leaders_batch2.py 寫入）。
  --batch v4_sourceurl：v3 sourceUrl 抽取錯誤的 80 筆（新版 *_V2）。
  --batch v5_clip    ：超出政權存在期間的 16 筆（9 筆新版 *_CLIP，7 筆整段在政權外、不再新增）。

leader_records 目前沒有撤回 API（LeadersEndpoints 只有 POST /leader-records），
所以直接在開發庫做軟撤回：只寫 retracted_at 與 retraction_reason，不 DELETE
（trg_leader_records_no_unretract 保證撤回不可逆）。只針對 worldline-borders-dev-db 容器。

用法：
  python3 retract_leaders.py --batch NAME [--dry-run]   # 預設：在交易中執行後 ROLLBACK，列出影響筆數
  python3 retract_leaders.py --batch NAME --send        # COMMIT
"""
import argparse, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument("--send", action="store_true")
ap.add_argument("--dry-run", action="store_true")
ap.add_argument("--ids", default=os.path.join(HERE, "sent-leaders.json"))
ap.add_argument("--batch", required=True, choices=["v4_sourceurl", "v5_clip"])
ap.add_argument("--container", default="worldline-borders-dev-db")
a = ap.parse_args()
if a.container != "worldline-borders-dev-db":
    sys.exit("拒絕：只允許開發庫容器 worldline-borders-dev-db。")
dry = a.dry_run or not a.send

BATCHES = {
    "v4_sourceurl": ("更正 sourceUrl：v3 轉換時把全形括號後的文字（例如「（本次查閱」）一併抓進網址；"
                     "其餘欄位不變，由同 _id 加 _V2 的新記錄取代（leaders_batch2 v4）。",
                     ["LS_HOS_FRENCH_THIRD_REPUBLIC_19130218", "LS_HOS_FRENCH_THIRD_REPUBLIC_19200218", "LS_HOS_FRENCH_THIRD_REPUBLIC_19200921", "LS_HOS_FRENCH_THIRD_REPUBLIC_19200923", "LS_HOG_FRENCH_THIRD_REPUBLIC_19120114", "LS_HOG_FRENCH_THIRD_REPUBLIC_19131209", "LS_HOG_KINGDOM_ITALY_19060529", "LS_HOG_KINGDOM_ITALY_19091211", "LS_HOG_KINGDOM_ITALY_19100331", "LS_HOG_KINGDOM_ITALY_19110330", "LS_HOG_KINGDOM_ITALY_19140321", "LS_HOG_KINGDOM_ITALY_19141105", "LS_HOG_KINGDOM_ITALY_19160618", "LS_HOG_KINGDOM_ITALY_19171029", "LS_HOG_KINGDOM_ITALY_19190623", "LS_HOG_KINGDOM_ITALY_19200521", "LS_HOG_KINGDOM_ITALY_19200615", "LS_HOG_KINGDOM_ITALY_19210704", "LS_HOG_KINGDOM_ITALY_19220226", "LS_HOG_KINGDOM_ITALY_19220801", "LS_HOG_KINGDOM_ITALY_19221031", "LS_HOG_KINGDOM_ITALY_19430725", "LS_HOG_KINGDOM_ITALY_19440422", "LS_HOG_KINGDOM_ITALY_19440618", "LS_HOG_KINGDOM_ITALY_19441212", "LS_HOG_KINGDOM_ITALY_19450621", "LS_HOG_KINGDOM_ITALY_19451210", "LS_HOG_RUSSIAN_EMPIRE_19140212", "LS_HOG_RUSSIAN_EMPIRE_19160202", "LS_HOG_RUSSIAN_EMPIRE_19161123", "LS_HOG_RUSSIAN_EMPIRE_19170109", "LS_HOS_RUSSIAN_SFSR_19190330", "LS_HOG_RUSSIAN_SFSR_19171108", "LS_HOG_SOVIET_UNION_19230706", "LS_HOG_SOVIET_UNION_19240202", "LS_HOG_SOVIET_UNION_19301219", "LS_HOG_SOVIET_UNION_19410506", "LS_HOG_EMPIRE_JAPAN_19060107", "LS_HOG_EMPIRE_JAPAN_19080714", "LS_HOG_EMPIRE_JAPAN_19110830", "LS_HOG_EMPIRE_JAPAN_19121221", "LS_HOG_EMPIRE_JAPAN_19130220", "LS_HOG_EMPIRE_JAPAN_19140416", "LS_HOG_EMPIRE_JAPAN_19161009", "LS_HOG_EMPIRE_JAPAN_19180929", "LS_HOG_EMPIRE_JAPAN_19211113", "LS_HOG_EMPIRE_JAPAN_19220612", "LS_HOG_EMPIRE_JAPAN_19230902", "LS_HOG_EMPIRE_JAPAN_19240107", "LS_HOG_EMPIRE_JAPAN_19240611", "LS_HOG_EMPIRE_JAPAN_19260130", "LS_HOG_EMPIRE_JAPAN_19270420", "LS_HOG_EMPIRE_JAPAN_19290702", "LS_HOG_EMPIRE_JAPAN_19310414", "LS_HOG_EMPIRE_JAPAN_19311213", "LS_HOG_EMPIRE_JAPAN_19320526", "LS_HOG_EMPIRE_JAPAN_19340708", "LS_HOG_EMPIRE_JAPAN_19360309", "LS_HOG_EMPIRE_JAPAN_19370202", "LS_HOG_EMPIRE_JAPAN_19370604", "LS_HOG_EMPIRE_JAPAN_19390105", "LS_HOG_EMPIRE_JAPAN_19390830", "LS_HOG_EMPIRE_JAPAN_19400116", "LS_HOG_EMPIRE_JAPAN_19400722", "LS_HOG_EMPIRE_JAPAN_19410718", "LS_HOG_EMPIRE_JAPAN_19411018", "LS_HOG_EMPIRE_JAPAN_19440722", "LS_HOG_EMPIRE_JAPAN_19450407", "LS_HOG_EMPIRE_JAPAN_19450817", "LS_HOG_EMPIRE_JAPAN_19451009", "LS_HOG_ROC_NATIONALIST_19281028", "LS_HOG_ROC_NATIONALIST_19301124", "LS_HOG_ROC_NATIONALIST_19310616", "LS_HOG_ROC_NATIONALIST_19320101", "LS_HOG_ROC_NATIONALIST_19320129", "LS_HOG_ROC_NATIONALIST_19351216", "LS_HOG_ROC_NATIONALIST_19380101", "LS_HOG_ROC_NATIONALIST_19391211", "LS_HOG_ROC_NATIONALIST_19430913", "LS_HOG_ROC_NATIONALIST_19450604"]),
    "v5_clip": ("依 dev DB 政權存在期間截斷：原期間超出政權範圍；截後仍有期間者由同 _id 加 _CLIP 的新記錄取代，"
                "整段在政權外者不再新增（leaders_batch2 v5）。",
                ["LS_HOG_KINGDOM_ITALY_19060529_V2", "LS_HOG_KINGDOM_ITALY_19450621_V2", "LS_HOG_KINGDOM_ITALY_19451210_V2", "LS_HOG_RUSSIAN_SFSR_19171108_V2", "LS_HOG_SOVIET_UNION_19410506_V2", "LS_HOS_USA_19010914", "LS_HOG_USA_19010914", "LS_HOS_USA_19090304", "LS_HOG_USA_19090304", "LS_HOS_USA_19130304", "LS_HOG_USA_19130304", "LS_HOG_EMPIRE_JAPAN_19060107_V2", "LS_HOG_EMPIRE_JAPAN_19080714_V2", "LS_HOG_EMPIRE_JAPAN_19450817_V2", "LS_HOG_EMPIRE_JAPAN_19451009_V2", "LS_HOG_ROC_NATIONALIST_19450604_V2"]),
}
REASON, RETRACT = BATCHES[a.batch]

sent = json.load(open(a.ids, encoding="utf-8"))
todo = [(k, sent[k]) for k in RETRACT if k in sent and (k + "__RETRACTED") not in sent]
missing = [k for k in RETRACT if k not in sent]
if missing:
    sys.exit(f"找不到 id：{missing}")
print(f"待撤回 {len(todo)} 筆（清單 {len(RETRACT)} 筆，已撤回 {len(RETRACT)-len(todo)} 筆）")
if not todo:
    sys.exit(0)
uuids = ",".join("'" + u + "'" for _, u in todo)
reason = REASON.replace("'", "''")
sql = (f"BEGIN;\n"
       f"UPDATE leader_records SET retracted_at = now(), retraction_reason = '{reason}' "
       f"WHERE id IN ({uuids}) AND retracted_at IS NULL;\n"
       + ("ROLLBACK;\n" if dry else "COMMIT;\n"))
out = subprocess.run(["docker", "exec", "-i", a.container, "psql", "-U", "worldline", "-d", "worldline_borders_dev",
                      "-v", "ON_ERROR_STOP=1", "-At"], input=sql, capture_output=True, text=True)
print(out.stdout.strip()); 
if out.returncode != 0:
    sys.exit("FAIL：" + out.stderr[-800:])
n = next((int(l.split()[-1]) for l in out.stdout.splitlines() if l.startswith("UPDATE ")), -1)
if dry:
    print(f"（dry-run：交易已 ROLLBACK，影響 {n} 筆）")
    sys.exit(0)
if n != len(todo):
    print(f"警告：預期 {len(todo)} 筆，實際 {n} 筆", file=sys.stderr)
for k, _ in todo:
    sent[k + "__RETRACTED"] = "retracted"
json.dump(sent, open(a.ids, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"完成：撤回 {n} 筆")
