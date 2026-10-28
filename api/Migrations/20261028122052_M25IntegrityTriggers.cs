using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Migrations
{
    /// <summary>
    /// M2.5 的 DB 層縱深防禦（手寫 SQL，延續 M2IntegrityTriggers）：
    /// - I5：控制關係、同盟陣營、陣營他稱、陣營成員 一律禁止 DELETE／TRUNCATE；UPDATE 必須附修改原因並寫入 data_revisions。
    /// - I6：同一控制方／被控制方／控制類型的「非爭議」控制關係期間不可重疊（排除約束）。
    /// - 陣營成員：同一政權在同一陣營的成員期間不可重疊（退出後再加入要新增一筆不重疊的紀錄）。
    /// - §4：狀態機 guard 允許 existing → annexed（被併吞）。
    /// - 疆域 guard：精度欄位也屬不可覆蓋內容（改精度＝改期間，只能出新版本）。
    /// </summary>
    public partial class M25IntegrityTriggers : Migration
    {
        private static readonly string[] NewTables =
            ["regime_control_relations", "alliances", "alliance_aliases", "alliance_memberships"];

        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql(@"
ALTER TABLE regime_control_relations
  ADD CONSTRAINT ex_regime_control_relations_no_overlap
  EXCLUDE USING gist (controller_regime_id WITH =, controlled_regime_id WITH =, control_type WITH =, valid_period WITH &&)
  WHERE (NOT is_disputed);

ALTER TABLE alliance_memberships
  ADD CONSTRAINT ex_alliance_memberships_no_overlap
  EXCLUDE USING gist (alliance_id WITH =, regime_id WITH =, valid_period WITH &&);");

            migrationBuilder.Sql(@"
CREATE OR REPLACE FUNCTION wl_regimes_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT (OLD.status = 'existing' AND NEW.status IN ('split', 'abdicated', 'destroyed', 'annexed')) THEN
    RAISE EXCEPTION '憲法 §4: 不合法的政權狀態轉換 % -> %', OLD.status, NEW.status
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'regimes.id / created_at 不可修改' USING ERRCODE = 'check_violation';
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION wl_regime_territories_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.superseded_by IS NOT NULL THEN
    RAISE EXCEPTION 'I5: 已被取代的疆域版本 % 不可再修改', OLD.id USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.regime_id IS DISTINCT FROM OLD.regime_id
     OR NEW.valid_period IS DISTINCT FROM OLD.valid_period
     OR NEW.valid_from_precision IS DISTINCT FROM OLD.valid_from_precision
     OR NEW.valid_to_precision IS DISTINCT FROM OLD.valid_to_precision
     OR NEW.geom IS DISTINCT FROM OLD.geom
     OR NEW.is_disputed IS DISTINCT FROM OLD.is_disputed
     OR NEW.is_illustrative IS DISTINCT FROM OLD.is_illustrative
     OR NEW.source IS DISTINCT FROM OLD.source
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'I5: 疆域內容不可覆蓋；請新增新版本並把舊版本的 superseded_by 指向它'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END
$$;");

            foreach (var table in NewTables)
            {
                migrationBuilder.Sql($@"
CREATE TRIGGER trg_00_{table}_forbid_delete BEFORE DELETE ON {table}
  FOR EACH ROW EXECUTE FUNCTION wl_forbid_delete();
CREATE TRIGGER trg_00_{table}_forbid_truncate BEFORE TRUNCATE ON {table}
  FOR EACH STATEMENT EXECUTE FUNCTION wl_forbid_delete();
CREATE TRIGGER trg_20_{table}_revision BEFORE UPDATE ON {table}
  FOR EACH ROW EXECUTE FUNCTION wl_record_revision();");
            }
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            foreach (var table in NewTables)
                migrationBuilder.Sql($@"
DROP TRIGGER IF EXISTS trg_20_{table}_revision ON {table};
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_delete ON {table};
DROP TRIGGER IF EXISTS trg_00_{table}_forbid_truncate ON {table};");

            migrationBuilder.Sql(@"
ALTER TABLE alliance_memberships DROP CONSTRAINT IF EXISTS ex_alliance_memberships_no_overlap;
ALTER TABLE regime_control_relations DROP CONSTRAINT IF EXISTS ex_regime_control_relations_no_overlap;

CREATE OR REPLACE FUNCTION wl_regimes_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM OLD.status
     AND NOT (OLD.status = 'existing' AND NEW.status IN ('split', 'abdicated', 'destroyed')) THEN
    RAISE EXCEPTION '憲法 §4: 不合法的政權狀態轉換 % -> %', OLD.status, NEW.status
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'regimes.id / created_at 不可修改' USING ERRCODE = 'check_violation';
  END IF;
  NEW.updated_at := now();
  RETURN NEW;
END
$$;

CREATE OR REPLACE FUNCTION wl_regime_territories_guard() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.superseded_by IS NOT NULL THEN
    RAISE EXCEPTION 'I5: 已被取代的疆域版本 % 不可再修改', OLD.id USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.id IS DISTINCT FROM OLD.id
     OR NEW.regime_id IS DISTINCT FROM OLD.regime_id
     OR NEW.valid_period IS DISTINCT FROM OLD.valid_period
     OR NEW.geom IS DISTINCT FROM OLD.geom
     OR NEW.is_disputed IS DISTINCT FROM OLD.is_disputed
     OR NEW.is_illustrative IS DISTINCT FROM OLD.is_illustrative
     OR NEW.source IS DISTINCT FROM OLD.source
     OR NEW.created_at IS DISTINCT FROM OLD.created_at THEN
    RAISE EXCEPTION 'I5: 疆域內容不可覆蓋；請新增新版本並把舊版本的 superseded_by 指向它'
      USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END
$$;");
        }
    }
}
