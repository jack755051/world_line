using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Tests;

/// <summary>
/// 詳細人物生平 B1 其餘項目（ARCHITECTURE §16.4.1、§16.4.2、§16.6）：模型與 migration 腳本。
/// 不連資料庫：只讀 EF 模型、比對 snapshot、產生 SQL 文字（同 LeaderRecordCitationModelTests 的作法）。
/// </summary>
public class BioCitationFieldsAndGapsModelTests
{
    private const string Previous = "20261110080453_LeaderRecordCitations";
    private const string Target = "20261110082807_BioCitationFieldsAndGaps";

    private static WorldLineDbContext NewContext()
    {
        var builder = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(builder, "Host=127.0.0.1;Port=1;Database=offline_model_only;Username=none;Password=none;Timeout=1");
        return new WorldLineDbContext(builder.Options);
    }

    private static IEntityType Entity<T>(WorldLineDbContext db) =>
        db.GetService<IDesignTimeModel>().Model.FindEntityType(typeof(T))!;

    private static Dictionary<string, string> Checks<T>(WorldLineDbContext db) =>
        Entity<T>(db).GetCheckConstraints().ToDictionary(c => c.Name!, c => c.Sql);

    [Fact]
    public void Model_has_no_changes_missing_from_migrations()
    {
        using var db = NewContext();
        Assert.False(db.Database.HasPendingModelChanges());
        // 戰役 C1（2026-11-11）之後已有更新的 migration（BattleC1）；這裡只確認本 migration 仍在清單中。
        Assert.Contains(Target, db.Database.GetMigrations());
    }

    [Fact]
    public void Field_citation_new_columns_are_all_nullable()
    {
        using var db = NewContext();
        var cols = Entity<LeaderBioFieldCitation>(db).GetProperties().ToDictionary(p => p.GetColumnName(), p => p);
        foreach (var c in new[] { "quote", "quote_lang", "grade", "date_precision", "policy_version" })
            Assert.True(cols[c].IsNullable, $"{c} 應可為 NULL（舊列留空）");
        Assert.Equal(35, cols["quote_lang"].GetMaxLength());
        Assert.Equal(1, cols["grade"].GetMaxLength());
    }

    [Fact]
    public void Grade_check_field_citations_accept_ABC_leader_record_only_AB()
    {
        using var db = NewContext();
        Assert.Equal("grade IS NULL OR grade IN ('A', 'B', 'C')", Checks<LeaderBioFieldCitation>(db)["ck_leader_bio_field_citations_grade"]);
        Assert.Equal("grade IS NULL OR grade IN ('A', 'B')", Checks<LeaderRecordCitation>(db)["ck_leader_record_citations_grade"]);
    }

    [Fact]
    public void Quote_length_is_not_a_db_constraint_and_quote_lang_is_unchecked()
    {
        using var db = NewContext();
        var all = Checks<LeaderBioFieldCitation>(db).Values.Concat(Checks<LeaderRecordCitation>(db).Values).ToList();
        Assert.DoesNotContain(all, sql => sql.Contains("length(") || sql.Contains("char_length") || sql.Contains("quote_lang"));
        Assert.Equal("quote IS NULL OR btrim(quote) <> ''", Checks<LeaderBioFieldCitation>(db)["ck_leader_bio_field_citations_quote_not_blank"]);
    }

    [Fact]
    public void Field_check_includes_deathPlace_and_bios_have_death_place_object()
    {
        using var db = NewContext();
        Assert.Contains("'deathPlace'", Checks<LeaderBioFieldCitation>(db)["ck_leader_bio_field_citations_field"]);
        var bio = Entity<LeaderBio>(db);
        var dp = bio.GetProperties().Single(p => p.GetColumnName() == "death_place");
        Assert.True(dp.IsNullable);
        Assert.Equal("jsonb", dp.GetColumnType());
        Assert.Equal("death_place IS NULL OR jsonb_typeof(death_place) = 'object'", Checks<LeaderBio>(db)["ck_leader_bios_death_place_object"]);
    }

    [Fact]
    public void Gaps_table_follows_16_4_2()
    {
        using var db = NewContext();
        var e = Entity<LeaderBioGap>(db);
        Assert.Equal("leader_bio_gaps", e.GetTableName());
        var cols = e.GetProperties().ToDictionary(p => p.GetColumnName(), p => p);
        foreach (var c in new[] { "bio_id", "target", "gap_kind", "checked_on", "created_at" }) Assert.False(cols[c].IsNullable, c);
        foreach (var c in new[] { "note", "candidate_citations", "resolved_at", "resolved_by_citation_id", "retracted_at", "retraction_reason" })
            Assert.True(cols[c].IsNullable, c);
        Assert.Equal("jsonb", cols["candidate_citations"].GetColumnType());

        var fk = Assert.Single(e.GetForeignKeys());
        Assert.Equal(typeof(LeaderBio), fk.PrincipalEntityType.ClrType);
        Assert.Equal(DeleteBehavior.Restrict, fk.DeleteBehavior);

        var checks = Checks<LeaderBioGap>(db);
        Assert.Equal("gap_kind IN ('conflict', 'not_found', 'identity_uncertain')", checks["ck_leader_bio_gaps_gap_kind"]);
        Assert.Contains("ck_leader_bio_gaps_target", checks.Keys);
        Assert.Contains("ck_leader_bio_gaps_field_target", checks.Keys);

        var ix = Assert.Single(e.GetIndexes(), i => i.IsUnique);
        Assert.Equal("resolved_at IS NULL AND retracted_at IS NULL", ix.GetFilter());
    }

    [Theory]
    [InlineData("field:birthDate", true)]
    [InlineData("position:01a1b4bf-60f2-74e4-829d-0f209fb93efa", true)]
    [InlineData("paragraph:early-life", true)]
    [InlineData("role:cn-xx-premier-1920", true)]
    [InlineData("role:", false)]
    [InlineData("role: x", false)]
    [InlineData("identity", true)]
    [InlineData("birthDate", false)]
    [InlineData("field:", false)]
    [InlineData("field: x", false)]
    public void Gap_target_pattern(string target, bool ok) =>
        Assert.Equal(ok, System.Text.RegularExpressions.Regex.IsMatch(target, LeaderBioGapKinds.TargetPattern.Replace("[:space:]", @"\s")));

    [Fact]
    public void Up_script_is_additive_and_installs_gaps_guard()
    {
        using var db = NewContext();
        var sql = db.GetService<IMigrator>().GenerateScript(Previous, Target);
        Assert.Contains("ALTER TABLE leader_bio_field_citations ADD quote text;", sql);
        Assert.Contains("ALTER TABLE leader_bios ADD death_place jsonb;", sql);
        Assert.Contains("CREATE TABLE leader_bio_gaps", sql);
        Assert.Contains("CREATE TRIGGER trg_leader_bio_gaps_guard", sql);
        Assert.Contains("BEFORE UPDATE OR DELETE ON leader_bio_gaps", sql);
        // 唯一 DROP 是 field CHECK（隨即以超集重建）；不刪表、不刪欄、不刪資料、不改資料。
        var drops = sql.Split('\n').Where(l => l.Contains("DROP ")).Select(l => l.Trim()).ToList();
        Assert.Equal(["ALTER TABLE leader_bio_field_citations DROP CONSTRAINT ck_leader_bio_field_citations_field;"], drops);
        Assert.DoesNotContain("DELETE FROM", sql);
        Assert.DoesNotContain("UPDATE leader_", sql);
        Assert.DoesNotContain("ALTER COLUMN", sql);
    }

    [Fact]
    public void Down_script_restores_previous_shape()
    {
        using var db = NewContext();
        var sql = db.GetService<IMigrator>().GenerateScript(Target, Previous);
        Assert.Contains("DROP TRIGGER IF EXISTS trg_leader_bio_gaps_guard", sql);
        Assert.Contains("DROP TABLE leader_bio_gaps", sql);
        Assert.Contains("ALTER TABLE leader_bio_field_citations DROP COLUMN quote", sql);
        Assert.Contains("ALTER TABLE leader_bios DROP COLUMN death_place", sql);
        Assert.Contains("DROP CONSTRAINT ck_leader_record_citations_grade", sql);
        Assert.DoesNotContain("DROP TABLE leader_record_citations", sql);
        Assert.DoesNotContain("DROP TABLE leader_bio_field_citations", sql);
    }
}
