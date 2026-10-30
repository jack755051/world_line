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
            var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
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

    [Fact] // 全部（含待決的英國本土與英法同盟候選）都要被 API 接受
    public async Task FrUk_1940_seed_requests_including_pending_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = await Replay(k, includePending: true);
        Guid Id(string key) => Guid.Parse(ids[key]);

        var jul15 = await Features(k, "1940-07-15", ids);
        Assert.Contains(Id("CR_MAIN"), jul15.Keys);
        Assert.Equal("co_belligerent", Camp(jul15[Id("CR_VICHY_FREE")]));
        Assert.Equal("direct_rule", jul15[Id("CR_VICHY_FREE")].GetProperty("properties").GetProperty("controlType").GetString());
        Assert.Equal("allies", Camp(jul15[Id("CR_UK_HOME")]));
        Assert.Equal("axis", Camp(jul15[Id("CR_MAIN")]));

        var aug15 = await Features(k, "1940-08-15", ids);
        Assert.Contains(Id("CR_VICHY_FREE"), aug15.Keys);
        Assert.Contains(Id("CR_UK_HOME"), aug15.Keys);

        // 自由區在德軍退回分界線（7 月中）之前、Anton 行動（1942-11-11）之後都不在
        Assert.DoesNotContain(Id("CR_VICHY_FREE"), (await Features(k, "1940-07-10", ids)).Keys);
        Assert.DoesNotContain(Id("CR_VICHY_FREE"), (await Features(k, "1942-11-11", ids)).Keys);

        var fr3 = Assert.Single(await Alignments(k, ids["REGIME_FR3"]));
        Assert.Equal("allies", fr3.GetProperty("camp").GetString());
        Assert.Equal("1939-09-03", fr3.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal("1940-06-25", fr3.GetProperty("validPeriod").GetProperty("end").GetString());
        Assert.Empty(await Alignments(k, ids["REGIME_FR_LIBRE"]));  // 自由法國：依據未定，不建
    }

    [Fact] // 預設送出（不含待決）：只有維琪自由區與維琪陣營，英國本土與英法同盟不送
    public async Task FrUk_1940_seed_requests_without_pending_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = await Replay(k, includePending: false);
        Assert.False(ids.ContainsKey("CR_UK_HOME"));
        Assert.False(ids.ContainsKey("AL_UK_ALLIES_1939"));
        Assert.False(ids.ContainsKey("AL_FR3_ALLIES_1939"));

        var jul15 = await Features(k, "1940-07-15", ids);
        Assert.Equal("co_belligerent", Camp(jul15[Guid.Parse(ids["CR_VICHY_FREE"])]));
        var vichy = Assert.Single(await Alignments(k, ids["REGIME_FR_STATE"]));
        Assert.Equal("1940-07-11", vichy.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal(JsonValueKind.Null, vichy.GetProperty("validPeriod").GetProperty("end").ValueKind);
        Assert.Empty(await Alignments(k, ids["REGIME_UK"]));
    }
}
