using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 詳細人物生平 B1：leader_record_citations 的 DB 層規則（I5 trigger、CHECK、FK）。
/// 跑在 PostGisFixture 的一次性容器（不碰任何既有資料庫）；屬 §16.7 B1 驗收「migration 在乾淨庫通過、I5 trigger」，
/// 需 Tai 核准後才執行。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class LeaderRecordCitationGuardTests(PostGisFixture fx)
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

    private static Task ExecAsync(NpgsqlConnection c, string sql) => ScalarAsync(c, sql);

    /// <summary>以 SQL 建一筆來源與一筆任期，回傳 (recordId, sourceId)。</summary>
    private static async Task<(Guid Record, Guid Source)> SeedAsync(NpgsqlConnection c)
    {
        var tag = Guid.NewGuid().ToString("N")[..8];
        var src = (Guid)(await ScalarAsync(c,
            "INSERT INTO sources (source_kind, title, publisher) VALUES ('official_record', 'Test record source', 'Test archive') RETURNING id"))!;
        var rec = (Guid)(await ScalarAsync(c, $"""
            WITH r AS (INSERT INTO regimes (slug) VALUES ('lrc-{tag}') RETURNING id)
            INSERT INTO leader_records (regime_id, name, role, valid_period, source)
            SELECT id, 'Test Leader', 'head_of_state', daterange('1930-01-01', '1935-01-01'), 'Test note' FROM r
            RETURNING id
            """))!;
        return (rec, src);
    }

    private static string Insert(Guid rec, Guid src, string locator = "'p. 12'", string quote = "'took office 1 January 1930'",
        string grade = "NULL", string precision = "'day'", string span = "NULL") => $"""
        INSERT INTO leader_record_citations (record_id, source_id, locator, quote, quote_lang, accessed_on, grade, date_precision, claim_span)
        VALUES ('{rec}', '{src}', {locator}, {quote}, 'en', DATE '2026-11-10', {grade}, {precision}, {span})
        RETURNING id
        """;

    [Theory]
    [InlineData("'C'")]
    [InlineData("'X'")]
    public async Task Leader_record_citation_still_rejects_grade_C_and_X(string grade)
    {
        await using var c = await OpenAsync();
        var (rec, src) = await SeedAsync(c);
        await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, Insert(rec, src, grade: grade)));
    }

    [Fact]
    public async Task Valid_citation_is_written_with_defaults()
    {
        await using var c = await OpenAsync();
        var (rec, src) = await SeedAsync(c);
        var id = (Guid)(await ScalarAsync(c, Insert(rec, src, span: "int4range(0, 2)")))!;
        Assert.Equal(true, await ScalarAsync(c, $"SELECT created_at IS NOT NULL AND retracted_at IS NULL FROM leader_record_citations WHERE id = '{id}'"));
    }

    [Theory]
    [InlineData("'  '", "'quote'", "'day'", "NULL")]          // locator 空白
    [InlineData("'p. 1'", "' '", "'day'", "NULL")]            // quote 空白
    [InlineData("'p. 1'", "'quote'", "'decade'", "NULL")]     // 精度不在值域
    [InlineData("'p. 1'", "'quote'", "'day'", "'empty'::int4range")]       // claim_span 空區間
    [InlineData("'p. 1'", "'quote'", "'day'", "int4range(-1, 2)")]         // claim_span 負序號
    public async Task Check_constraints_reject_invalid_rows(string locator, string quote, string precision, string span)
    {
        await using var c = await OpenAsync();
        var (rec, src) = await SeedAsync(c);
        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, Insert(rec, src, locator, quote, precision: precision, span: span)));
    }

    [Fact]
    public async Task Unknown_record_or_source_is_rejected_by_foreign_keys()
    {
        await using var c = await OpenAsync();
        var (rec, src) = await SeedAsync(c);
        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, Insert(Guid.NewGuid(), src)));
        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, Insert(rec, Guid.NewGuid())));
    }

    [Fact]
    public async Task I5_citation_cannot_be_deleted_and_retraction_is_irreversible()
    {
        await using var c = await OpenAsync();
        var (rec, src) = await SeedAsync(c);
        var id = (Guid)(await ScalarAsync(c, Insert(rec, src)))!;

        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, $"DELETE FROM leader_record_citations WHERE id = '{id}'"));
        // 撤回必須附原因
        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, $"UPDATE leader_record_citations SET retracted_at = now() WHERE id = '{id}'"));
        await ExecAsync(c, $"UPDATE leader_record_citations SET retracted_at = now(), retraction_reason = 'test' WHERE id = '{id}'");
        await Assert.ThrowsAsync<PostgresException>(() =>
            ExecAsync(c, $"UPDATE leader_record_citations SET retracted_at = NULL, retraction_reason = NULL WHERE id = '{id}'"));
        // 被引用的任期不能被連帶刪除（FK RESTRICT；leader_records 本身亦受 I5 保護）
        await Assert.ThrowsAsync<PostgresException>(() => ExecAsync(c, $"DELETE FROM leader_records WHERE id = '{rec}'"));
    }
}
