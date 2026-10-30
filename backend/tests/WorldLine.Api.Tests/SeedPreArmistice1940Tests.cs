using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/pre-armistice-1940/requests/*.json（停戰前快照 1940-06-04、06-12，DRAFT）送到測試容器（不是 appdb_ww2）。
/// 先重播法國、陣營、法英三批取得前置 id。檢查：快照當天有德、法控制區與控制資料缺備註，隔天不延長（§9）。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedPreArmistice1940Tests(PostGisFixture fx)
{
    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww2");
    }

    private static async Task ReplayDir(ApiTestKit k, string sub, Dictionary<string, string> ids)
    {
        foreach (var path in Directory.GetFiles(Path.Combine(SeedRoot(), sub, "requests"), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            if (req["_meta"]?["requiresDecision"]?.GetValue<bool>() == true) continue;
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

    [Fact]
    public async Task Pre_armistice_snapshots_are_accepted_and_last_one_day()
    {
        var k = new ApiTestKit(fx);
        var ids = new Dictionary<string, string>();
        foreach (var sub in new[] { "france-1940-07-15", "alignments", "fr-uk-1940", "pre-armistice-1940" })
            await ReplayDir(k, sub, ids);

        async Task<(HashSet<string> records, HashSet<string> gaps, JsonElement data)> On(string date)
        {
            var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/control?date={date}"), HttpStatusCode.OK)).GetProperty("data");
            var records = data.GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Select(f => f.GetProperty("properties").GetProperty("controlRecordId").GetString()!).ToHashSet();
            var gaps = data.GetProperty("coverageNotes").EnumerateArray().Select(n => n.GetProperty("id").GetString()!).ToHashSet();
            return (records, gaps, data);
        }

        var (r0604, g0604, d0604) = await On("1940-06-04");
        Assert.Contains(ids["CR_DE_0604"], r0604);
        Assert.Contains(ids["CR_FR3_0604"], r0604);
        Assert.Contains(ids["CR_NORD"], r0604);
        foreach (var g in new[] { "GAP_FRAME_0604", "GAP_MAGINOT_0604", "GAP_DUNKIRK_0604" }) Assert.Contains(ids[g], g0604);
        var theater = d0604.GetProperty("theaters").EnumerateArray().Single(t => t.GetProperty("theaterCode").GetString() == $"west-europe-{k.Tag}");
        Assert.Equal("attested", theater.GetProperty("state").GetString());

        // 法國的陣營：第三共和沒有切片（原則 1），只有補充（1939-09-03 照會）
        var fr3 = d0604.GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Single(f => f.GetProperty("properties").GetProperty("controlRecordId").GetString() == ids["CR_FR3_0604"]).GetProperty("properties");
        Assert.Equal(JsonValueKind.Null, fr3.GetProperty("controllerAlignment").ValueKind);
        Assert.Contains(fr3.GetProperty("controllerSupplements").EnumerateArray(), e => e.GetProperty("eventId").GetString() == ids["EV_FR3_DECL_1939"]);

        // 快照只撐一天：06-05 起不延長（§9 推估不當史料）
        var (r0605, g0605, _) = await On("1940-06-05");
        Assert.DoesNotContain(ids["CR_DE_0604"], r0605);
        Assert.DoesNotContain(ids["GAP_FRAME_0604"], g0605);

        var (r0612, g0612, _) = await On("1940-06-12");
        Assert.Contains(ids["CR_DE_0612"], r0612);
        Assert.Contains(ids["CR_FR3_0612"], r0612);
        foreach (var g in new[] { "GAP_FRAME_0612", "GAP_MAGINOT_0612", "GAP_CAUX_0612", "GAP_LINEBREAK_0612" }) Assert.Contains(ids[g], g0612);
        Assert.DoesNotContain(ids["CR_DE_0612"], (await On("1940-06-13")).records);
    }
}
