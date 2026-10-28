using System.Net;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/france-1940-07-15/requests/*.json 依序送到測試容器（不是 appdb_ww2），
/// 確認這批待 Tai 檢查的種子資料會被 API 接受（R7 引用、I1 區間、幾何有效）。
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

    [Fact]
    public async Task France_1940_07_15_seed_requests_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = new Dictionary<string, string>();
        Guid controlId = Guid.Empty;
        foreach (var path in Directory.GetFiles(SeedDir(), "*.json").Order(StringComparer.Ordinal))
        {
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (body["code"] is not null) body["code"] = $"{body["code"]}-{k.Tag}";
            var raw = Regex.Replace(body.ToJsonString(), @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
            var res = await k.W.PostAsync((string)req["_post"]!, new StringContent(raw, Encoding.UTF8, "application/json"));
            var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
            var id = data.TryGetProperty("id", out var p) ? p.GetString()! : data.GetProperty("controlRecordId").GetString()!;
            ids[(string)req["_placeholder"]!] = id;
            if ((string)req["_placeholder"]! == "CONTROL_RECORD") controlId = Guid.Parse(id);
        }
        Assert.NotEqual(Guid.Empty, controlId);

        var features = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/control?date=1940-07-15"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("featureCollection").GetProperty("features").EnumerateArray()
            .Where(f => f.GetProperty("properties").GetProperty("controlRecordId").GetGuid() == controlId).ToList();
        Assert.Single(features);
        Assert.Equal("MultiPolygon", features[0].GetProperty("geometry").GetProperty("type").GetString());
        Assert.Equal(4, features[0].GetProperty("properties").GetProperty("citations").GetArrayLength());
    }
}
