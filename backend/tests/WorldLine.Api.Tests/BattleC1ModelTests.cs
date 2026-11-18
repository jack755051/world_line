using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Tests;

/// <summary>
/// 戰役 C1 migration（ARCHITECTURE §19.1）：模型與 migration 腳本。不連資料庫、不啟動容器：
/// 只讀 EF 模型、比對 snapshot、產生 SQL 文字（同 BioCitationFieldsAndGapsModelTests 的作法）。
/// </summary>
public class BattleC1ModelTests
{
    private const string Previous = "20261110082807_BioCitationFieldsAndGaps";
    private const string Target = "20261111053803_BattleC1";

    private static readonly string[] Tables =
    [
        "battle_profiles", "battle_phases", "battle_map_features", "battle_units",
        "battle_profile_citations", "battle_phase_citations", "battle_map_feature_citations", "battle_unit_citations",
    ];

    private static WorldLineDbContext NewContext()
    {
        var builder = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(builder, "Host=127.0.0.1;Port=1;Database=offline_model_only;Username=none;Password=none;Timeout=1");
        return new WorldLineDbContext(builder.Options);
    }

    private static string Script(WorldLineDbContext db) =>
        db.GetService<IMigrator>().GenerateScript(Previous, Target);

    [Fact]
    public void Model_has_no_changes_missing_from_migrations()
    {
        using var db = NewContext();
        Assert.False(db.Database.HasPendingModelChanges());
        // 之後的 migration（例如 B3 BioParagraphsPositionsRoles）排在 BattleC1 後面，故只檢查 BattleC1 仍在清單內。
        Assert.Contains(Target, db.Database.GetMigrations());
        // C2a：新增式的 BattleEventKindOperation（event_kind 值域加 operation，只放寬 CHECK）也在清單內。
        Assert.Contains("20261111065550_BattleEventKindOperation", db.Database.GetMigrations());
    }

    [Fact]
    public void Migration_is_additive_only()
    {
        using var db = NewContext();
        var sql = Script(db);
        foreach (var t in Tables) Assert.Contains($"CREATE TABLE {t} (", sql);
        Assert.DoesNotContain("ALTER TABLE leader", sql);
        Assert.DoesNotContain("ALTER TABLE historical_events", sql);
        Assert.DoesNotContain("DROP TABLE", sql);
        Assert.DoesNotContain("DROP COLUMN", sql);
        // 不建 C3／C4 的表。
        Assert.DoesNotContain("person_event_participations", sql);
        Assert.DoesNotContain("battle_figures", sql);
    }

    [Fact]
    public void Every_table_has_I5_guard_trigger_and_retraction_check()
    {
        using var db = NewContext();
        var sql = Script(db);
        foreach (var t in Tables)
        {
            Assert.Contains($"CREATE TRIGGER trg_{t}_guard BEFORE UPDATE OR DELETE ON {t}", sql);
            Assert.Contains($"ck_{t}_retraction_reason", sql);
        }
    }

    [Fact]
    public void Citation_tables_use_unified_fields_and_grade_A_or_B()
    {
        using var db = NewContext();
        var model = db.GetService<IDesignTimeModel>().Model;
        foreach (var type in new[] { typeof(BattleProfileCitation), typeof(BattlePhaseCitation), typeof(BattleMapFeatureCitation), typeof(BattleUnitCitation) })
        {
            var e = model.FindEntityType(type)!;
            var cols = e.GetProperties().ToDictionary(p => p.GetColumnName());
            foreach (var c in new[] { "source_id", "locator", "quote", "accessed_on", "grade", "date_precision", "policy_version", "retracted_at", "retraction_reason" })
                Assert.True(cols.ContainsKey(c), $"{e.GetTableName()} 缺 {c}");
            Assert.False(cols["quote"].IsNullable);
            Assert.False(cols["grade"].IsNullable);
            var grade = e.GetCheckConstraints().Single(x => x.Name!.EndsWith("_grade", StringComparison.Ordinal));
            Assert.Equal("grade IN ('A', 'B')", grade.Sql);
        }
    }

    [Fact]
    public void Map_feature_checks_follow_section_19_1_3()
    {
        using var db = NewContext();
        var checks = db.GetService<IDesignTimeModel>().Model.FindEntityType(typeof(BattleMapFeature))!
            .GetCheckConstraints().ToDictionary(c => c.Name!, c => c.Sql);
        Assert.Equal("geom_basis <> 'derived' OR status <> 'verified'", checks["ck_battle_map_features_derived_not_verified"]);
        Assert.Contains("feature_kind = 'site' AND GeometryType(geom) = 'POINT'", checks["ck_battle_map_features_geom_kind"]);
        Assert.Contains("feature_kind = 'arrow' AND GeometryType(geom) = 'LINESTRING'", checks["ck_battle_map_features_geom_kind"]);
    }
}
