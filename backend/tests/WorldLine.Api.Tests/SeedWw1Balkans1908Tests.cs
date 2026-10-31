using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww1/balkans-1908-1914/requests/*.json（WW1 第一批，DRAFT）整批送到測試容器（不是 appdb_ww2）。
/// 前置批次的政權（義、羅、希、比、丹、挪、瑞、保、法、義屬愛琴海、葡）與海岸線來源先建替身；
/// 葡萄牙共和國的撤回／重送引用開發庫既有 id，這裡略過。檢查：全部通過 API 驗證、截圖日的政權、待查證事件沒有引用、衝突紀錄。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedWw1Balkans1908Tests(PostGisFixture fx)
{
    private static readonly string[] PriorRegimes = ["REGIME_IT", "REGIME_RO", "REGIME_GR", "REGIME_BE", "REGIME_DK", "REGIME_NO", "REGIME_SE", "REGIME_BG", "REGIME_FR3", "REGIME_IT_AEGEAN", "REGIME_PT"];

    private static string BatchRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww1", "balkans-1908-1914");
    }

    private static async Task<Dictionary<string, string>> ReplayAsync(ApiTestKit k)
    {
        var root = BatchRoot();
        var geoms = new Dictionary<string, JsonNode>();
        foreach (var f in JsonNode.Parse(await File.ReadAllTextAsync(Path.Combine(root, "ww1-1908-1914-derived.geojson")))!["features"]!.AsArray())
            geoms[f!["id"]!.ToJsonString().Trim('"')] = f["geometry"]!;
        var ids = new Dictionary<string, string>();
        foreach (var ph in PriorRegimes)
        {
            var slug = $"{ph.ToLowerInvariant().Replace('_', '-')}-{k.Tag}";
            ids[ph] = (await k.Id(await k.W.PostAsJsonAsync("/api/v1/regimes", new
            {
                slug,
                names = new[] { new { nameKind = "self", originalText = ph, originalLang = "en", display = new Dictionary<string, string> { ["zh-Hant"] = ph, ["en"] = ph }, isPrimary = true } },
            }))).ToString();
        }
        ids["SRC_NE_LAND"] = (await k.Source("dataset", "cc0", $"Natural Earth {k.Tag}")).ToString();
        foreach (var path in Directory.GetFiles(Path.Combine(root, "requests"), "*.json").Order(StringComparer.Ordinal))
        {
            var name = Path.GetFileName(path);
            if (name.StartsWith("04-retract-") || name.EndsWith("sov_pt_republic.json")) continue; // 引用開發庫既有紀錄
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (req["_geometryFrom"] is { } g) body["geometry"] = geoms[g.ToJsonString().Trim('"')].DeepClone();
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync(Fill((string)req["_post"]!), new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
            ids[(string)req["_placeholder"]!] = data.GetProperty("id").GetString()!;
        }
        return ids;
    }

    [Fact]
    public async Task Ww1_batch_1_is_accepted_and_maps_regimes_on_screenshot_dates()
    {
        var k = new ApiTestKit(fx);
        var ids = await ReplayAsync(k);

        async Task<Dictionary<string, JsonElement>> On(string date)
        {
            var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK)).GetProperty("data");
            return data.GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Select(f => f.GetProperty("properties"))
                .Where(p => p.GetProperty("regimeSlug").GetString()!.EndsWith(k.Tag))
                .ToDictionary(p => p.GetProperty("recordId").GetString()!);
        }
        string Slug(JsonElement p) => p.GetProperty("regimeSlug").GetString()![..^(k.Tag.Length + 1)];

        // 1908-10-07：奧匈（起事件＝波士尼亞併吞，已查證）、鄂圖曼（含利比亞）、蒙特內哥羅親王國
        var d0 = await On("1908-10-07");
        var s0 = d0.Values.Select(Slug).ToHashSet();
        Assert.Contains("principality-of-montenegro", s0);
        Assert.DoesNotContain("kingdom-of-montenegro", s0);
        Assert.Equal("verified", d0[ids["SOV_AH"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Contains(ids["SOV_OT_A"], d0.Keys);

        // 1913-01-01：阿爾巴尼亞臨時政府（非主權）、義屬多德卡尼斯（非主權）、利比亞已歸義大利
        var d1 = await On("1913-01-01");
        Assert.Equal("not_sovereign", d1[ids["SOV_AL_PROV"]].GetProperty("layerStatus").GetString());
        Assert.Equal("not_sovereign", d1[ids["SOV_IT_AEGEAN"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_LY_TR"], d1.Keys);
        Assert.Contains(ids["SOV_OT_D"], d1.Keys);
        Assert.Equal("pending", d1[ids["SOV_AL_PROV"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal(0, d1[ids["SOV_AL_PROV"]].GetProperty("startEvent").GetProperty("citations").GetArrayLength());

        // 1913-07-01：倫敦割讓區待分配（非主權）
        Assert.Equal("not_sovereign", (await On("1913-07-01"))[ids["SOV_LONDON"]].GetProperty("layerStatus").GetString());

        // 1913-09-01：布加勒斯特和約後；克里特國與割讓區都已不在
        var d3 = await On("1913-09-01");
        Assert.Contains(ids["SOV_GR_B"], d3.Keys);
        Assert.DoesNotContain(ids["SOV_LONDON"], d3.Keys);
        Assert.DoesNotContain("cretan-state", d3.Values.Select(Slug));
        Assert.Equal("verified", d3[ids["SOV_RS_B"]].GetProperty("startEvent").GetProperty("verification").GetString());

        // 1914-07-28：奧匈—塞爾維亞衝突（開放迄日）
        var raw = await (await k.R.GetAsync("/api/v1/conflicts?date=1914-07-28")).Content.ReadAsStringAsync();
        Assert.Contains(ids["CF_AH_RS"], raw);
        Assert.DoesNotContain(ids["CF_BG_RS"], raw);
    }
}
