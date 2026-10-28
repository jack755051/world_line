using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using WorldLine.Contracts;

namespace WorldLine.Api.Tests;

/// <summary>政權（I2、I4）、GET /control（§6.7 史料／推估）、GET /timeline/snapshots、統一回應格式。</summary>
[Collection(PostGisCollection.Name)]
public sealed class RegimeAndQueryTests(PostGisFixture fx)
{
    [Fact]
    public async Task I2_regime_requires_self_name()
    {
        var k = new ApiTestKit(fx);
        var res = await k.W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug = $"vichy-{k.Tag}",
            names = new[] { new { nameKind = "exonym", originalText = "Vichy France", originalLang = "en", display = new Dictionary<string, string> { ["en"] = "Vichy France" } } },
        });
        await ApiTestKit.Expect(res, HttpStatusCode.BadRequest, ErrorCodes.SelfNameRequired);
    }

    [Fact]
    public async Task I4_exonym_requires_existing_observer_and_round_trips()
    {
        var k = new ApiTestKit(fx);
        var observer = await k.Regime("united-kingdom");
        var selfName = new { nameKind = "self", originalText = "État français", originalLang = "fr", display = new Dictionary<string, string> { ["zh-Hant"] = "法蘭西國", ["en"] = "French State" }, isPrimary = true, observerRegimeId = (Guid?)null };

        var orphan = await k.W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug = $"french-state-{k.Tag}",
            names = new[] { selfName, new { nameKind = "exonym", originalText = "Vichy France", originalLang = "en", display = new Dictionary<string, string> { ["en"] = "Vichy France" }, isPrimary = false, observerRegimeId = (Guid?)null } },
        });
        await ApiTestKit.Expect(orphan, HttpStatusCode.BadRequest, ErrorCodes.OrphanExonym);

        var ok = await k.W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug = $"french-state-{k.Tag}",
            names = new[] { selfName, new { nameKind = "exonym", originalText = "Vichy France", originalLang = "en", display = new Dictionary<string, string> { ["en"] = "Vichy France" }, isPrimary = false, observerRegimeId = (Guid?)observer } },
        });
        var id = await k.Id(ok);

        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{id}"), HttpStatusCode.OK)).GetProperty("data");
        var names = data.GetProperty("names").EnumerateArray().ToList();
        Assert.Equal(2, names.Count);
        Assert.Equal("self", names[0].GetProperty("nameKind").GetString());
        Assert.Equal("法蘭西國", names[0].GetProperty("display").GetProperty("zh-Hant").GetString());
        Assert.Equal(observer, names[1].GetProperty("observerRegimeId").GetGuid());
    }

    [Fact]
    public async Task Localized_text_only_accepts_supported_languages()
    {
        var k = new ApiTestKit(fx);
        var res = await k.W.PostAsJsonAsync("/api/v1/theaters", new { code = $"x-{k.Tag}", name = new Dictionary<string, string> { ["fr"] = "Europe" } });
        await ApiTestKit.Expect(res, HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
    }

    [Fact]
    public async Task Control_by_date_returns_features_and_attested_or_interpolated_state()
    {
        var k = new ApiTestKit(fx);
        var germany = await k.Regime("deutsches-reich");
        var theater = await k.Theater("west-europe");
        var code = k.TheaterCode("west-europe");
        var s1 = await k.Snapshot(theater, "1940-07-15");
        var s2 = await k.Snapshot(theater, "1942-11-11");
        var source = await k.Source();
        var created = (await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(germany, s1, source, "1940-06-25", "1942-11-11",
            ApiTestKit.Square(-5, 43, 3))), HttpStatusCode.Created)).GetProperty("data");
        var versionId = created.GetProperty("versionId").GetGuid();

        // 快照當日 → attested，含該控制區
        var d1 = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1940-07-15"), HttpStatusCode.OK)).GetProperty("data");
        var fc = d1.GetProperty("featureCollection");
        Assert.Equal("FeatureCollection", fc.GetProperty("type").GetString());
        var feature = fc.GetProperty("features").EnumerateArray().Single(f => f.GetProperty("id").GetGuid() == versionId);
        Assert.Equal("Feature", feature.GetProperty("type").GetString());
        Assert.Equal("MultiPolygon", feature.GetProperty("geometry").GetProperty("type").GetString());
        var props = feature.GetProperty("properties");
        Assert.Equal(germany, props.GetProperty("controllerRegimeId").GetGuid());
        Assert.Equal("military_occupation", props.GetProperty("controlType").GetString());
        Assert.Equal(code, props.GetProperty("theaterCode").GetString());
        Assert.Equal(s1, props.GetProperty("snapshotId").GetGuid());
        Assert.Equal("1940-06-25", props.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal("1942-11-11", props.GetProperty("validPeriod").GetProperty("end").GetString());
        Assert.Equal("WWII Europe Map 15", props.GetProperty("citations")[0].GetProperty("locator").GetString());
        var st1 = Theater(d1, code);
        Assert.Equal("attested", st1.GetProperty("state").GetString());
        Assert.Equal(s1, st1.GetProperty("attestingSnapshot").GetProperty("id").GetGuid());

        // 兩快照之間 → interpolated，附前後快照
        var d2 = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1941-06-01"), HttpStatusCode.OK)).GetProperty("data");
        var st2 = Theater(d2, code);
        Assert.Equal("interpolated", st2.GetProperty("state").GetString());
        Assert.Equal("1940-07-15", st2.GetProperty("prevSnapshot").GetProperty("asOf").GetString());
        Assert.Equal("1942-11-11", st2.GetProperty("nextSnapshot").GetProperty("asOf").GetString());

        // 半開區間：迄日當天不再包含
        var d3 = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1942-11-11"), HttpStatusCode.OK)).GetProperty("data");
        Assert.DoesNotContain(d3.GetProperty("featureCollection").GetProperty("features").EnumerateArray(), f => f.GetProperty("id").GetGuid() == versionId);
        Assert.Equal("attested", Theater(d3, code).GetProperty("state").GetString());

        // 早於第一個快照 → outside（Story 3 TODO）
        var d0 = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1939-09-01"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("outside", Theater(d0, code).GetProperty("state").GetString());
    }

    [Fact]
    public async Task Interval_snapshot_attests_its_whole_period()
    {
        var k = new ApiTestKit(fx);
        var theater = await k.Theater("france-demarcation");
        await k.Snapshot(theater, "1940-06-22", "1940-06-22", "1942-11-11");
        var data = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1941-03-01"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("attested", Theater(data, k.TheaterCode("france-demarcation")).GetProperty("state").GetString());
    }

    [Fact]
    public async Task Timeline_lists_snapshots_with_primary_sources_paginated()
    {
        var k = new ApiTestKit(fx);
        var regime = await k.Regime("deutsches-reich");
        var theater = await k.Theater("tl");
        var code = k.TheaterCode("tl");
        var s1 = await k.Snapshot(theater, "1939-10-06");
        await k.Snapshot(theater, "1941-06-22");
        var source = await k.Source(title: $"Atlas {k.Tag}");
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, s1, source, "1939-10-06", "1941-06-22",
            ApiTestKit.Square(30, 50, 1))), HttpStatusCode.Created);

        var data = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/timeline/snapshots?from=1939-01-01&to=1950-01-01&pageSize=500"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(1, data.GetProperty("page").GetInt32());
        var mine = data.GetProperty("items").EnumerateArray().Where(i => i.GetProperty("theaterCode").GetString() == code).ToList();
        Assert.Equal(["1939-10-06", "1941-06-22"], mine.Select(i => i.GetProperty("asOf").GetString()!).ToArray());
        var src = mine[0].GetProperty("primarySources").EnumerateArray().Single();
        Assert.Equal($"Atlas {k.Tag}", src.GetProperty("title").GetString());
        Assert.Empty(mine[1].GetProperty("primarySources").EnumerateArray());

        var filtered = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/timeline/snapshots?from=1941-01-01&to=1941-12-31&pageSize=500"), HttpStatusCode.OK)).GetProperty("data");
        Assert.DoesNotContain(filtered.GetProperty("items").EnumerateArray(), i => i.GetProperty("asOf").GetString() == "1939-10-06");
    }

    [Fact]
    public async Task Bad_query_parameters_use_unified_error_format()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control"), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
        await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1940-13-01"), HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
        await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sources/{Guid.NewGuid()}"), HttpStatusCode.NotFound, ErrorCodes.NotFound);
    }

    private static JsonElement Theater(JsonElement data, string code) =>
        data.GetProperty("theaters").EnumerateArray().Single(t => t.GetProperty("theaterCode").GetString() == code);
}
