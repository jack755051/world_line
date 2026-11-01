using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/borders-1938-1940/requests/*.json（主權圖層試驗，DRAFT）整批送到測試容器（不是 appdb_ww2）。
/// 幾何依 `_geometryFrom` 從 borders-ohm-1938-1940.geojson 讀入。檢查：全部通過 API 驗證、
/// 截圖日的政權與起訖事件、待查證事件沒有引用。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedBorders1938Tests(PostGisFixture fx)
{
    private static string BatchRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww2", "borders-1938-1940");
    }

    private static async Task<Dictionary<string, string>> ReplayAsync(ApiTestKit k)
    {
        var root = BatchRoot();
        // feature id：OHM 關係 id（數字）或 05-* 修正用的衍生幾何（FIX_*，borders-fixes-1938-1940.geojson）
        var geoms = new Dictionary<string, JsonNode>();
        foreach (var file in new[] { "borders-ohm-1938-1940.geojson", "borders-fixes-1938-1940.geojson" })
            foreach (var f in JsonNode.Parse(await File.ReadAllTextAsync(Path.Combine(root, file)))!["features"]!.AsArray())
                geoms[f!["id"]!.ToJsonString().Trim('"')] = f["geometry"]!;
        var ids = new Dictionary<string, string>();
        foreach (var path in Directory.GetFiles(Path.Combine(root, "requests"), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (req["_geometryFrom"] is { } g) body["geometry"] = geoms[g.ToJsonString().Trim('"')].DeepClone();
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync(Fill((string)req["_post"]!), new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            // 05-2-*：撤回（I5，不原地修改）回 200；其他新增回 201
            var isRetraction = ((string)req["_post"]!).EndsWith("/retraction");
            var data = (await ApiTestKit.Expect(res, isRetraction ? HttpStatusCode.OK : HttpStatusCode.Created)).GetProperty("data");
            ids[(string)req["_placeholder"]!] = data.GetProperty("id").GetString()!;
        }
        return ids;
    }

    [Fact]
    public async Task Borders_batch_is_accepted_and_maps_events_on_screenshot_dates()
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

        // 1938-01-01：奧地利、捷克斯洛伐克仍在；德國那筆沒有起事件（期初疆界不追溯）、迄事件＝德奧合併（已查證）
        var d0 = await On("1938-01-01");
        var slugs0 = d0.Values.Select(Slug).ToHashSet();
        Assert.Contains("federal-state-of-austria", slugs0);
        Assert.Contains("czechoslovak-republic", slugs0);
        var reich0 = d0[ids["SOV_R2693085"]];
        Assert.Equal(JsonValueKind.Null, reich0.GetProperty("startEvent").ValueKind);
        Assert.Equal("verified", reich0.GetProperty("endEvent").GetProperty("verification").GetString());

        // 1938-10-05：分區佔領中，德國仍是拆分後的前段（幾何不含蘇台德），迄事件＝分區佔領（已查證）
        var d05 = await On("1938-10-05");
        Assert.DoesNotContain(ids["SOV_R2704712"], d05.Keys);
        Assert.Equal("verified", d05[ids["SOV_R2704712_A"]].GetProperty("endEvent").GetProperty("verification").GetString());

        // 1938-10-15：蘇台德已畫入德國（修正紀錄）；起事件＝分區佔領（4 筆 FRUS 引用），迄事件＝德捷邊界最終劃定（待查證）
        var reich1 = (await On("1938-10-15"))[ids["SOV_FIX_REICH_SUDETEN"]];
        Assert.Equal("verified", reich1.GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal(4, reich1.GetProperty("startEvent").GetProperty("citations").GetArrayLength());
        Assert.Equal("pending", reich1.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal(0, reich1.GetProperty("endEvent").GetProperty("citations").GetArrayLength());
        Assert.StartsWith("relation/2704712 v208 ∪", reich1.GetProperty("geometry").GetProperty("locator").GetString());

        // 1939-04-15：阿爾巴尼亞已由義大利兼領；捷克斯洛伐克已不在
        var slugs2 = (await On("1939-04-15")).Values.Select(Slug).ToHashSet();
        Assert.Contains("albania-under-italy", slugs2);
        Assert.DoesNotContain("albanian-kingdom", slugs2);
        Assert.DoesNotContain("czechoslovak-republic", slugs2);
        Assert.Contains("slovak-state-1939", slugs2);

        // 1939-10-15：波蘭與但澤都已不在（OHM 在 10-06／09-01 結束）；但澤已畫入德國、波蘭中部為德佔軍事管理（非主權）
        var d3 = await On("1939-10-15");
        var slugs3 = d3.Values.Select(Slug).ToHashSet();
        Assert.DoesNotContain("polish-republic", slugs3);
        Assert.DoesNotContain("free-city-of-danzig", slugs3);
        Assert.Equal("verified", d3[ids["SOV_FIX_REICH_DANZIG"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.DoesNotContain(ids["SOV_FIX_MILVERW_PL"], d3.Keys); // 頁碼更正後撤回重加（05-4）
        var pl = d3[ids["SOV_FIX_MILVERW_PL_R2"]];
        Assert.Equal("german-military-administration-poland", Slug(pl));
        Assert.Equal("not_sovereign", pl.GetProperty("layerStatus").GetString());
        Assert.Equal("verified", pl.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal("Doc. 477, p. 560, nn. 2–3", pl.GetProperty("endEvent").GetProperty("citations")[0].GetProperty("locator").GetString());

        // 1940-04-01：蘇聯用扣除比薩拉比亞的修正紀錄；原紀錄已撤回
        var d35 = await On("1940-04-01");
        Assert.Contains(ids["SOV_FIX_SU_NO_BESSARABIA"], d35.Keys);
        Assert.DoesNotContain(ids["SOV_R2851878"], d35.Keys);

        // 1940-09-15：波羅的海三國已併入蘇聯；比北軍政府標示為非主權
        var d4 = await On("1940-09-15");
        var slugs4 = d4.Values.Select(Slug).ToHashSet();
        Assert.DoesNotContain("republic-of-latvia", slugs4);
        Assert.Contains("french-state-vichy", slugs4);
        Assert.Equal("not_sovereign", d4[ids["SOV_R2748553"]].GetProperty("layerStatus").GetString());
        var su = d4[ids["SOV_R2848812"]];
        Assert.Equal("cc_by", su.GetProperty("geometry").GetProperty("geometryLicense").GetString());
        Assert.False(string.IsNullOrEmpty(su.GetProperty("geometry").GetProperty("attribution").GetString()));
        Assert.Equal(98, su.GetProperty("geometry").GetProperty("ohmVersion").GetInt32());
    }
}
