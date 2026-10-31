using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 先重播 WW1 第一批（balkans-1908-1914），再依序重播第二批 data/seed/ww1/war-1914-1918/requests/sub1..sub3（DRAFT）到測試容器（不是 appdb_ww2）。
/// 前置批次的政權、海岸線、美國來源先建替身。第二批 sub1 先撤回第一批迄於 1914-07-29 的紀錄再延長重送（先撤後增），這裡一併驗證。
/// 檢查：全部通過 API 驗證、四個截圖日的政權與層級、佔領歸屬（控制層級、共同佔領）、待查證事件沒有引用、衝突起訖。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedWw1War1914Tests(PostGisFixture fx)
{
    private static readonly string[] PriorRegimes = ["REGIME_IT", "REGIME_RO", "REGIME_GR", "REGIME_BE", "REGIME_DK", "REGIME_NO", "REGIME_SE", "REGIME_BG", "REGIME_FR3", "REGIME_IT_AEGEAN", "REGIME_PT",
        "REGIME_LU", "REGIME_EE", "REGIME_FI", "REGIME_CS", "REGIME_PL", "REGIME_US"];

    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww1");
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
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
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

    private static async Task<Dictionary<string, string>> ReplayAsync(ApiTestKit k)
    {
        var root = SeedRoot();
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
        ids["SRC_OHM_US"] = (await k.Source("dataset", "cc0", $"OHM US {k.Tag}")).ToString();
        // 第一批（葡萄牙共和國的撤回／重送引用開發庫既有 id，略過）
        var b1 = Path.Combine(root, "balkans-1908-1914");
        await ReplayDirAsync(k, Path.Combine(b1, "requests"), await Geoms(Path.Combine(b1, "ww1-1908-1914-derived.geojson")), ids,
            name => name.StartsWith("04-retract-") || name.EndsWith("sov_pt_republic.json"));
        var b2 = Path.Combine(root, "war-1914-1918");
        var g2 = await Geoms(Path.Combine(b2, "ww1-1914-1918-derived.geojson"));
        foreach (var sub in new[] { "sub1", "sub2", "sub3" })
            await ReplayDirAsync(k, Path.Combine(b2, "requests", sub), g2, ids, _ => false);
        return ids;
    }

    [Fact]
    public async Task Ww1_batch_2_is_accepted_and_maps_regimes_and_occupations_on_screenshot_dates()
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
        async Task<string> Conflicts(string date) => await (await k.R.GetAsync($"/api/v1/conflicts?date={date}")).Content.ReadAsStringAsync();

        // 第一批延長的紀錄取代原紀錄；1914-07-28 仍是同一範圍
        var d0 = await On("1914-07-28");
        Assert.Contains(ids["SOV_AH_R"], d0.Keys);
        Assert.DoesNotContain(ids["SOV_AH"], d0.Keys);

        // 1915-06-01：比利時、法國北部佔領區（非主權、德國管理），伊瑟河以西的比利時；義奧開戰
        var d1 = await On("1915-06-01");
        var be = d1[ids["SOV_GG_BE_B"]];
        Assert.Equal("not_sovereign", be.GetProperty("layerStatus").GetString());
        Assert.Equal("civil_administration", be.GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Equal("military_administration", d1[ids["SOV_NFR_A"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Contains(ids["SOV_BE_3"], d1.Keys);
        Assert.Contains(ids["SOV_EG"], d1.Keys);
        Assert.Contains(ids["SOV_RU_EMP_R"], d1.Keys);
        var c1 = await Conflicts("1915-06-01");
        Assert.Contains(ids["CF_IT_AH"], c1);
        Assert.Contains(ids["CF_AH_RS_R"], c1);
        Assert.DoesNotContain(ids["CF_BG_RS"], c1);

        // 1916-12-01：多布羅加被佔領、塞爾維亞與蒙特內哥羅整個被佔領（塞爾維亞政權不在地圖上）、波蘭攝政王國（共同佔領）
        var d2 = await On("1916-12-01");
        Assert.Contains(ids["SOV_RO_B_2"], d2.Keys);
        Assert.True(d2[ids["SOV_DOB_A"]].GetProperty("occupation").GetProperty("coOccupied").GetBoolean());
        Assert.Equal("annexed", d2[ids["SOV_SERBIA_BG"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Contains(ids["SOV_MGG_MN"], d2.Keys);
        Assert.DoesNotContain("kingdom-of-serbia", d2.Values.Select(Slug));
        Assert.True(d2[ids["SOV_PL_REGENCY"]].GetProperty("occupation").GetProperty("coOccupied").GetBoolean());
        Assert.Equal("pending", d2[ids["SOV_SERBIA_BG"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal(0, d2[ids["SOV_SERBIA_BG"]].GetProperty("startEvent").GetProperty("citations").GetArrayLength());
        Assert.Contains(ids["CF_RO_AH"], await Conflicts("1916-12-01"));

        // 1918-03-04：布列斯特和約後；烏克蘭（法理）、立陶宛（非主權）、俄羅斯蘇維埃共和國；瓦拉幾亞仍被佔領
        var d3 = await On("1918-03-04");
        Assert.Equal("de_jure", d3[ids["SOV_UA_1"]].GetProperty("layerStatus").GetString());
        Assert.Equal("not_sovereign", d3[ids["SOV_LT"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_RSFSR_C_2"], d3.Keys);
        Assert.DoesNotContain("russian-empire", d3.Values.Select(Slug));
        Assert.Contains(ids["SOV_RO_WAL"], d3.Keys);
        Assert.Equal("verified", d3[ids["SOV_LT"]].GetProperty("startEvent").GetProperty("verification").GetString());
        var c3 = await Conflicts("1918-03-04");
        Assert.DoesNotContain(ids["CF_RSFSR_DE"], c3);
        Assert.Contains(ids["CF_RSFSR_DE"], await Conflicts("1918-03-02"));

        // 1918-11-11：停戰日；停戰線以東的比、法佔領區，捷克斯洛伐克、斯洛維尼亞人克羅埃西亞人和塞爾維亞人國、波蘭；德法衝突到停戰當日為止
        var d4 = await On("1918-11-11");
        Assert.Contains(ids["SOV_GG_BE_C"], d4.Keys);
        Assert.Contains(ids["SOV_NFR_B"], d4.Keys);
        Assert.Contains(ids["SOV_CS"], d4.Keys);
        Assert.Equal("not_sovereign", d4[ids["SOV_SCS"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_PL"], d4.Keys);
        Assert.Contains(ids["SOV_RS_B_4"], d4.Keys);
        Assert.Contains(ids["SOV_OT_F"], d4.Keys);
        // 衝突期間含迄事件當日（ConflictsEndpoints：迄事件起日＋1 天為開區間終點），停戰隔天才消失
        Assert.Contains(ids["CF_DE_FR"], await Conflicts("1918-11-11"));
        Assert.DoesNotContain(ids["CF_DE_FR"], await Conflicts("1918-11-12"));
    }
}
