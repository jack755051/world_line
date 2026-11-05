#!/usr/bin/env python3
"""
軟撤回測試用生平種子資料（bios_test_seed.py 於 2026-11-03 所建立的測試資料）。

撤回對象（共 3 筆）：
  leader_records 01a19efa-769a-7615-9705-89c66d803905
      邱吉爾 UK head_of_government 1940-05-10..1945-07-26（由測試種子建立，is_test=true）
  leader_bios 01a19ef6-b3dd-7b81-91ac-bc92c33a4aaa
      Adolf Hitler（is_test=true）
  leader_bios 01a19efa-758c-718a-b1ec-27916469f239
      Winston Churchill（is_test=true）

撤回做法：只填 retracted_at＋retraction_reason，不 DELETE，不動 verified 等其他欄位。
只針對 worldline-borders-dev-db 容器。

用法：
  python3 retract_test_bios.py              # dry-run（預設）：在交易中執行後 ROLLBACK，列出影響筆數
  python3 retract_test_bios.py --send       # COMMIT
"""
import argparse, subprocess, sys

REASON = "測試種子，未經考證"

LEADER_RECORD_ID = "01a19efa-769a-7615-9705-89c66d803905"
BIO_IDS = [
    "01a19ef6-b3dd-7b81-91ac-bc92c33a4aaa",  # Adolf Hitler
    "01a19efa-758c-718a-b1ec-27916469f239",  # Winston Churchill
]

ap = argparse.ArgumentParser(description="軟撤回測試用生平種子資料")
ap.add_argument("--send", action="store_true", help="實際 COMMIT（預設為 dry-run，交易後 ROLLBACK）")
ap.add_argument("--container", default="worldline-borders-dev-db")
a = ap.parse_args()

if a.container != "worldline-borders-dev-db":
    sys.exit("拒絕：只允許開發庫容器 worldline-borders-dev-db。")

dry = not a.send
reason_escaped = REASON.replace("'", "''")
bio_ids_sql = ", ".join(f"'{bid}'" for bid in BIO_IDS)

sql = (
    "BEGIN;\n"
    f"UPDATE leader_records\n"
    f"  SET retracted_at = now(), retraction_reason = '{reason_escaped}'\n"
    f"  WHERE id = '{LEADER_RECORD_ID}' AND retracted_at IS NULL;\n"
    f"UPDATE leader_bios\n"
    f"  SET retracted_at = now(), retraction_reason = '{reason_escaped}'\n"
    f"  WHERE id IN ({bio_ids_sql}) AND retracted_at IS NULL;\n"
    + ("ROLLBACK;\n" if dry else "COMMIT;\n")
)

out = subprocess.run(
    ["docker", "exec", "-i", a.container,
     "psql", "-U", "worldline", "-d", "worldline_borders_dev",
     "-v", "ON_ERROR_STOP=1", "-At"],
    input=sql, capture_output=True, text=True,
)
print(out.stdout.strip())
if out.returncode != 0:
    sys.exit("FAIL：" + out.stderr[-800:])

lines = out.stdout.splitlines()
counts = [int(l.split()[-1]) for l in lines if l.startswith("UPDATE ")]
total = sum(counts)

if dry:
    print(f"（dry-run：交易已 ROLLBACK，影響 {total} 筆；明細：{counts}）")
else:
    print(f"完成：撤回 {total} 筆（leader_records: {counts[0] if counts else 0}，leader_bios: {counts[1] if len(counts) > 1 else 0}）")
