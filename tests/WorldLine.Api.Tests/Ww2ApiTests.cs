using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using WorldLine.Api.Seed;
using static WorldLine.Api.Tests.ApiTests;

namespace WorldLine.Api.Tests;

/// <summary>M2.5 二戰階段 API：?date=、控制關係、同盟陣營、被併吞、事件時區（以示範 seed 驗證）。</summary>
public class Ww2ApiTests(ApiFactory factory) : IClassFixture<ApiFactory>
{
    private const string Ww2Prefix = "0b1e0000-0000-4000-8000-0000000001";

    private async Task<HttpClient> ClientAsync(bool withKey = false)
    {
        await TestDatabase.EnsureReadyAsync();
        var client = factory.CreateClient();
        if (withKey) client.DefaultRequestHeaders.Add(Api.ApiKeyFilter.HeaderName, ApiFactory.TestKey);
        return client;
    }

    private static string S(JsonNode? n) => n!.GetValue<string>();

    private static async Task<JsonArray> ArrayAsync(HttpClient client, string url) =>
        (await JsonAsync(await client.GetAsync(url), HttpStatusCode.OK)).AsArray();

    [Fact]
    public async Task Regimes_on_1942_06_01_include_puppets_and_exclude_annexed_austria()
    {
        var client = await ClientAsync();
        var ww2 = (await ArrayAsync(client, "/api/v1/regimes?date=1942-06-01"))
            .Where(r => S(r!["id"]).StartsWith(Ww2Prefix)).ToList();
        var names = ww2.Select(r => S(r!["selfName"])).ToHashSet();
        foreach (var expected in new[] { "德意志國", "大日本帝國", "義大利王國", "大不列顛及北愛爾蘭聯合王國", "美利堅合眾國",
                     "蘇維埃社會主義共和國聯盟", "中華民國", "滿洲國", "法蘭西國", "法蘭西共和國" })
            Assert.Contains(expected, names);
        Assert.DoesNotContain("奧地利聯邦國", names);

        var italy = ww2.Single(r => S(r!["selfName"]) == "義大利王國")!;
        Assert.Contains(italy["alliances"]!.AsArray(), a => S(a!["selfName"]) == "軸心國");
        var manchukuo = ww2.Single(r => S(r!["selfName"]) == "滿洲國")!;
        Assert.Contains(manchukuo["controlledBy"]!.AsArray(), c => S(c!["controlType"]) == "puppet" && S(c["regime"]!["selfName"]) == "大日本帝國");
        var france = ww2.Single(r => S(r!["selfName"]) == "法蘭西共和國")!;
        Assert.Contains(france["controlledBy"]!.AsArray(), c => S(c!["controlType"]) == "occupation" && S(c["regime"]!["selfName"]) == "德意志國");

        // ROC 視角：滿洲國顯示「偽滿洲國」（定性用語是觀察視角他稱）
        var roc = Ww2Seeder.RepublicOfChina;
        var asSeenByRoc = (await ArrayAsync(client, $"/api/v1/regimes?date=1942-06-01&observer={roc}"))
            .Single(r => S(r!["id"]) == Ww2Seeder.Manchukuo.ToString())!;
        Assert.Equal("偽滿洲國", S(asSeenByRoc["displayName"]));
        Assert.Equal("滿洲國", S(asSeenByRoc["selfName"]));
    }

    [Fact]
    public async Task Italy_has_left_the_axis_on_1943_10_01_and_joins_allies_as_co_belligerent_later()
    {
        var client = await ClientAsync();
        JsonNode Alliance(JsonArray arr, Guid id) => arr.Single(a => S(a!["id"]) == id.ToString())!;
        IEnumerable<string> Members(JsonNode a) => a["members"]!.AsArray().Select(m => S(m!["regime"]!["selfName"]));

        var june42 = await ArrayAsync(client, "/api/v1/alliances?date=1942-06-01");
        Assert.Equivalent(new[] { "大日本帝國", "德意志國", "義大利王國" }, Members(Alliance(june42, Ww2Seeder.Axis)).ToArray(), strict: true);
        Assert.Equal(4, Members(Alliance(june42, Ww2Seeder.Allies)).Count());

        var oct43 = await ArrayAsync(client, "/api/v1/alliances?date=1943-10-01");
        Assert.Equivalent(new[] { "大日本帝國", "德意志國" }, Members(Alliance(oct43, Ww2Seeder.Axis)).ToArray(), strict: true);
        Assert.DoesNotContain("義大利王國", Members(Alliance(oct43, Ww2Seeder.Allies)));

        var oct13 = await ArrayAsync(client, "/api/v1/alliances?date=1943-10-13");
        var italyInAllies = Alliance(oct13, Ww2Seeder.Allies)["members"]!.AsArray().Single(m => S(m!["regime"]!["selfName"]) == "義大利王國")!;
        Assert.Equal("co_belligerent", S(italyInAllies["role"]));

        // year 捷徑＝該年任一天：1943 年義大利仍曾是軸心國成員
        var y43 = await ArrayAsync(client, "/api/v1/alliances?year=1943");
        Assert.Contains("義大利王國", Members(Alliance(y43, Ww2Seeder.Axis)));

        var italy = (await ArrayAsync(client, "/api/v1/regimes?date=1943-10-01")).Single(r => S(r!["id"]) == Ww2Seeder.Italy.ToString())!;
        Assert.Empty(italy["alliances"]!.AsArray());

        // 陣營詳情含全部期間（I7：依精度輸出）
        var axis = await JsonAsync(await client.GetAsync($"/api/v1/alliances/{Ww2Seeder.Axis}"), HttpStatusCode.OK);
        var italyMember = axis["members"]!.AsArray().Single(m => S(m!["regime"]!["selfName"]) == "義大利王國")!;
        Assert.Equal("1943-09-08", S(italyMember["leftOn"]));
        Assert.Equal("day", S(italyMember["leftPrecision"]));
    }

    [Fact]
    public async Task Control_relations_and_occupied_areas_on_1942_06_01()
    {
        var client = await ClientAsync();
        var rels = await ArrayAsync(client, "/api/v1/control-relations?date=1942-06-01");
        bool Has(string controller, string controlled, string type) => rels.Any(r =>
            S(r!["controller"]!["selfName"]) == controller && S(r["controlled"]!["selfName"]) == controlled && S(r["controlType"]) == type);
        Assert.True(Has("大日本帝國", "滿洲國", "puppet"));
        Assert.True(Has("大日本帝國", "中華民國", "occupation"));
        Assert.True(Has("德意志國", "法蘭西共和國", "occupation"));
        var vichy = rels.Single(r => S(r!["controlled"]!["selfName"]) == "法蘭西國" && S(r["controlType"]) == "puppet")!;
        Assert.True(vichy["isDisputed"]!.GetValue<bool>());
        // 1942-11-11 起德軍才進佔南部
        Assert.False(Has("德意志國", "法蘭西國", "occupation"));
        Assert.Contains(await ArrayAsync(client, "/api/v1/control-relations?date=1943-01-01&type=occupation"),
            r => S(r!["controlled"]!["selfName"]) == "法蘭西國");

        var areas = await JsonAsync(await client.GetAsync("/api/v1/control-relations/areas?date=1942-06-01"), HttpStatusCode.OK);
        Assert.Equal("FeatureCollection", S(areas["type"]));
        Assert.True(areas["features"]!.AsArray().Count >= 2);

        Assert.Equal(HttpStatusCode.BadRequest, (await client.GetAsync("/api/v1/control-relations?date=1942-06-01&type=invasion")).StatusCode);
    }

    [Fact]
    public async Task Territories_snapshot_by_date_marks_illustrative_and_control()
    {
        var client = await ClientAsync();
        var fc = await JsonAsync(await client.GetAsync("/api/v1/territories?date=1942-06-01"), HttpStatusCode.OK);
        var features = fc["features"]!.AsArray();
        var vichy = features.Single(f => S(f!["properties"]!["regimeId"]) == Ww2Seeder.VichyFrance.ToString())!;
        Assert.Equal("1940-07-10", S(vichy["properties"]!["validFrom"]));
        Assert.Equal("day", S(vichy["properties"]!["validFromPrecision"]));
        Assert.True(vichy["properties"]!["isIllustrative"]!.GetValue<bool>());
        Assert.Contains("示意", S(vichy["properties"]!["source"]));
        Assert.DoesNotContain(features, f => S(f!["properties"]!["regimeId"]) == Ww2Seeder.Austria.ToString());
        var france = features.Single(f => S(f!["properties"]!["regimeId"]) == Ww2Seeder.FrenchRepublic.ToString())!;
        Assert.NotEmpty(france["properties"]!["controlledBy"]!.AsArray());

        // 1938-03-12 奧地利仍在，03-13 起併入德意志國的疆域
        var before = await JsonAsync(await client.GetAsync("/api/v1/territories?date=1938-03-12"), HttpStatusCode.OK);
        Assert.Contains(before["features"]!.AsArray(), f => S(f!["properties"]!["regimeId"]) == Ww2Seeder.Austria.ToString());
        var after = await JsonAsync(await client.GetAsync("/api/v1/territories?date=1938-03-13"), HttpStatusCode.OK);
        Assert.DoesNotContain(after["features"]!.AsArray(), f => S(f!["properties"]!["regimeId"]) == Ww2Seeder.Austria.ToString());

        Assert.Equal(HttpStatusCode.BadRequest, (await client.GetAsync("/api/v1/territories?date=1942-06-01&year=1942")).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.GetAsync("/api/v1/territories?date=1942-13-01")).StatusCode);
    }

    [Fact]
    public async Task Annexed_austria_and_precision_of_existence_dates()
    {
        var client = await ClientAsync();
        var austria = await JsonAsync(await client.GetAsync($"/api/v1/regimes/{Ww2Seeder.Austria}"), HttpStatusCode.OK);
        Assert.Equal("annexed", S(austria["regime"]!["status"]));
        Assert.Equal("德意志國", S(austria["annexedBy"]!["selfName"]));
        Assert.Equal("1938-03-13", S(austria["regime"]!["existenceTo"]));
        var germany = await JsonAsync(await client.GetAsync($"/api/v1/regimes/{Ww2Seeder.Germany}"), HttpStatusCode.OK);
        Assert.Contains(germany["annexed"]!.AsArray(), r => S(r!["selfName"]) == "奧地利聯邦國");
        Assert.Contains(germany["controlRelations"]!.AsArray(), r => S(r!["controlled"]!["selfName"]) == "法蘭西共和國");

        // I7：只知年就只輸出年
        var japan = await JsonAsync(await client.GetAsync($"/api/v1/regimes/{Ww2Seeder.Japan}"), HttpStatusCode.OK);
        Assert.Equal("1868", S(japan["regime"]!["existenceFrom"]));
        Assert.Equal("year", S(japan["regime"]!["existenceFromPrecision"]));
        Assert.Null(japan["regime"]!["existenceTo"]);
    }

    [Fact]
    public async Task Pearl_harbor_keeps_local_date_with_time_zone_note_and_eras_use_dates()
    {
        var client = await ClientAsync();
        var events = await ArrayAsync(client, "/api/v1/events?date=1941-12-07");
        var ph = events.Single(e => S(e!["id"]) == "attack-on-pearl-harbor-1941")!;
        Assert.Equal("1941-12-07", S(ph["startEdtf"]));
        Assert.Equal("day", S(ph["precision"]));
        Assert.Equal("Pacific/Honolulu", S(ph["timeZone"]));
        Assert.Contains("1941-12-08", S(ph["timeNote"]));
        Assert.Equal(2, ph["perspectiveCount"]!.GetValue<int>());
        // 當地日期記錄：日本時間的 12-08 查不到
        Assert.DoesNotContain(await ArrayAsync(client, "/api/v1/events?date=1941-12-08"), e => S(e!["id"]) == "attack-on-pearl-harbor-1941");

        var labels = (await ArrayAsync(client, "/api/v1/reign-eras?date=1942-06-01")).Select(e => S(e!["label"])).ToList();
        Assert.Contains("昭和十七年", labels);
        Assert.Contains("民國三十一年", labels);
        Assert.Contains("康德九年", labels);
        // 1934-02-28 仍是大同；03-01 起康德元年
        Assert.Contains("大同三年", (await ArrayAsync(client, "/api/v1/reign-eras?date=1934-02-28")).Select(e => S(e!["label"])));
        Assert.Contains("康德元年", (await ArrayAsync(client, "/api/v1/reign-eras?date=1934-03-01")).Select(e => S(e!["label"])));
    }

    // ---------- 寫入 ----------

    [Fact]
    public async Task New_write_endpoints_require_api_key()
    {
        var anon = await ClientAsync();
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PostAsJsonAsync("/api/v1/control-relations",
            new { controllerRegimeId = Ww2Seeder.Japan, controlledRegimeId = Ww2Seeder.Manchukuo, controlType = "puppet", validFrom = "1932", validTo = "1945" })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PostAsJsonAsync("/api/v1/alliances", new { selfName = "x", existenceFrom = "1940" })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PostAsJsonAsync($"/api/v1/alliances/{Ww2Seeder.Axis}/members",
            new { regimeId = Ww2Seeder.Manchukuo, joinedOn = "1940" })).StatusCode);
    }

    [Fact]
    public async Task Create_control_relation_validates_I6()
    {
        var client = await ClientAsync(withKey: true);
        var (a, _) = await CreateRegimeAsync(client, "1930", "1950");
        var (b, _) = await CreateRegimeAsync(client, "1935-06", "1945-08-15");
        object Body(object controller, object controlled, string from, string? to, string type = "occupation", bool disputed = false) =>
            new { controllerRegimeId = controller, controlledRegimeId = controlled, controlType = type, validFrom = from, validTo = to, isDisputed = disputed };
        async Task<HttpStatusCode> Post(object body) => (await client.PostAsJsonAsync("/api/v1/control-relations", body)).StatusCode;

        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, a, "1938", "1940")));                 // 自我控制
        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, Guid.NewGuid(), "1938", "1940")));    // 被控制方不存在（I6 不可孤兒）
        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, b, "1934", "1940")));                 // 超出被控制方存續期間
        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, b, "1938", null)));                   // 必須有終點
        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, b, "1938", "1940", "invasion")));     // 類型不合法
        Assert.Equal(HttpStatusCode.BadRequest, await Post(Body(a, b, "1938-02-30", "1940")));           // 日期不存在

        var created = await JsonAsync(await client.PostAsJsonAsync("/api/v1/control-relations", Body(a, b, "1938-03-01", "1940-05")), HttpStatusCode.Created);
        Assert.Equal("1940-05", S(created["validTo"]));
        Assert.Equal("month", S(created["validToPrecision"]));
        Assert.Equal(HttpStatusCode.Conflict, await Post(Body(a, b, "1939", "1941")));
        Assert.Equal(HttpStatusCode.Created, await Post(Body(a, b, "1939", "1941", disputed: true)));
        Assert.Equal(HttpStatusCode.Created, await Post(Body(a, b, "1939", "1941", "puppet")));
    }

    [Fact]
    public async Task Create_alliance_and_membership_periods()
    {
        var client = await ClientAsync(withKey: true);
        var (member, _) = await CreateRegimeAsync(client, "1900", null);
        var alliance = await JsonAsync(await client.PostAsJsonAsync("/api/v1/alliances",
            new { selfName = $"測試陣營-{Guid.NewGuid():N}"[..16], existenceFrom = "1936-10-25" }), HttpStatusCode.Created);
        var id = S(alliance["id"]);
        Assert.Null(alliance["existenceTo"]);

        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync("/api/v1/alliances", new { selfName = " ", existenceFrom = "1940" })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync($"/api/v1/alliances/{id}/members",
            new { regimeId = member, joinedOn = "1943-13" })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync($"/api/v1/alliances/{id}/members",
            new { regimeId = Guid.NewGuid(), joinedOn = "1940" })).StatusCode);

        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync($"/api/v1/alliances/{id}/members",
            new { regimeId = member, joinedOn = "1937", leftOn = "1938-06" })).StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, (await client.PostAsJsonAsync($"/api/v1/alliances/{id}/members",
            new { regimeId = member, joinedOn = "1938" })).StatusCode);
        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync($"/api/v1/alliances/{id}/members",
            new { regimeId = member, role = "co_belligerent", joinedOn = "1939" })).StatusCode);

        var detail = await JsonAsync(await client.GetAsync($"/api/v1/alliances/{id}"), HttpStatusCode.OK);
        Assert.Equal(2, detail["members"]!.AsArray().Count);
        var on1938 = (await ArrayAsync(client, "/api/v1/alliances?date=1938-07-01")).Single(a => S(a!["id"]) == id)!;
        Assert.Empty(on1938["members"]!.AsArray());
    }

    [Fact]
    public async Task Patch_regime_to_annexed_requires_annexing_regime()
    {
        var client = await ClientAsync(withKey: true);
        var (id, version) = await CreateRegimeAsync(client, "1918-11-12", "1938-03-13");
        var (annexer, _) = await CreateRegimeAsync(client, "1871-01-18", null);

        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/regimes/{id}",
            new { version, changeReason = "被併吞缺併吞方", status = "annexed" })).StatusCode);
        var ok = await JsonAsync(await client.PatchAsJsonAsync($"/api/v1/regimes/{id}",
            new { version, changeReason = "德奧合併", status = "annexed", annexedByRegimeId = annexer }), HttpStatusCode.OK);
        Assert.Equal("annexed", S(ok["regime"]!["status"]));
        Assert.Equal(annexer, S(ok["regime"]!["annexedByRegimeId"]));
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/regimes/{id}",
            new { version = version + 1, changeReason = "改成滅亡", status = "destroyed", destroyedByRegimeId = annexer })).StatusCode);
    }
}
