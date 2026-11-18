using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Metadata;
using Microsoft.EntityFrameworkCore.Migrations;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Tests;

/// <summary>
/// 詳細人物生平 B1（ARCHITECTURE §16.3-2、§16.4.1）：leader_record_citations 的模型與 migration 腳本。
/// 不連資料庫：只讀 EF 模型、比對 snapshot、產生 SQL 文字。連線字串指向不可能連上的埠，若意外嘗試連線會直接失敗。
/// </summary>
public class LeaderRecordCitationModelTests
{
    private const string Previous = "20261107051907_PersonPortraitAndFieldCitations";
    private const string Target = "20261110080453_LeaderRecordCitations";

    private static WorldLineDbContext NewContext()
    {
        var builder = new DbContextOptionsBuilder<WorldLineDbContext>();
        DbSetup.Configure(builder, "Host=127.0.0.1;Port=1;Database=offline_model_only;Username=none;Password=none;Timeout=1");
        return new WorldLineDbContext(builder.Options);
    }

    private static IEntityType Entity(WorldLineDbContext db) =>
        db.GetService<IDesignTimeModel>().Model.FindEntityType(typeof(LeaderRecordCitation))!;

    [Fact]
    public void Model_has_no_changes_missing_from_migrations()
    {
        using var db = NewContext();
        Assert.False(db.Database.HasPendingModelChanges());
        Assert.Contains(Target, db.Database.GetMigrations());
    }

    [Fact]
    public void Table_columns_and_nullability_follow_16_4_1()
    {
        using var db = NewContext();
        var e = Entity(db);
        Assert.Equal("leader_record_citations", e.GetTableName());

        string?[] required = ["record_id", "source_id", "locator", "quote", "accessed_on", "created_at"];
        string?[] optional = ["quote_lang", "evidence_note", "grade", "date_precision", "claim_span", "policy_version", "retracted_at", "retraction_reason"];
        var cols = e.GetProperties().ToDictionary(p => p.GetColumnName(), p => p);
        foreach (var c in required) Assert.False(cols[c!].IsNullable, $"{c} 應為 NOT NULL");
        foreach (var c in optional) Assert.True(cols[c!].IsNullable, $"{c} 應可為 NULL");
        Assert.Equal("int4range", cols["claim_span"].GetColumnType());
    }

    [Fact]
    public void Foreign_keys_point_to_leader_records_and_sources_and_never_cascade()
    {
        using var db = NewContext();
        var fks = Entity(db).GetForeignKeys().ToList();
        Assert.Equal(2, fks.Count);
        Assert.Contains(fks, f => f.PrincipalEntityType.ClrType == typeof(LeaderRecord) && f.Properties.Single().Name == nameof(LeaderRecordCitation.RecordId));
        Assert.Contains(fks, f => f.PrincipalEntityType.ClrType == typeof(Source) && f.Properties.Single().Name == nameof(LeaderRecordCitation.SourceId));
        Assert.All(fks, f => Assert.Equal(DeleteBehavior.Restrict, f.DeleteBehavior));
    }

    [Fact]
    public void Check_constraints_exist_and_grade_only_accepts_A_or_B()
    {
        using var db = NewContext();
        var checks = Entity(db).GetCheckConstraints().ToDictionary(c => c.Name!, c => c.Sql);
        Assert.Equal(
            new[]
            {
                "ck_leader_record_citations_claim_span",
                "ck_leader_record_citations_date_precision",
                "ck_leader_record_citations_grade",
                "ck_leader_record_citations_locator_not_blank",
                "ck_leader_record_citations_quote_not_blank",
                "ck_leader_record_citations_retraction_reason",
            },
            checks.Keys.Order());
        Assert.Equal("date_precision IS NULL OR date_precision IN ('day', 'month', 'year')", checks["ck_leader_record_citations_date_precision"]);
        // grade CHECK 由 BioCitationFieldsAndGaps 加上（Tai 2026-11-10 16:20）；T2：policy_version 不做檢查。
        Assert.Equal("grade IS NULL OR grade IN ('A', 'B')", checks["ck_leader_record_citations_grade"]);
        Assert.DoesNotContain(checks.Values, sql => sql.Contains("policy_version"));
    }

    [Fact]
    public void Up_script_is_additive_and_installs_I5_guard()
    {
        using var db = NewContext();
        var sql = db.GetService<IMigrator>().GenerateScript(Previous, Target);
        Assert.Contains("CREATE TABLE leader_record_citations", sql);
        Assert.Contains("CREATE INDEX ix_leader_record_citations_record_id", sql);
        Assert.Contains("CREATE INDEX ix_leader_record_citations_source_id", sql);
        Assert.Contains("CREATE TRIGGER trg_leader_record_citations_guard", sql);
        Assert.Contains("BEFORE UPDATE OR DELETE ON leader_record_citations", sql);
        // 新增式：不改、不刪既有表與資料。
        Assert.DoesNotContain("ALTER TABLE leader_records", sql);
        Assert.DoesNotContain("DROP ", sql);
        Assert.DoesNotContain("DELETE FROM", sql);
        Assert.DoesNotContain("UPDATE leader_records", sql);
    }

    [Fact]
    public void Down_script_removes_only_the_new_table_and_its_guard()
    {
        using var db = NewContext();
        var sql = db.GetService<IMigrator>().GenerateScript(Target, Previous);
        Assert.Contains("DROP TRIGGER IF EXISTS trg_leader_record_citations_guard", sql);
        Assert.Contains("DROP FUNCTION IF EXISTS fn_leader_record_citations_guard", sql);
        Assert.Contains("DROP TABLE leader_record_citations", sql);
        Assert.DoesNotContain("DROP TABLE leader_records", sql);
        Assert.DoesNotContain("DROP TABLE sources", sql);
    }
}
