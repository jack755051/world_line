using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 詳細人物生平 B1：BioCitationFieldsAndGaps 的 DB 層規則（grade CHECK、quote 不可空白但不限長、deathPlace、leader_bio_gaps 的 I5 trigger）。
/// 跑在 PostGisFixture 的一次性容器（不碰任何既有資料庫）。
/// 2026-11-10：已寫、未執行——Tai 16:20 核准範圍規定新 migration 不套用到任何庫（含測試容器），執行前需再核准。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class BioCitationFieldsAndGapsGuardTests(PostGisFixture fx)
{
    private async Task<NpgsqlConnection> OpenAsync()
    {
        var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        return c;
    }

    private static async Task<object?> ScalarAsync(NpgsqlConnection c, string sql)
    {
        await using var cmd = new NpgsqlCommand(sql, c);
        return await cmd.ExecuteScalarAsync();
    }

    private static async Task<(Guid Bio, Guid Source)> SeedAsync(NpgsqlConnection c)
    {
        var bio = (Guid)(await ScalarAsync(c, "INSERT INTO leader_bios (name) VALUES ('Gap Test Person') RETURNING id"))!;
        var src = (Guid)(await ScalarAsync(c,
            "INSERT INTO sources (source_kind, title, publisher) VALUES ('official_record', 'Gap test source', 'Test archive') RETURNING id"))!;
        return (bio, src);
    }

    private static string FieldCitation(Guid bio, Guid src, string field, string quote, string grade) => $"""
        INSERT INTO leader_bio_field_citations (bio_id, field, source_id, locator, accessed_on, quote, grade)
        VALUES ('{bio}', '{field}', '{src}', 'p. 1', '2026-11-10', {quote}, {grade}) RETURNING id
        """;

    [Theory]
    [InlineData("'X'")]
    [InlineData("'a'")]
    public async Task Grade_outside_A_B_C_is_rejected(string grade)
    {
        await using var c = await OpenAsync();
        var (bio, src) = await SeedAsync(c);
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, FieldCitation(bio, src, "birthDate", "'b. 1862'", grade)));
    }

    [Fact]
    public async Task Grade_C_is_accepted()
    {
        await using var c = await OpenAsync();
        var (bio, src) = await SeedAsync(c);
        Assert.NotNull(await ScalarAsync(c, FieldCitation(bio, src, "birthDate", "'b. 1862'", "'C'")));
    }

    [Fact]
    public async Task Long_quote_is_accepted_by_db_but_blank_quote_is_not()
    {
        await using var c = await OpenAsync();
        var (bio, src) = await SeedAsync(c);
        // 80 字上限只在程式檢查（BioSourcePolicy），DB 不擋。
        Assert.NotNull(await ScalarAsync(c, FieldCitation(bio, src, "deathPlace", $"'{new string('x', 200)}'", "'A'")));
        Assert.NotNull(await ScalarAsync(c, FieldCitation(bio, src, "deathDate", "NULL", "NULL")));
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, FieldCitation(bio, src, "deathDate", "'  '", "NULL")));
    }

    [Fact]
    public async Task Gap_rows_cannot_be_deleted_and_resolution_is_irreversible()
    {
        await using var c = await OpenAsync();
        var (bio, _) = await SeedAsync(c);
        var gap = await ScalarAsync(c, $"""
            INSERT INTO leader_bio_gaps (bio_id, target, gap_kind, note, checked_on, candidate_citations)
            VALUES ('{bio}', 'field:birthDate', 'conflict', 'BnF 1873 vs 1874', '2026-11-10', '[]') RETURNING id
            """);
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"DELETE FROM leader_bio_gaps WHERE id = '{gap}'"));
        await ScalarAsync(c, $"UPDATE leader_bio_gaps SET resolved_at = now() WHERE id = '{gap}'");
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"UPDATE leader_bio_gaps SET resolved_at = NULL WHERE id = '{gap}'"));
    }

    [Theory]
    [InlineData("'birthDate'", "'conflict'")] // 缺前綴
    [InlineData("'field:height'", "'conflict'")] // 欄位不在值域
    [InlineData("'field:birthDate'", "'unknown'")] // gap_kind 不在值域
    public async Task Gap_target_and_kind_are_checked(string target, string kind)
    {
        await using var c = await OpenAsync();
        var (bio, _) = await SeedAsync(c);
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c,
            $"INSERT INTO leader_bio_gaps (bio_id, target, gap_kind, checked_on) VALUES ('{bio}', {target}, {kind}, '2026-11-10')"));
    }

    [Fact]
    public async Task Only_one_open_gap_per_bio_target_kind()
    {
        await using var c = await OpenAsync();
        var (bio, _) = await SeedAsync(c);
        var sql = $"INSERT INTO leader_bio_gaps (bio_id, target, gap_kind, checked_on) VALUES ('{bio}', 'field:party', 'not_found', '2026-11-10') RETURNING id";
        await ScalarAsync(c, sql);
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, sql));
    }
}
