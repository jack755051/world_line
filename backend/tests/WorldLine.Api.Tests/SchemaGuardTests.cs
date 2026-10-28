using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>DB 層規則（PRD §6.2 規則落點表）：I1 CHECK、I4／代稱視角 CHECK、R7 publisher、I5 trigger。</summary>
[Collection(PostGisCollection.Name)]
public sealed class SchemaGuardTests(PostGisFixture fx)
{
    private const string Square = "ST_Multi(ST_GeomFromText('POLYGON((0 0,1 0,1 1,0 1,0 0))',4326))";

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

    /// <summary>以 SQL 建一筆完整的控制紀錄版本，回傳 (versionId)。</summary>
    private static async Task<Guid> SeedVersionAsync(NpgsqlConnection c)
    {
        var tag = Guid.NewGuid().ToString("N")[..8];
        var sql = $"""
            WITH s AS (INSERT INTO sources (source_kind, title, publisher) VALUES ('atlas_map', 't', 'p') RETURNING id),
                 r AS (INSERT INTO regimes (slug) VALUES ('schema-{tag}') RETURNING id),
                 th AS (INSERT INTO theaters (code, name) VALUES ('th-{tag}', '{"{"}"en":"x"{"}"}') RETURNING id),
                 sn AS (INSERT INTO control_snapshots (theater_id, as_of) SELECT id, DATE '1940-07-15' FROM th RETURNING id),
                 cr AS (INSERT INTO control_records (controller_regime_id) SELECT id FROM r RETURNING id),
                 v AS (INSERT INTO control_record_versions (control_record_id, snapshot_id, control_type, valid_period, geom)
                       SELECT cr.id, sn.id, 'military_occupation', daterange('1940-06-25','1942-11-11'), {Square} FROM cr, sn RETURNING id)
            SELECT id FROM v
            """;
        return (Guid)(await ScalarAsync(c, sql))!;
    }

    [Fact]
    public async Task Extensions_postgis_and_btree_gist_are_installed()
    {
        await using var c = await OpenAsync();
        var n = (long)(await ScalarAsync(c, "SELECT count(*) FROM pg_extension WHERE extname IN ('postgis','btree_gist')"))!;
        Assert.Equal(2, n);
    }

    [Fact]
    public async Task I5_versions_cannot_be_deleted()
    {
        await using var c = await OpenAsync();
        var id = await SeedVersionAsync(c);
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            ScalarAsync(c, $"DELETE FROM control_record_versions WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
    }

    [Fact]
    public async Task I5_sources_cannot_be_deleted_or_truncated()
    {
        await using var c = await OpenAsync();
        await SeedVersionAsync(c);
        var del = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, "DELETE FROM sources"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, del.SqlState);
        var trunc = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, "TRUNCATE sources CASCADE"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, trunc.SqlState);
    }

    [Fact]
    public async Task I5_version_content_cannot_be_updated()
    {
        await using var c = await OpenAsync();
        var id = await SeedVersionAsync(c);
        var ex = await Assert.ThrowsAsync<PostgresException>(() =>
            ScalarAsync(c, $"UPDATE control_record_versions SET control_type = 'direct_rule' WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
    }

    [Fact]
    public async Task I5_old_version_may_be_superseded_once_then_frozen()
    {
        await using var c = await OpenAsync();
        var oldId = await SeedVersionAsync(c);
        var newId = (Guid)(await ScalarAsync(c, $"""
            INSERT INTO control_record_versions (control_record_id, snapshot_id, control_type, valid_period, geom, revision_reason)
            SELECT control_record_id, snapshot_id, 'military_occupation', daterange('1940-06-25','1942-11-12'), geom, '修正迄日'
            FROM control_record_versions WHERE id = '{oldId}' RETURNING id
            """))!;

        await ScalarAsync(c, $"UPDATE control_record_versions SET superseded_by = '{newId}', superseded_at = now() WHERE id = '{oldId}'");

        var again = await Assert.ThrowsAsync<PostgresException>(() =>
            ScalarAsync(c, $"UPDATE control_record_versions SET superseded_at = now() WHERE id = '{oldId}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, again.SqlState);
    }

    [Fact]
    public async Task I1_unbounded_valid_period_is_rejected()
    {
        await using var c = await OpenAsync();
        var id = await SeedVersionAsync(c);
        var ex = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"""
            INSERT INTO control_record_versions (control_record_id, snapshot_id, control_type, valid_period, geom)
            SELECT control_record_id, snapshot_id, 'military_occupation', daterange('1940-06-25', NULL), geom
            FROM control_record_versions WHERE id = '{id}'
            """));
        Assert.Equal(PostgresErrorCodes.CheckViolation, ex.SqlState);
        Assert.Equal("ck_crv_valid_period_bounded", ex.ConstraintName);
    }

    [Fact]
    public async Task R9_missing_data_is_not_a_control_type()
    {
        await using var c = await OpenAsync();
        var id = await SeedVersionAsync(c);
        var ex = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"""
            INSERT INTO control_record_versions (control_record_id, snapshot_id, control_type, valid_period, geom)
            SELECT control_record_id, snapshot_id, 'no_data', valid_period, geom
            FROM control_record_versions WHERE id = '{id}'
            """));
        Assert.Equal("ck_crv_control_type", ex.ConstraintName);
    }

    [Fact]
    public async Task Exonym_requires_observer_and_publisher_cannot_be_blank()
    {
        await using var c = await OpenAsync();
        var slug = "exo-" + Guid.NewGuid().ToString("N")[..8];
        var exo = await Assert.ThrowsAsync<PostgresException>(() => ScalarAsync(c, $"""
            WITH r AS (INSERT INTO regimes (slug) VALUES ('{slug}') RETURNING id)
            INSERT INTO regime_names (regime_id, name_kind, original_text, original_lang, display)
            SELECT id, 'exonym', 'Vichy France', 'en', '{"{"}"en":"Vichy France"{"}"}' FROM r
            """));
        Assert.Equal("ck_regime_names_exonym_observer", exo.ConstraintName);

        var pub = await Assert.ThrowsAsync<PostgresException>(() =>
            ScalarAsync(c, "INSERT INTO sources (source_kind, title, publisher) VALUES ('map', 't', '  ')"));
        Assert.Equal("ck_sources_publisher_not_blank", pub.ConstraintName);
    }
}
