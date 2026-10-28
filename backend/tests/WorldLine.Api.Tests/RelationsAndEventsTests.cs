using System.Net;
using System.Net.Http.Json;
using Npgsql;
using WorldLine.Contracts;

namespace WorldLine.Api.Tests;

/// <summary>
/// Tai 2026-10-28 決定：
/// - 扶植關係兩者並存：控制紀錄 patronRegimeId ＋ regime_relations patron_puppet（regimeA＝扶植方、regimeB＝傀儡）。
/// - 事件記當地日期＋IANA 時區＋選填多語 timeNote。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class RelationsAndEventsTests(PostGisFixture fx)
{
    [Fact]
    public async Task Patron_recorded_both_on_control_version_and_as_patron_puppet_relation()
    {
        var k = new ApiTestKit(fx);
        var germany = await k.Regime("deutsches-reich");
        var vichy = await k.Regime("etat-francais");
        var theater = await k.Theater("france");
        var snapshot = await k.Snapshot(theater, "1942-11-11");
        var source = await k.Source();

        // 控制紀錄：控制方記傀儡政權，扶植方記在 patronRegimeId（給地圖）
        var body = ApiTestKit.ControlBody(vichy, snapshot, source, "1942-11-11", "1944-08-25", ApiTestKit.Square(2, 44, 2), "puppet_administration");
        body["patronRegimeId"] = germany.ToString();
        var created = (await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.Created)).GetProperty("data");
        var versionId = created.GetProperty("versionId").GetGuid();

        // 持續關係：patron_puppet（給聚焦面板）
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/regime-relations", new
        {
            regimeAId = germany, regimeBId = vichy, relationType = "patron_puppet",
            validPeriod = new { start = "1942-11-11", end = "1944-08-25" },
            note = new Dictionary<string, string> { ["zh-Hant"] = "安東行動後德軍佔領全法" },
        }), HttpStatusCode.Created);

        var feature = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1943-06-01"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Single(f => f.GetProperty("id").GetGuid() == versionId);
        Assert.Equal(germany, feature.GetProperty("properties").GetProperty("patronRegimeId").GetGuid());

        var asPuppet = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{vichy}/interactions?date=1943-06-01"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("relations").EnumerateArray().Single();
        Assert.Equal("puppet", asPuppet.GetProperty("role").GetString());
        Assert.Equal(germany, asPuppet.GetProperty("counterpartRegimeId").GetGuid());

        var asPatron = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{germany}/interactions?date=1943-06-01"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("relations").EnumerateArray().Single();
        Assert.Equal("patron", asPatron.GetProperty("role").GetString());

        // 期間外（半開區間迄日當天）不回傳
        var after = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{vichy}/interactions?date=1944-08-25"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("relations");
        Assert.Equal(0, after.GetArrayLength());
    }

    [Fact]
    public async Task Relation_validation()
    {
        var k = new ApiTestKit(fx);
        var a = await k.Regime("a");
        var b = await k.Regime("b");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/regime-relations", new
        {
            regimeAId = a, regimeBId = b, relationType = "at_war", validPeriod = new { start = (string?)null, end = "1945-05-08" },
        }), HttpStatusCode.BadRequest, ErrorCodes.PeriodRequired);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/regime-relations", new
        {
            regimeAId = a, regimeBId = a, relationType = "at_war", validPeriod = new { start = "1941-06-22", end = "1945-05-08" },
        }), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/regime-relations", new
        {
            regimeAId = a, regimeBId = b, relationType = "friendship", validPeriod = new { start = "1941-06-22", end = "1945-05-08" },
        }), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
        // 迄日未知可留空
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/regime-relations", new
        {
            regimeAId = a, regimeBId = b, relationType = "at_war", validPeriod = new { start = "1941-06-22", end = (string?)null },
        }), HttpStatusCode.Created);
        await ApiTestKit.Expect(await fx.Reader().PostAsJsonAsync("/api/v1/regime-relations", new { }), HttpStatusCode.Unauthorized, ErrorCodes.Unauthorized);
    }

    [Fact]
    public async Task Event_records_local_date_iana_zone_and_time_note()
    {
        var k = new ApiTestKit(fx);
        var res = await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "battle",
            occurred = new { start = "1941-12-07", end = "1941-12-08" },
            datePrecision = "day",
            localTimeZone = "Pacific/Honolulu",
            timeNote = new Dictionary<string, string> { ["zh-Hant"] = "東京時間 12 月 8 日", ["en"] = "8 December, Tokyo time" },
            summary = new Dictionary<string, string> { ["zh-Hant"] = "珍珠港事件", ["en"] = "Attack on Pearl Harbor" },
            location = new { type = "Point", coordinates = new[] { -157.95, 21.35 } },
        });
        var id = await k.Id(res);

        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/events/{id}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("1941-12-07", data.GetProperty("occurred").GetProperty("start").GetString());
        Assert.Equal("1941-12-08", data.GetProperty("occurred").GetProperty("end").GetString());
        Assert.Equal("Pacific/Honolulu", data.GetProperty("localTimeZone").GetString());
        Assert.Equal("東京時間 12 月 8 日", data.GetProperty("timeNote").GetProperty("zh-Hant").GetString());
        Assert.Equal("Point", data.GetProperty("location").GetProperty("type").GetString());
    }

    [Fact]
    public async Task Event_time_zone_is_optional_but_must_be_iana()
    {
        var k = new ApiTestKit(fx);
        object Body(string? zone) => new
        {
            eventKind = "treaty", occurred = new { start = "1940-09-27", end = "1940-09-28" }, datePrecision = "day", localTimeZone = zone,
        };
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Body(null)), HttpStatusCode.Created);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Body("Europe/Berlin")), HttpStatusCode.Created);
        foreach (var bad in new[] { "Tokyo Standard Time", "UTC", "Etc/GMT-9", "+09:00", "Mars/Olympus" })
            await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", Body(bad)), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
    }

    [Fact]
    public async Task Event_requires_bounded_occurred_and_known_precision()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "war", occurred = new { start = "1937-07-07", end = (string?)null }, datePrecision = "day",
        }), HttpStatusCode.BadRequest, ErrorCodes.PeriodRequired);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "war", occurred = new { start = "1937-07-07", end = "1937-07-08" }, datePrecision = "hour",
        }), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
    }

    [Fact]
    public async Task I5_relations_and_events_cannot_be_deleted()
    {
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        foreach (var t in new[] { "regime_relations", "historical_events" })
        {
            await using var cmd = new NpgsqlCommand($"TRUNCATE {t}", c);
            var ex = await Assert.ThrowsAsync<PostgresException>(() => cmd.ExecuteNonQueryAsync());
            Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
        }
    }
}
