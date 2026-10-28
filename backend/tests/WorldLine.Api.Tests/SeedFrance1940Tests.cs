using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/france-1940-07-15/requests/*.json 依序送到測試容器（不是 appdb_ww2），
/// 確認這批待 Tai 檢查的種子資料會被 API 接受（R7 引用、I1 區間、I3 同控制方不重疊、幾何有效）。
/// regime slug 與 theater code 加上測試標籤，避免與其他測試衝突。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedFrance1940Tests(PostGisFixture fx)
{
    private static string SeedDir()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww2", "france-1940-07-15", "requests");
    }

    private static async Task<Dictionary<string, string>> Replay(ApiTestKit k, bool includePending)
    {
        var ids = new Dictionary<string, string>();
        foreach (var path in Directory.GetFiles(SeedDir(), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            if (!includePending && req["_meta"]?["requiresDecision"]?.GetValue<bool>() == true) continue;
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (body["code"] is not null) body["code"] = $"{body["code"]}-{k.Tag}";
            var raw = Regex.Replace(body.ToJsonString(), @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync((string)req["_post"]!, new StringContent(raw, Encoding.UTF8, "application/json"));
            var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
            ids[(string)req["_placeholder"]!] = data.TryGetProperty("id", out var p) ? p.GetString()! : data.GetProperty("controlRecordId").GetString()!;
        }
        return ids;
    }

    private static async Task<List<JsonElement>> Features(ApiTestKit k, string date, Dictionary<string, string> ids)
    {
        var mine = ids.Where(kv => kv.Key.StartsWith("CR_")).Select(kv => Guid.Parse(kv.Value)).ToHashSet();
        return (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/control?date={date}"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Where(f => mine.Contains(f.GetProperty("properties").GetProperty("controlRecordId").GetGuid())).ToList();
    }

    private static Guid Id(Dictionary<string, string> ids, string key) => Guid.Parse(ids[key]);
    private static HashSet<Guid> Records(List<JsonElement> fs) =>
        fs.Select(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid()).ToHashSet();

    [Fact] // 全部（含待決的東北禁區）都要被 API 接受，且各區在同一天互不重疊（I3）
    public async Task France_1940_seed_requests_including_pending_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = await Replay(k, includePending: true);

        var jul17 = await Features(k, "1940-07-17", ids);
        Assert.Equal(new HashSet<Guid> { Id(ids, "CR_MAIN"), Id(ids, "CR_NORD"), Id(ids, "CR_AM_MIL"), Id(ids, "CR_ZI_PRE") }, Records(jul17));
        Assert.All(jul17, f => Assert.Equal("MultiPolygon", f.GetProperty("geometry").GetProperty("type").GetString()));

        var aug15 = await Features(k, "1940-08-15", ids);
        Assert.Equal(new HashSet<Guid> { Id(ids, "CR_MAIN"), Id(ids, "CR_NORD"), Id(ids, "CR_AM_CDZ"), Id(ids, "CR_ZI") }, Records(aug15));
        var am = aug15.Single(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid() == Id(ids, "CR_AM_CDZ"));
        Assert.Equal("direct_rule", am.GetProperty("properties").GetProperty("controlType").GetString());

        // 北部兩省在本體區之前就已歸布魯塞爾軍管
        Assert.Equal(new HashSet<Guid> { Id(ids, "CR_NORD") }, Records(await Features(k, "1940-06-20", ids)));
    }

    [Fact] // 預設送出（不含待決）也要能完整跑完
    public async Task France_1940_seed_requests_without_pending_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = await Replay(k, includePending: false);
        Assert.False(ids.ContainsKey("CR_ZI"));
        Assert.Equal(3, (await Features(k, "1940-07-17", ids)).Count);
    }
}
