using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 2026-10-31（使用者拍板，實作為 AI 提案・待拍板）：
/// 1. 陣營「補充」：事件參與方＋事件引用（PRD §6.3 event_participants／event_citations），GET /control 帶 controllerSupplements；
/// 2. 陣營切片撤回（I5：只寫一次撤回，撤回後可重新分段）；
/// 3. 控制資料缺（R9）：control_coverage_notes，不可與現行控制紀錄重疊，GET /control 帶 coverageNotes。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SupplementsAndGapsTests(PostGisFixture fx)
{
    private static object Cite(Guid source, string locator) => new { sourceId = source, locator, evidenceNote = "測試依據" };

    private static object Event(string start, string end, Guid[] belligerents, params object[] citations) => new
    {
        eventKind = "war",
        occurred = new { start, end },
        datePrecision = "day",
        summary = new Dictionary<string, string> { ["zh-Hant"] = "宣戰", ["en"] = "Declaration of war" },
        participants = belligerents.Select(b => new { regimeId = b, role = "belligerent" }).ToArray(),
        citations,
    };

    [Fact]
    public async Task Event_with_participants_and_citations_round_trips()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk"); var de = await k.Regime("de");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var data = (await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [uk, de], Cite(frus, "Doc. 419, p. 414"))),
            HttpStatusCode.Created)).GetProperty("data");
        Assert.Equal(2, data.GetProperty("participants").GetArrayLength());
        Assert.Equal("Doc. 419, p. 414", data.GetProperty("citations")[0].GetProperty("locator").GetString());
        var id = data.GetProperty("id").GetGuid();
        var got = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/events/{id}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(2, got.GetProperty("participants").GetArrayLength());
    }

    [Fact]
    public async Task Event_citation_without_usage_rights_or_locator_is_rejected()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk");
        var unlicensed = await k.Source(kind: "peer_reviewed", license: null, title: "paper");
        var ok = await k.Source(kind: "official_record", title: "FRUS");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [uk], Cite(unlicensed, "p. 1"))),
            HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [uk], Cite(ok, " "))),
            HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [Guid.NewGuid()], Cite(ok, "p. 1"))),
            HttpStatusCode.BadRequest, "VALIDATION_FAILED");
    }

    [Fact] // 補充只呈現已發生、附引用的事件；不改變陣營（controllerAlignment 仍依切片）
    public async Task Control_features_carry_supplements_without_changing_camp()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk"); var de = await k.Regime("de");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var map = await k.Source();
        var snap = await k.Snapshot(await k.Theater("brit"), "1940-07-15");
        var cr = await k.Id(await k.PostControl(ApiTestKit.ControlBody(uk, snap, map, "1940-06-01", "1940-12-31", ApiTestKit.Square(-40, 60, 1))), "controlRecordId");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [uk, de], Cite(frus, "Doc. 419, p. 414"))), HttpStatusCode.Created);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1940-11-01", "1940-11-02", [uk], Cite(frus, "p. 9"))), HttpStatusCode.Created);
        // 沒有引用的事件不當補充
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-10-01", "1939-10-02", [uk])), HttpStatusCode.Created);

        var props = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1940-07-15"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Single(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid() == cr).GetProperty("properties");
        Assert.Equal(JsonValueKind.Null, props.GetProperty("controllerAlignment").ValueKind);
        var sup = props.GetProperty("controllerSupplements");
        Assert.Equal(1, sup.GetArrayLength());
        Assert.Equal("1939-09-03", sup[0].GetProperty("occurred").GetProperty("start").GetString());
        Assert.Equal("Doc. 419, p. 414", sup[0].GetProperty("citations")[0].GetProperty("locator").GetString());
    }

    [Fact]
    public async Task Alignment_retraction_is_one_time_and_allows_resegmenting()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("de");
        var src = await k.Source(kind: "official_record", title: "DGFP D VI");
        object Body(string loc) => new { camp = "axis", validPeriod = new { start = "1939-05-22", end = "1940-09-27" }, citations = new[] { new { sourceId = src, role = "primary", locator = loc, evidenceNote = "x" } } };
        var id = await k.Id(await k.W.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments", Body("Doc. No. 426")));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments/{id}/retraction", new { reason = " " }), HttpStatusCode.BadRequest);
        var r = (await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments/{id}/retraction", new { reason = "改指向美國政府印刷局版" }), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(id, r.GetProperty("id").GetGuid());
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments/{id}/retraction", new { reason = "again" }), HttpStatusCode.Conflict);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{Guid.NewGuid()}/alignments/{id}/retraction", new { reason = "x" }), HttpStatusCode.NotFound);
        var list = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{de}/alignments"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(0, list.GetArrayLength());
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments", Body("Doc. No. 426 (GPO)")), HttpStatusCode.Created);
        // 未帶 API key 不可撤回
        await ApiTestKit.Expect(await k.R.PostAsJsonAsync($"/api/v1/regimes/{de}/alignments/{id}/retraction", new { reason = "x" }), HttpStatusCode.Unauthorized);
    }

    private static object Gap(object geometry, string start, string end, string reason = "no_qualified_source") => new
    {
        geometry, validPeriod = new { start, end }, reason,
        note = new Dictionary<string, string> { ["zh-Hant"] = "地圖未畫", ["en"] = "Not shown on the map" },
        researchRef = "data/seed/ww2/pre-armistice-1940/README.md",
    };

    [Fact]
    public async Task Coverage_note_is_listed_on_control_and_cannot_overlap_control()
    {
        var k = new ApiTestKit(fx);
        var reich = await k.Regime("reich");
        var map = await k.Source();
        var snap = await k.Snapshot(await k.Theater("alps"), "1940-07-15");
        await k.Id(await k.PostControl(ApiTestKit.ControlBody(reich, snap, map, "1940-07-15", "1942-11-11", ApiTestKit.Square(-60, 70, 1))), "controlRecordId");

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-59.5, 70, 1), "1940-07-15", "1942-11-11")),
            HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-59, 70, 1), "1940-07-15", "1942-11-11", "unknown")),
            HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-59, 70, 1), "1940-07-15", null!)),
            HttpStatusCode.BadRequest);
        // 邊界相接可以
        var id = await k.Id(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-59, 70, 1), "1940-07-15", "1942-11-11")));

        JsonElement Notes(JsonElement body) => body.GetProperty("data").GetProperty("coverageNotes");
        var on = Notes(await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1941-01-01"), HttpStatusCode.OK));
        var n = on.EnumerateArray().Single(x => x.GetProperty("id").GetGuid() == id);
        Assert.Equal("no_qualified_source", n.GetProperty("reason").GetString());
        Assert.Equal("MultiPolygon", n.GetProperty("geometry").GetProperty("type").GetString());
        var off = Notes(await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1942-11-11"), HttpStatusCode.OK));
        Assert.DoesNotContain(off.EnumerateArray(), x => x.GetProperty("id").GetGuid() == id);
    }

    [Fact] // I5 兜底：參與方、事件引用不可改不可刪；涵蓋備註只允許一次撤回
    public async Task Schema_guards_for_new_tables()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk");
        var frus = await k.Source(kind: "official_record", title: "FRUS");
        var ev = (await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Event("1939-09-03", "1939-09-04", [uk], Cite(frus, "p. 1"))), HttpStatusCode.Created))
            .GetProperty("data").GetProperty("id").GetGuid();
        var gap = await k.Id(await k.W.PostAsJsonAsync("/api/v1/control-coverage-notes", Gap(ApiTestKit.Square(-80, 75, 1), "1940-01-01", "1940-02-01")));

        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        async Task Exec(string sql) { await using var cmd = new NpgsqlCommand(sql, c); await cmd.ExecuteNonQueryAsync(); }
        async Task Restrict(string sql) =>
            Assert.Equal(PostgresErrorCodes.RestrictViolation, (await Assert.ThrowsAsync<PostgresException>(() => Exec(sql))).SqlState);

        await Restrict($"UPDATE event_participants SET role = 'other' WHERE event_id = '{ev}'");
        await Restrict($"DELETE FROM event_participants WHERE event_id = '{ev}'");
        await Restrict($"UPDATE event_citations SET locator = 'p. 2' WHERE event_id = '{ev}'");
        await Restrict($"DELETE FROM event_citations WHERE event_id = '{ev}'");
        await Restrict($"DELETE FROM control_coverage_notes WHERE id = '{gap}'");
        await Restrict($"UPDATE control_coverage_notes SET reason = 'not_yet_digitized' WHERE id = '{gap}'");
        await Exec($"UPDATE control_coverage_notes SET retracted_at = now(), retraction_reason = '測試' WHERE id = '{gap}'");
        await Restrict($"UPDATE control_coverage_notes SET retraction_reason = 'x' WHERE id = '{gap}'");
    }
}
