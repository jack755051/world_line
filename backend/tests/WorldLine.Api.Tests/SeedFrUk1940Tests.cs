using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/fr-uk-1940/requests/*.json（法、英政權與 1940 控制區，DRAFT）送到測試容器（不是 appdb_ww2）。
/// 先重播法國那批（預設、不含待決）與陣營那批，取得 SNAP_0715、SRC_LECONTE 等前置 id，再送本批。
/// slug 與 theater code 加測試標籤，避免與其他測試衝突。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedFrUk1940Tests(PostGisFixture fx)
{
    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww2");
    }

    private static async Task ReplayDir(ApiTestKit k, string sub, Dictionary<string, string> ids, bool includePending)
    {
        foreach (var path in Directory.GetFiles(Path.Combine(SeedRoot(), sub, "requests"), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            if (!includePending && req["_meta"]?["requiresDecision"]?.GetValue<bool>() == true) continue;
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (body["code"] is not null) body["code"] = $"{body["code"]}-{k.Tag}";
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync(Fill((string)req["_post"]!), new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            var expected = ((string)req["_post"]!).EndsWith("/retraction") ? HttpStatusCode.OK : HttpStatusCode.Created;
            var data = (await ApiTestKit.Expect(res, expected)).GetProperty("data");
            ids[(string)req["_placeholder"]!] = data.TryGetProperty("id", out var p) ? p.GetString()! : data.GetProperty("controlRecordId").GetString()!;
        }
    }

    private static async Task<Dictionary<string, string>> Replay(ApiTestKit k, bool includePending)
    {
        var ids = new Dictionary<string, string>();
        await ReplayDir(k, "france-1940-07-15", ids, includePending: false);
        await ReplayDir(k, "alignments", ids, includePending: false);
        await ReplayDir(k, "fr-uk-1940", ids, includePending);
        return ids;
    }

    private static async Task<Dictionary<Guid, JsonElement>> Features(ApiTestKit k, string date, Dictionary<string, string> ids)
    {
        var mine = ids.Where(kv => kv.Key.StartsWith("CR_")).Select(kv => Guid.Parse(kv.Value)).ToHashSet();
        return (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/control?date={date}"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Where(f => mine.Contains(f.GetProperty("properties").GetProperty("controlRecordId").GetGuid()))
            .ToDictionary(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid());
    }

    private static string? Camp(JsonElement feature) =>
        feature.GetProperty("properties").TryGetProperty("controllerAlignment", out var a) && a.ValueKind == JsonValueKind.Object
            ? a.GetProperty("camp").GetString() : null;

    private static async Task<List<JsonElement>> Alignments(ApiTestKit k, string regimeId) =>
        (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{regimeId}/alignments"), HttpStatusCode.OK))
            .GetProperty("data").EnumerateArray().ToList();

    private static JsonElement Props(JsonElement f) => f.GetProperty("properties");

    [Fact] // Tai 2026-10-31：同盟依聯合國家宣言（英國 1942-01-01 起）；參戰照會、承認只作「補充」；英國本土不寫；阿爾卑斯五省為控制資料缺
    public async Task FrUk_1940_seed_requests_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = await Replay(k, includePending: true);
        Guid Id(string key) => Guid.Parse(ids[key]);
        Assert.False(ids.ContainsKey("CR_UK_HOME"));

        var jul15 = await Features(k, "1940-07-15", ids);
        Assert.Contains(Id("CR_MAIN"), jul15.Keys);
        Assert.Equal("co_belligerent", Camp(jul15[Id("CR_VICHY_FREE")]));
        Assert.Equal("direct_rule", Props(jul15[Id("CR_VICHY_FREE")]).GetProperty("controlType").GetString());
        Assert.Equal("axis", Camp(jul15[Id("CR_MAIN")]));
        // 德國的補充：英、法對德宣戰（1939-09-03）
        var deSup = Props(jul15[Id("CR_MAIN")]).GetProperty("controllerSupplements").EnumerateArray().Select(e => e.GetProperty("eventId").GetString()).ToList();
        Assert.Contains(ids["EV_UK_DECL_1939"], deSup);
        Assert.Contains(ids["EV_FR3_DECL_1939"], deSup);
        Assert.DoesNotContain(Id("CR_VICHY_FREE"), (await Features(k, "1940-07-10", ids)).Keys);
        Assert.DoesNotContain(Id("CR_VICHY_FREE"), (await Features(k, "1942-11-11", ids)).Keys);

        // 英國：1942-01-01 起同盟；第三共和、自由法國沒有陣營切片
        var uk = Assert.Single(await Alignments(k, ids["REGIME_UK"]));
        Assert.Equal("allies", uk.GetProperty("camp").GetString());
        Assert.Equal("1942-01-01", uk.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Empty(await Alignments(k, ids["REGIME_FR3"]));
        Assert.Empty(await Alignments(k, ids["REGIME_FR_LIBRE"]));

        // 自由法國起日記在自稱名稱（1940-06-23），依據為英國承認事件
        var ev = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/events/{ids["EV_UK_RECOG_FF"]}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("1940-06-23", ev.GetProperty("occurred").GetProperty("start").GetString());
        Assert.Contains(ev.GetProperty("participants").EnumerateArray(), p => p.GetProperty("regimeId").GetString() == ids["REGIME_FR_LIBRE"]);
        Assert.Equal("Doc. 235, pp. 266–267（美國駐法副大使 Biddle 1940-06-24 電報，Bordeaux）", ev.GetProperty("citations")[0].GetProperty("locator").GetString());

        // 阿爾卑斯五省：控制資料缺（R9）
        var notes = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1940-07-15"), HttpStatusCode.OK)).GetProperty("data").GetProperty("coverageNotes");
        var alpine = notes.EnumerateArray().Single(n => n.GetProperty("id").GetString() == ids["GAP_ALPINE"]);
        Assert.Equal("no_qualified_source", alpine.GetProperty("reason").GetString());
    }
}
