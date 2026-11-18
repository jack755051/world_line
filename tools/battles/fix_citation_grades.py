"""更正已寫入開發庫的戰役引文等級：取消「單一來源降一級」後，引文等級要回到來源本身的等級（docs/source-rules.md D2）。
用法：python3 -I tools/battles/fix_citation_grades.py <battle> [--apply]
- 依 I5「撤回＋重寫」：等級不符的引文不改原列，而是寫一筆等級正確的新列，再把舊列標為撤回並註明原因。
- 同時把 sources.grade／grade_basis 設成考證檔 sources.json 的值。
- 只連 5442 開發庫的容器（同 db_write.py）；預設整個交易最後 ROLLBACK，--apply 才 COMMIT。可重跑（已更正的不會再動）。
"""
import json, subprocess, sys, uuid
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]
NS = uuid.uuid5(uuid.NAMESPACE_URL, "https://worldline.local/battle-seed")   # 同 write_battle_sql.py
CONTAINER, DB = "worldline-borders-dev-db", "worldline_borders_dev"
TABLES = ["battle_profile_citations", "battle_phase_citations", "battle_map_feature_citations", "battle_unit_citations"]
REASON = "來源等級更正：取消單一來源降一級，引文等級回到來源本身的等級（docs/source-rules.md D2，Tai 2026-11-13）"


def q(s): return "'" + str(s).replace("'", "''") + "'"


def main():
    battle = sys.argv[1]; apply = "--apply" in sys.argv
    src = json.loads((REPO / "data/seed/battles" / battle / "sources.json").read_text()); src = src.get("sources", src)
    rows = [(str(uuid.uuid5(NS, "source|" + k)), v["grade"], v.get("gradeBasis") or "見考證檔 sources.json") for k, v in src.items() if isinstance(v, dict) and v.get("grade") in ("A", "B")]
    vals = ", ".join(f"({q(i)}::uuid, {q(g)}, {q(b)})" for i, g, b in rows)
    sql = ["\\set ON_ERROR_STOP on", "BEGIN;", f"CREATE TEMP TABLE wl_fix (source_id uuid, grade text, basis text) ON COMMIT DROP; INSERT INTO wl_fix VALUES {vals};",
           "UPDATE sources s SET grade = f.grade, grade_basis = f.basis, updated_at = now(), version = s.version + 1 FROM wl_fix f WHERE s.id = f.source_id AND (s.grade IS DISTINCT FROM f.grade OR s.grade_basis IS DISTINCT FROM f.basis);",
           "SELECT 'sources', s.id, s.grade FROM sources s JOIN wl_fix f ON f.source_id = s.id ORDER BY 2;"]
    for t in TABLES:
        sql += [f"CREATE TEMP TABLE wl_old_{t} ON COMMIT DROP AS SELECT c.id, f.grade AS want FROM {t} c JOIN wl_fix f ON f.source_id = c.source_id WHERE c.retracted_at IS NULL AND c.grade <> f.grade;",
                f"INSERT INTO {t} SELECT (jsonb_populate_record(NULL::{t}, to_jsonb(c) || jsonb_build_object('id', gen_random_uuid(), 'grade', o.want, 'created_at', now()))).* FROM {t} c JOIN wl_old_{t} o ON o.id = c.id;",
                f"UPDATE {t} c SET retracted_at = now(), retraction_reason = {q(REASON)} FROM wl_old_{t} o WHERE o.id = c.id;",
                f"SELECT '{t}', (SELECT count(*) FROM wl_old_{t}) AS corrected, (SELECT string_agg(g || '=' || n, ' ' ORDER BY g) FROM (SELECT c.grade g, count(*) n FROM {t} c JOIN wl_fix f ON f.source_id = c.source_id WHERE c.retracted_at IS NULL GROUP BY 1) x);"]
    sql.append("COMMIT;" if apply else "ROLLBACK;")
    p = subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c", f'psql -X -q -At -F "|" -U "$POSTGRES_USER" -d {DB}'], input="\n".join(sql) + "\n", capture_output=True, text=True)
    out = p.stdout + ("\n[stderr]\n" + p.stderr if p.stderr.strip() else "") + f"\n[exit {p.returncode}] {'COMMIT' if apply and p.returncode == 0 else 'ROLLBACK'}\n"
    (REPO / "data/seed/battles" / battle / "db" / f"{battle}.regrade.{'apply' if apply else 'dry-run'}.txt").write_text(out)
    print(out); sys.exit(p.returncode)


if __name__ == "__main__":
    main()
