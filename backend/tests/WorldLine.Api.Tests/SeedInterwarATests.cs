using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 先重播 WW1 第一、二批，再依序重播兩次大戰之間 A 批 data/seed/interwar/batch-a/requests/A1..A3（DRAFT）到測試容器（不是 appdb_ww2）。
/// 前置批次以外的政權與來源先建替身。A1 先撤回 WW1 第二批的德意志帝國紀錄（迄 1918-11-12 試驗終點），再以迄 1918-11-09 重送（先撤後增），這裡一併驗證。
/// 檢查：全部通過 API 驗證、三個截圖日的政權與層級、佔領歸屬、待查證事件沒有引用、衝突起訖。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedInterwarATests(PostGisFixture fx)
{
    private static readonly string[] Ww1PriorRegimes = ["REGIME_IT", "REGIME_RO", "REGIME_GR", "REGIME_BE", "REGIME_DK", "REGIME_NO", "REGIME_SE", "REGIME_BG", "REGIME_FR3", "REGIME_IT_AEGEAN", "REGIME_PT",
        "REGIME_LU", "REGIME_EE", "REGIME_FI", "REGIME_CS", "REGIME_PL", "REGIME_US"];
    // A 批另外引用的開發庫既有政權（WW1 兩批沒有建）
    private static readonly string[] InterwarPriorRegimes = ["REGIME_DANZIG", "REGIME_DE", "REGIME_HU", "REGIME_LT", "REGIME_LV", "REGIME_SU", "REGIME_TR", "REGIME_UK"];

    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed");
    }

    private static async Task<Dictionary<string, JsonNode>> Geoms(string file)
    {
        var geoms = new Dictionary<string, JsonNode>();
        foreach (var f in JsonNode.Parse(await File.ReadAllTextAsync(file))!["features"]!.AsArray())
            geoms[f!["id"]!.ToJsonString().Trim('"')] = f["geometry"]!;
        return geoms;
    }

    private static async Task ReplayDirAsync(ApiTestKit k, string dir, Dictionary<string, JsonNode> geoms, Dictionary<string, string> ids, Func<string, bool> skip)
    {
        foreach (var path in Directory.GetFiles(dir, "*.json").Order(StringComparer.Ordinal))
        {
            var name = Path.GetFileName(path);
            if (skip(name)) continue;
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (req["_geometryFrom"] is { } g) body["geometry"] = geoms[g.ToJsonString().Trim('"')].DeepClone();
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids.TryGetValue(m.Groups[1].Value, out var v) ? v : throw new Exception($"{name}: 缺少 {m.Groups[1].Value}"));
            var post = Fill((string)req["_post"]!);
            var res = await k.W.PostAsync(post, new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            if (post.EndsWith("/retraction"))
            {
                try { await ApiTestKit.Expect(res, HttpStatusCode.OK); }
                catch (Exception e) { throw new Exception($"{name}: {e.Message}", e); }
                continue;
            }
            JsonElement data;
            try { data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data"); }
            catch (Exception e) { throw new Exception($"{name}: {e.Message}", e); }
            ids[(string)req["_placeholder"]!] = data.GetProperty("id").GetString()!;
        }
    }

    private static async Task Stub(ApiTestKit k, Dictionary<string, string> ids, string ph)
    {
        var slug = $"{ph.ToLowerInvariant().Replace('_', '-')}-{k.Tag}";
        ids[ph] = (await k.Id(await k.W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug,
            names = new[] { new { nameKind = "self", originalText = ph, originalLang = "en", display = new Dictionary<string, string> { ["zh-Hant"] = ph, ["en"] = ph }, isPrimary = true } },
        }))).ToString();
    }

    private static async Task<Dictionary<string, string>> ReplayAsync(ApiTestKit k)
    {
        var root = SeedRoot();
        var ids = new Dictionary<string, string>();
        foreach (var ph in Ww1PriorRegimes) await Stub(k, ids, ph);
        ids["SRC_NE_LAND"] = (await k.Source("dataset", "cc0", $"Natural Earth {k.Tag}")).ToString();
        ids["SRC_OHM_US"] = (await k.Source("dataset", "cc0", $"OHM US {k.Tag}")).ToString();
        var b1 = Path.Combine(root, "ww1", "balkans-1908-1914");
        await ReplayDirAsync(k, Path.Combine(b1, "requests"), await Geoms(Path.Combine(b1, "ww1-1908-1914-derived.geojson")), ids,
            name => name.StartsWith("04-retract-") || name.EndsWith("sov_pt_republic.json"));
        var b2 = Path.Combine(root, "ww1", "war-1914-1918");
        var g2 = await Geoms(Path.Combine(b2, "ww1-1914-1918-derived.geojson"));
        foreach (var sub in new[] { "sub1", "sub2", "sub3" })
            await ReplayDirAsync(k, Path.Combine(b2, "requests", sub), g2, ids, _ => false);
        foreach (var ph in InterwarPriorRegimes) await Stub(k, ids, ph);
        var a = Path.Combine(root, "interwar", "batch-a");
        var ga = await Geoms(Path.Combine(a, "interwar-a-derived.geojson"));
        foreach (var sub in new[] { "A1", "A2", "A3" })
            await ReplayDirAsync(k, Path.Combine(a, "requests", sub), ga, ids, _ => false);
        return ids;
    }

    [Fact]
    public async Task Interwar_batch_a_is_accepted_and_maps_regimes_and_occupations_on_screenshot_dates()
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
        async Task<string> Conflicts(string date) => await (await k.R.GetAsync($"/api/v1/conflicts?date={date}")).Content.ReadAsStringAsync();

        // 先撤後增：德意志帝國迄 1918-11-09，11-09 起德意志國
        Assert.Contains(ids["SOV_DE_EMP_R2"], (await On("1918-11-08")).Keys);
        var d0 = await On("1918-11-10");
        Assert.DoesNotContain(ids["SOV_DE_EMP_R"], d0.Keys);
        Assert.DoesNotContain(ids["SOV_DE_EMP_R2"], d0.Keys);
        Assert.Contains(ids["SOV_DE_A"], d0.Keys);

        // 1919-07-01：凡爾賽簽字後、生效前；波蘭（東加利西亞仍由西烏克蘭控制）、匈牙利蘇維埃共和國、義大利佔領的原奧匈領土
        var d1 = await On("1919-07-01");
        Assert.Contains(ids["SOV_PL_A_3"], d1.Keys);
        Assert.Equal("not_sovereign", d1[ids["SOV_ZUNR"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_HU_SR"], d1.Keys);
        Assert.Contains(ids["SOV_DE_B"], d1.Keys);
        Assert.Equal("military_administration", d1[ids["SOV_IT_JULIAN"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Equal("pending", d1[ids["SOV_ZUNR"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal(0, d1[ids["SOV_ZUNR"]].GetProperty("startEvent").GetProperty("citations").GetArrayLength());
        var c1 = await Conflicts("1919-07-01");
        Assert.Contains(ids["CF_PL_RSFSR"], c1);
        Assert.Contains(ids["CF_PL_ZUNR"], c1);
        Assert.Contains(ids["CF_RO_HUSR"], c1);

        // 1921-04-01：里加和約後；希臘佔領士麥那、阜姆自由邦、薩爾與梅梅爾國際管理；希土戰爭進行中、波蘇戰爭已結束
        var d2 = await On("1921-04-01");
        Assert.Contains(ids["SOV_GR_B_1"], d2.Keys);
        Assert.Equal("military_administration", d2[ids["SOV_SMYRNA"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Contains(ids["SOV_FIUME_FS"], d2.Keys);
        Assert.Equal("not_sovereign", d2[ids["SOV_SAAR"]].GetProperty("layerStatus").GetString());
        Assert.Equal("civil_administration", d2[ids["SOV_MEMEL"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Equal("verified", d2[ids["SOV_GR_B_1"]].GetProperty("startEvent").GetProperty("verification").GetString());
        var c2 = await Conflicts("1921-04-01");
        Assert.Contains(ids["CF_GR_GNA"], c2);
        Assert.DoesNotContain(ids["CF_PL_RSFSR"], c2);
        Assert.Contains(ids["CF_PL_RSFSR"], await Conflicts("1921-03-18"));

        // 1923-08-01：洛桑條約簽字後；法比共同佔領魯爾、蘇聯、安卡拉大國民議會政府（共和國宣布前）；希土戰爭已結束
        var d3 = await On("1923-08-01");
        Assert.True(d3[ids["SOV_RUHR"]].GetProperty("occupation").GetProperty("coOccupied").GetBoolean());
        Assert.Contains(ids["SOV_DE_H_2"], d3.Keys);
        Assert.Contains(ids["SOV_SU"], d3.Keys);
        Assert.Contains(ids["SOV_GNA"], d3.Keys);
        Assert.DoesNotContain(ids["SOV_TR_A"], d3.Keys);
        Assert.Contains(ids["SOV_TR_A"], (await On("1923-11-01")).Keys);
        Assert.DoesNotContain(ids["CF_GR_GNA"], await Conflicts("1923-08-01"));
    }
}
