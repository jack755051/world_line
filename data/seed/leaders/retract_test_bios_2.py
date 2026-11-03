#!/usr/bin/env python3
"""
軟撤回其餘 3 筆測試生平（bios_test_seed.py 重跑時多建、e1bd309 未涵蓋者）。做法同 retract_test_bios.py。

撤回對象（leader_bios，皆 is_test=true，未接任何任期）：
  01a19ef6-b466-7e2e-94e1-8ec3c0e5ac10  Winston Churchill
  01a19ef9-1bcf-763e-9c99-0b9b37660da1  Adolf Hitler
  01a19ef9-1c0b-781a-911b-adc230abbeaf  Winston Churchill

只填 retracted_at＋retraction_reason，不 DELETE；WHERE 另加 is_test=true 防呆。只針對 worldline-borders-dev-db。

用法：
  python3 retract_test_bios_2.py           # dry-run（預設）：交易中執行後 ROLLBACK
  python3 retract_test_bios_2.py --send    # COMMIT
"""
import argparse, subprocess, sys

REASON = "測試種子，未經考證"
BIO_IDS = [
    "01a19ef6-b466-7e2e-94e1-8ec3c0e5ac10",  # Winston Churchill
    "01a19ef9-1bcf-763e-9c99-0b9b37660da1",  # Adolf Hitler
    "01a19ef9-1c0b-781a-911b-adc230abbeaf",  # Winston Churchill
]

ap = argparse.ArgumentParser(description="軟撤回其餘測試生平")
ap.add_argument("--send", action="store_true", help="實際 COMMIT（預設 dry-run，交易後 ROLLBACK）")
ap.add_argument("--container", default="worldline-borders-dev-db")
a = ap.parse_args()
if a.container != "worldline-borders-dev-db":
    sys.exit("拒絕：只允許開發庫容器 worldline-borders-dev-db。")

dry = not a.send
reason = REASON.replace("'", "''")
ids = ", ".join(f"'{b}'" for b in BIO_IDS)
sql = (
    "BEGIN;\n"
    f"UPDATE leader_bios SET retracted_at = now(), retraction_reason = '{reason}'\n"
    f"  WHERE id IN ({ids}) AND is_test AND retracted_at IS NULL;\n"
    "SELECT 'linked_active', count(*) FROM leader_records WHERE retracted_at IS NULL AND person_id IN (" + ids + ");\n"
    "SELECT 'test_unretracted', count(*) FROM leader_bios WHERE is_test AND retracted_at IS NULL;\n"
    + ("ROLLBACK;\n" if dry else "COMMIT;\n")
)
out = subprocess.run(["docker", "exec", "-i", a.container, "psql", "-U", "worldline", "-d", "worldline_borders_dev",
                      "-v", "ON_ERROR_STOP=1", "-At"], input=sql, capture_output=True, text=True)
print(out.stdout.strip())
if out.returncode != 0:
    sys.exit("FAIL：" + out.stderr[-800:])
n = sum(int(l.split()[-1]) for l in out.stdout.splitlines() if l.startswith("UPDATE "))
print(f"（dry-run：交易已 ROLLBACK，影響 {n} 筆）" if dry else f"完成：撤回 leader_bios {n} 筆")
