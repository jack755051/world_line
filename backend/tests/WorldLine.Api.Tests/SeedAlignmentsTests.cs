using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 把 data/seed/ww2/alignments/requests/*.json 送到測試容器（不是 appdb_ww2）：
/// 先用法國那批的政權檔建德國（slug 加測試標籤），再依序送陣營來源與切片，確認 API 接受。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedAlignmentsTests(PostGisFixture fx)
{
    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed", "ww2");
    }

    private static async Task Send(ApiTestKit k, string path, Dictionary<string, string> ids)
    {
        var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
        var body = req["body"]!.AsObject();
        if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
        string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids[m.Groups[1].Value]);
        var res = await k.W.PostAsync(Fill((string)req["_post"]!), new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
        var data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data");
        ids[(string)req["_placeholder"]!] = data.GetProperty("id").GetString()!;
    }

    [Fact]
    public async Task Alignment_seed_requests_are_accepted()
    {
        var k = new ApiTestKit(fx);
        var ids = new Dictionary<string, string>();
        await Send(k, Path.Combine(SeedRoot(), "france-1940-07-15", "requests", "02-regime-deutsches-reich.json"), ids);
        foreach (var path in Directory.GetFiles(Path.Combine(SeedRoot(), "alignments", "requests"), "*.json").Order(StringComparer.Ordinal))
            await Send(k, path, ids);

        var list = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{ids["REGIME_DE"]}/alignments"), HttpStatusCode.OK))
            .GetProperty("data").EnumerateArray().ToList();
        // 兩段：鋼鐵條約 [1939-05-22, 1940-09-27) 接三國同盟條約 [1940-09-27, 未定)，相接不重疊
        Assert.Equal(2, list.Count);
        Assert.All(list, a => Assert.Equal("axis", a.GetProperty("camp").GetString()));
        Assert.Equal("1939-05-22", list[0].GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal("1940-09-27", list[0].GetProperty("validPeriod").GetProperty("end").GetString());
        Assert.Equal("1940-09-27", list[1].GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal(JsonValueKind.Null, list[1].GetProperty("validPeriod").GetProperty("end").ValueKind);
        // 每筆都要有 primary 引用，且授權在允許清單（使用權）
        Assert.All(list, a => Assert.Contains(a.GetProperty("citations").EnumerateArray(), c =>
            c.GetProperty("role").GetString() == "primary"
            && new[] { "us_federal_pd", "pd_expired" }.Contains(c.GetProperty("licenseCode").GetString())));
    }
}
