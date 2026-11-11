using System.Net;
using System.Text.Json;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// B3 分段生平（migration BioParagraphsPositionsRoles）：DB 約束（I5、部分唯一、角色層 position_kind、source_kind、citation 必填、jsonb）
/// 與 GET /leader-bios/{id} 的 paragraphs／positions／roles 區塊。跑在一次性測試容器，不碰 5442。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class BioParagraphsPositionsRolesTests(PostGisFixture fx)
{
    private async Task<NpgsqlConnection> OpenAsync()
    {
        var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        return c;
    }

    private static async Task<object?> Scalar(NpgsqlConnection c, string sql)
    {
        await using var cmd = new NpgsqlCommand(sql, c);
        return await cmd.ExecuteScalarAsync();
    }

    private static async Task<(Guid Bio, Guid Source)> Seed(NpgsqlConnection c)
    {
        var bio = (Guid)(await Scalar(c, "INSERT INTO leader_bios (name, is_test) VALUES ('B3 Test Person', true) RETURNING id"))!;
        var src = (Guid)(await Scalar(c, "INSERT INTO sources (source_kind, title, publisher, url) VALUES ('encyclopedia', 'Test entry', 'Test Press', 'https://example.org/b3') RETURNING id"))!;
        return (bio, src);
    }

    private static Task<object?> Para(NpgsqlConnection c, Guid bio, int ord, string body = "{\"zh-Hant\":\"文\",\"en\":\"text\"}") =>
        Scalar(c, $"INSERT INTO leader_bio_paragraphs (bio_id, ord, body) VALUES ('{bio}', {ord}, '{body}'::jsonb) RETURNING id");

    private static Task<object?> Pos(NpgsqlConnection c, Guid bio, string key, string kind = "minister") =>
        Scalar(c, $"INSERT INTO person_positions (bio_id, seed_key, title, position_kind, period) VALUES ('{bio}', '{key}', '{{\"orig\":\"x\"}}'::jsonb, '{kind}', '[1920-01-01,)') RETURNING id");

    private static Task<object?> Role(NpgsqlConnection c, Guid bio, string key, string kind = "head_of_state") =>
        Scalar(c, $"INSERT INTO person_roles (bio_id, seed_key, title, role_kind, period) VALUES ('{bio}', '{key}', '{{\"orig\":\"x\"}}'::jsonb, '{kind}', '[1920-01-01,1921-01-01)') RETURNING id");

    [Fact]
    public async Task Source_kind_accepts_encyclopedia_and_official_website_only_plus_old_values()
    {
        await using var c = await OpenAsync();
        foreach (var k in new[] { "encyclopedia", "official_website", "peer_reviewed" })
            Assert.NotNull(await Scalar(c, $"INSERT INTO sources (source_kind, title, publisher) VALUES ('{k}', 't', 'p') RETURNING id"));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, "INSERT INTO sources (source_kind, title, publisher) VALUES ('blog', 't', 'p') RETURNING id"));
    }

    [Fact]
    public async Task Paragraph_ord_unique_among_active_rows_and_body_must_be_object()
    {
        await using var c = await OpenAsync();
        var (bio, _) = await Seed(c);
        var first = await Para(c, bio, 1);
        await Assert.ThrowsAsync<PostgresException>(() => Para(c, bio, 1));
        Assert.NotNull(await Para(c, bio, 2));
        await Assert.ThrowsAsync<PostgresException>(() => Para(c, bio, 3, "[1]"));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"INSERT INTO leader_bio_paragraphs (bio_id, ord, body) VALUES ('{bio}', 0, '{{}}') RETURNING id"));
        // 撤回後同 ord 可再寫（僅有效列唯一）。
        await Scalar(c, $"UPDATE leader_bio_paragraphs SET retracted_at = now(), retraction_reason = 'rewrite' WHERE id = '{first}' RETURNING id");
        Assert.NotNull(await Para(c, bio, 1));
    }

    [Fact]
    public async Task Position_seed_key_unique_among_active_and_role_layer_kinds_rejected()
    {
        await using var c = await OpenAsync();
        var (bio, _) = await Seed(c);
        await Pos(c, bio, "k1");
        await Assert.ThrowsAsync<PostgresException>(() => Pos(c, bio, "k1"));
        foreach (var kind in new[] { "head_of_state", "head_of_government", "de_facto_leader" })
            await Assert.ThrowsAsync<PostgresException>(() => Pos(c, bio, "k-" + kind, kind));
        // 未知種類也不收；有界期間必須非空。
        await Assert.ThrowsAsync<PostgresException>(() => Pos(c, bio, "k2", "astronaut"));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"INSERT INTO person_positions (bio_id, seed_key, title, position_kind, period) VALUES ('{bio}', 'k3', '{{}}', 'other', 'empty') RETURNING id"));
    }

    [Fact]
    public async Task Role_kinds_include_cabinet_minister_and_reject_others()
    {
        await using var c = await OpenAsync();
        var (bio, _) = await Seed(c);
        foreach (var kind in new[] { "head_of_state", "head_of_government", "de_facto_leader", "cabinet_minister" })
            Assert.NotNull(await Role(c, bio, "r-" + kind, kind));
        await Assert.ThrowsAsync<PostgresException>(() => Role(c, bio, "r-bad", "occupation_administrator"));
        await Assert.ThrowsAsync<PostgresException>(() => Role(c, bio, "r-head_of_state"));
    }

    [Theory]
    [InlineData("leader_bio_paragraph_citations", "paragraph_id")]
    [InlineData("person_position_citations", "position_id")]
    [InlineData("person_role_citations", "role_id")]
    public async Task Citation_requires_locator_quote_and_grade_is_A_or_B(string table, string fk)
    {
        await using var c = await OpenAsync();
        var (bio, src) = await Seed(c);
        var parent = table switch
        {
            "leader_bio_paragraph_citations" => await Para(c, bio, 1),
            "person_position_citations" => await Pos(c, bio, "p"),
            _ => await Role(c, bio, "r"),
        };
        string Ins(string locator, string quote, string grade) =>
            $"INSERT INTO {table} ({fk}, source_id, locator, quote, accessed_on, grade) VALUES ('{parent}', '{src}', {locator}, {quote}, '2026-11-11', {grade}) RETURNING id";
        Assert.NotNull(await Scalar(c, Ins("'p. 1'", "'q'", "'A'")));
        Assert.NotNull(await Scalar(c, Ins("'p. 1'", "'q'", "NULL")));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, Ins("' '", "'q'", "'A'")));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, Ins("'p. 1'", "' '", "'A'")));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, Ins("'p. 1'", "'q'", "'C'")));
    }

    [Theory]
    [InlineData("leader_bio_paragraphs")]
    [InlineData("person_positions")]
    [InlineData("person_roles")]
    public async Task I5_no_delete_no_truncate_no_unretract(string table)
    {
        await using var c = await OpenAsync();
        var (bio, _) = await Seed(c);
        var id = table switch
        {
            "leader_bio_paragraphs" => await Para(c, bio, 1),
            "person_positions" => await Pos(c, bio, "d"),
            _ => await Role(c, bio, "d"),
        };
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"DELETE FROM {table} WHERE id = '{id}'"));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"TRUNCATE {table} CASCADE"));
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"UPDATE {table} SET retracted_at = now() WHERE id = '{id}'"));  // 缺理由
        await Scalar(c, $"UPDATE {table} SET retracted_at = now(), retraction_reason = 'x' WHERE id = '{id}' RETURNING id");
        await Assert.ThrowsAsync<PostgresException>(() => Scalar(c, $"UPDATE {table} SET retracted_at = NULL, retraction_reason = NULL WHERE id = '{id}'"));
    }

    [Fact]
    public async Task Get_bio_returns_paragraphs_positions_roles_with_citations_and_hides_retracted()
    {
        await using var c = await OpenAsync();
        var (bio, src) = await Seed(c);
        var p1 = await Para(c, bio, 1, "{\"zh-Hant\":\"第一段\",\"en\":\"one\"}");
        var p2 = await Para(c, bio, 2);
        await Scalar(c, $"UPDATE leader_bio_paragraphs SET retracted_at = now(), retraction_reason = 'x' WHERE id = '{p2}' RETURNING id");
        var pos = await Pos(c, bio, "pos-a");
        var role = await Role(c, bio, "role-a");
        await Scalar(c, $"INSERT INTO leader_bio_paragraph_citations (paragraph_id, source_id, locator, quote, quote_lang, accessed_on, grade) VALUES ('{p1}', '{src}', 'p. 2', 'quote A', 'en', '2026-11-11', 'A') RETURNING id");
        await Scalar(c, $"INSERT INTO person_position_citations (position_id, source_id, locator, quote, accessed_on, grade) VALUES ('{pos}', '{src}', 'p. 3', 'quote P', '2026-11-11', 'B') RETURNING id");
        await Scalar(c, $"INSERT INTO person_role_citations (role_id, source_id, locator, quote, accessed_on) VALUES ('{role}', '{src}', 'p. 4', 'quote R', '2026-11-11') RETURNING id");
        await Scalar(c, $"INSERT INTO leader_bio_gaps (bio_id, target, gap_kind, checked_on) VALUES ('{bio}', 'position:pos-a', 'not_found', '2026-11-11') RETURNING id");

        var k = new ApiTestKit(fx);
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leader-bios/{bio}"), HttpStatusCode.OK)).GetProperty("data");

        var pars = data.GetProperty("paragraphs");
        Assert.Equal(1, pars.GetArrayLength());
        Assert.Equal("第一段", pars[0].GetProperty("body").GetProperty("zh-Hant").GetString());
        var cite = pars[0].GetProperty("citations")[0];
        Assert.Equal("A", cite.GetProperty("grade").GetString());
        Assert.Equal("p. 2", cite.GetProperty("locator").GetString());
        Assert.Equal("quote A", cite.GetProperty("quote").GetString());
        Assert.Equal("en", cite.GetProperty("quoteLang").GetString());
        Assert.Equal("2026-11-11", cite.GetProperty("accessedOn").GetString());
        Assert.Equal("Test entry", cite.GetProperty("source").GetProperty("title").GetString());
        Assert.Equal("https://example.org/b3", cite.GetProperty("source").GetProperty("url").GetString());
        Assert.Equal("Test Press", cite.GetProperty("source").GetProperty("publisher").GetString());

        var positions = data.GetProperty("positions");
        Assert.Equal("minister", positions[0].GetProperty("positionKind").GetString());
        Assert.Equal("quote P", positions[0].GetProperty("citations")[0].GetProperty("quote").GetString());
        Assert.Equal(JsonValueKind.Null, positions[0].GetProperty("period").GetProperty("end").ValueKind);

        var roles = data.GetProperty("roles");
        Assert.Equal("head_of_state", roles[0].GetProperty("roleKind").GetString());
        Assert.Equal("quote R", roles[0].GetProperty("citations")[0].GetProperty("quote").GetString());
        Assert.Equal("position:pos-a", data.GetProperty("gaps")[0].GetProperty("target").GetString());
    }

    [Fact]
    public async Task Get_bio_without_paragraphs_still_works_and_keeps_summary()
    {
        await using var c = await OpenAsync();
        var bio = (Guid)(await Scalar(c, "INSERT INTO leader_bios (name, summary, is_test) VALUES ('No Paragraph Person', '{\"zh-Hant\":\"一句話\",\"en\":\"one line\"}'::jsonb, true) RETURNING id"))!;
        var k = new ApiTestKit(fx);
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leader-bios/{bio}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("一句話", data.GetProperty("summary").GetProperty("zh-Hant").GetString());
        Assert.Equal(0, data.GetProperty("paragraphs").GetArrayLength());
        Assert.Equal(0, data.GetProperty("positions").GetArrayLength());
        Assert.Equal(0, data.GetProperty("roles").GetArrayLength());
    }
}
