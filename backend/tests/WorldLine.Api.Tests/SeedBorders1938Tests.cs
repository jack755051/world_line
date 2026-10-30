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
        var geoms = JsonNode.Parse(await File.ReadAllTextAsync(Path.Combine(root, "borders-ohm-1938-1940.geojson")))!["features"]!.AsArray()
            .ToDictionary(f => f!["id"]!.GetValue<long>(), f => f!["geometry"]!);
        var ids = new Dictionary<string, string>();
        foreach (var path in Directory.GetFiles(Path.Combine(root, "requests"), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (req["_geometryFrom"] is { } g) body["geometry"] = geoms[g.GetValue<long>()].DeepClone();
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync((string)req["_post"]!, new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
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

        // 1938-10-15：德國起事件＝德奧合併（已查證），迄事件＝德捷邊界最終劃定（待查證）
        var reich1 = (await On("1938-10-15"))[ids["SOV_R2704712"]];
        Assert.Equal("verified", reich1.GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal("pending", reich1.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal(0, reich1.GetProperty("endEvent").GetProperty("citations").GetArrayLength());

        // 1939-04-15：阿爾巴尼亞已由義大利兼領；捷克斯洛伐克已不在
        var slugs2 = (await On("1939-04-15")).Values.Select(Slug).ToHashSet();
        Assert.Contains("albania-under-italy", slugs2);
        Assert.DoesNotContain("albanian-kingdom", slugs2);
        Assert.DoesNotContain("czechoslovak-republic", slugs2);
        Assert.Contains("slovak-state-1939", slugs2);

        // 1939-10-15：波蘭與但澤都已不在（OHM 在 10-06／09-01 結束）
        var slugs3 = (await On("1939-10-15")).Values.Select(Slug).ToHashSet();
        Assert.DoesNotContain("polish-republic", slugs3);
        Assert.DoesNotContain("free-city-of-danzig", slugs3);

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
