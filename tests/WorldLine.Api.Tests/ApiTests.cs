using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;

namespace WorldLine.Api.Tests;

/// <summary>
/// 以 WebApplicationFactory 在記憶體內啟動 API，連到專用測試資料庫（WORLDLINE_TEST_DB）。
/// 寫入測試會真的 commit 到測試庫（I5 不可刪），因此每個測試都建立自己的新政權，彼此不干擾、可重複執行。
/// </summary>
public sealed class ApiFactory : WebApplicationFactory<Program>
{
    public const string TestKey = "integration-test-key-not-a-secret";

    protected override void ConfigureWebHost(IWebHostBuilder builder)
    {
        builder.UseEnvironment("Development");
        builder.UseSetting("ConnectionStrings:DefaultConnection", TestDb.ConnectionString ?? "");
        builder.UseSetting(Api.ApiKeyFilter.ConfigKey, TestKey);
    }
}

public class ApiTests(ApiFactory factory) : IClassFixture<ApiFactory>
{
    private static readonly string Tang = "0b1e0000-0000-4000-8000-000000000006";

    private async Task<HttpClient> ClientAsync(bool withKey = false)
    {
        await TestDatabase.EnsureReadyAsync();
        var client = factory.CreateClient();
        if (withKey) client.DefaultRequestHeaders.Add(Api.ApiKeyFilter.HeaderName, ApiFactory.TestKey);
        return client;
    }

    internal static async Task<JsonNode> JsonAsync(HttpResponseMessage res, HttpStatusCode expected)
    {
        var body = await res.Content.ReadAsStringAsync();
        Assert.True(res.StatusCode == expected, $"預期 {(int)expected}，實得 {(int)res.StatusCode}：{body}");
        return JsonNode.Parse(body)!;
    }

    internal static object Square(double x, double y, double size = 5) => new
    {
        type = "Polygon",
        coordinates = new[] { new[] { new[] { x, y }, new[] { x + size, y }, new[] { x + size, y + size }, new[] { x, y + size }, new[] { x, y } } },
    };

    internal static async Task<(string Id, int Version)> CreateRegimeAsync(HttpClient client, string from = "0100", string? to = "0200")
    {
        var res = await client.PostAsJsonAsync("/api/v1/regimes", new
        {
            selfName = $"測試國-{Guid.NewGuid():N}"[..16],
            existenceFrom = from,
            existenceTo = to,
            aliases = new[] { new { aliasName = "測試別名", aliasType = "historiographic" } },
        });
        var json = await JsonAsync(res, HttpStatusCode.Created);
        Assert.NotNull(res.Headers.Location);
        return (json["regime"]!["id"]!.GetValue<string>(), json["regime"]!["version"]!.GetValue<int>());
    }

    // ---------- 讀取（公開） ----------

    [Fact]
    public async Task Regimes_in_220_are_han_and_wei_with_split_origin()
    {
        var client = await ClientAsync();
        var arr = (await JsonAsync(await client.GetAsync("/api/v1/regimes?year=220"), HttpStatusCode.OK)).AsArray();
        var seeded = arr.Where(r => r!["id"]!.GetValue<string>().StartsWith("0b1e0000")).ToList();
        Assert.Equal(["漢", "魏"], seeded.Select(r => r!["selfName"]!.GetValue<string>()).Order());
        var wei = seeded.Single(r => r!["selfName"]!.GetValue<string>() == "魏")!;
        Assert.Equal("split", wei["originTransitionType"]!.GetValue<string>());
        Assert.Equal("abdicated", wei["status"]!.GetValue<string>());
    }

    [Fact]
    public async Task Regime_detail_separates_abdication_and_destruction()
    {
        var client = await ClientAsync();
        var wei = await JsonAsync(await client.GetAsync("/api/v1/regimes/0b1e0000-0000-4000-8000-000000000002"), HttpStatusCode.OK);
        Assert.Equal("漢", wei["predecessor"]!["selfName"]!.GetValue<string>());
        var jin = wei["successors"]!.AsArray().Single()!;
        Assert.Equal("晉", jin["selfName"]!.GetValue<string>());
        Assert.Equal("abdication", jin["originTransitionType"]!.GetValue<string>());

        var shu = await JsonAsync(await client.GetAsync("/api/v1/regimes/0b1e0000-0000-4000-8000-000000000003"), HttpStatusCode.OK);
        Assert.Equal("destroyed", shu["regime"]!["status"]!.GetValue<string>());
        Assert.Equal("0b1e0000-0000-4000-8000-000000000002", shu["regime"]!["destroyedByRegimeId"]!.GetValue<string>());
        Assert.Contains(shu["aliases"]!.AsArray(), a => a!["aliasName"]!.GetValue<string>() == "蜀漢");
    }

    [Fact]
    public async Task Territories_return_geojson_feature_collection()
    {
        var client = await ClientAsync();
        var res = await client.GetAsync("/api/v1/territories?year=220");
        var fc = await JsonAsync(res, HttpStatusCode.OK);
        Assert.Equal("FeatureCollection", fc["type"]!.GetValue<string>());
        var features = fc["features"]!.AsArray();
        Assert.NotEmpty(features);
        foreach (var f in features)
        {
            Assert.Equal("Feature", f!["type"]!.GetValue<string>());
            Assert.Equal("MultiPolygon", f["geometry"]!["type"]!.GetValue<string>());
            Assert.NotNull(f["properties"]!["regimeId"]);
            Assert.True(string.CompareOrdinal(f["properties"]!["validFrom"]!.GetValue<string>(), "0220-12-31") <= 0);
            Assert.NotNull(f["properties"]!["validFromPrecision"]);
        }
        var han = features.Single(f => f!["properties"]!["regimeId"]!.GetValue<string>() == "0b1e0000-0000-4000-8000-000000000001")!;
        Assert.True(han["properties"]!["isIllustrative"]!.GetValue<bool>());
    }

    [Fact]
    public async Task Tang_observer_sees_arab_empire_as_dashi_in_750()
    {
        var client = await ClientAsync();
        var fc = await JsonAsync(await client.GetAsync($"/api/v1/territories?year=750&observer={Tang}"), HttpStatusCode.OK);
        var names = fc["features"]!.AsArray()
            .Select(f => (Self: f!["properties"]!["selfName"]!.GetValue<string>(), Display: f["properties"]!["displayName"]!.GetValue<string>()))
            .ToList();
        Assert.Contains(("唐", "唐"), names);
        Assert.Contains(("阿拔斯哈里發國", "大食"), names);
    }

    [Fact]
    public async Task Events_lineage_presets_and_reign_eras()
    {
        var client = await ClientAsync();
        var events = (await JsonAsync(await client.GetAsync("/api/v1/events?year=751"), HttpStatusCode.OK)).AsArray();
        var talas = events.Single(e => e!["id"]!.GetValue<string>() == "battle-of-talas-751")!;
        Assert.Equal("month", talas["precision"]!.GetValue<string>());
        Assert.True(talas["approximate"]!.GetValue<bool>());
        Assert.Equal(3, talas["perspectiveCount"]!.GetValue<int>());
        var perspectives = (await JsonAsync(await client.GetAsync("/api/v1/events/battle-of-talas-751/perspectives"), HttpStatusCode.OK)).AsArray();
        Assert.Equal(3, perspectives.Count);

        var presets = (await JsonAsync(await client.GetAsync("/api/v1/lineage-presets"), HttpStatusCode.OK)).AsArray();
        Assert.True(presets[0]!["isDefault"]!.GetValue<bool>());
        Assert.Single(presets, p => p!["isDefault"]!.GetValue<bool>());
        var members = (await JsonAsync(await client.GetAsync($"/api/v1/lineage-presets/{presets[0]!["id"]}/regimes"), HttpStatusCode.OK)).AsArray();
        Assert.Equal(["漢", "魏", "晉"], members.Select(m => m!["regime"]!["selfName"]!.GetValue<string>()));

        var eras = (await JsonAsync(await client.GetAsync("/api/v1/reign-eras?year=742"), HttpStatusCode.OK)).AsArray();
        Assert.Contains(eras, e => e!["label"]!.GetValue<string>() == "天寶元年");
    }

    [Fact]
    public async Task Errors_are_problem_details()
    {
        var client = await ClientAsync();
        var res = await client.GetAsync($"/api/v1/regimes/{Guid.NewGuid()}");
        Assert.Equal(HttpStatusCode.NotFound, res.StatusCode);
        Assert.Equal("application/problem+json", res.Content.Headers.ContentType?.MediaType);
        var missingYear = await client.GetAsync("/api/v1/territories");
        Assert.Equal(HttpStatusCode.BadRequest, missingYear.StatusCode);
        Assert.Equal("application/problem+json", missingYear.Content.Headers.ContentType?.MediaType);
    }

    // ---------- 寫入（需 API Key） ----------

    [Fact]
    public async Task Writes_without_or_with_wrong_key_are_rejected()
    {
        var anon = await ClientAsync();
        var body = new { selfName = "未授權", existenceFrom = "0001", existenceTo = "0002" };
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PostAsJsonAsync("/api/v1/regimes", body)).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PatchAsJsonAsync($"/api/v1/regimes/{Tang}", new { version = 0, changeReason = "x", selfName = "x" })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PostAsJsonAsync($"/api/v1/regimes/{Tang}/territories", new { validFrom = "0700", validTo = "0701", geometry = Square(0, 0) })).StatusCode);
        Assert.Equal(HttpStatusCode.Unauthorized, (await anon.PatchAsJsonAsync($"/api/v1/territories/{Guid.NewGuid()}/correct", new { version = 0, reason = "x" })).StatusCode);

        var wrong = factory.CreateClient();
        wrong.DefaultRequestHeaders.Add(Api.ApiKeyFilter.HeaderName, "wrong-key");
        var res = await wrong.PostAsJsonAsync("/api/v1/regimes", body);
        Assert.Equal(HttpStatusCode.Unauthorized, res.StatusCode);
        Assert.Equal("application/problem+json", res.Content.Headers.ContentType?.MediaType);
    }

    [Fact]
    public async Task Writes_are_disabled_when_server_has_no_key()
    {
        await TestDatabase.EnsureReadyAsync();
        using var noKey = factory.WithWebHostBuilder(b => b.UseSetting(Api.ApiKeyFilter.ConfigKey, ""));
        var client = noKey.CreateClient();
        client.DefaultRequestHeaders.Add(Api.ApiKeyFilter.HeaderName, ApiFactory.TestKey);
        var res = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "x", existenceFrom = "0001", existenceTo = "0002" });
        Assert.Equal(HttpStatusCode.ServiceUnavailable, res.StatusCode);
        Assert.Equal(HttpStatusCode.OK, (await client.GetAsync("/api/v1/regimes?year=220")).StatusCode);
    }

    [Fact]
    public async Task Create_regime_validates_invariants()
    {
        var client = await ClientAsync(withKey: true);
        var blank = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "  ", existenceFrom = "0001", existenceTo = "0002" });
        Assert.Equal(HttpStatusCode.BadRequest, blank.StatusCode);
        var destroyedNoBy = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "x", existenceFrom = "0001", existenceTo = "0002", status = "destroyed" });
        Assert.Equal(HttpStatusCode.BadRequest, destroyedNoBy.StatusCode);
        var halfOrigin = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "x", existenceFrom = "0001", existenceTo = "0002", predecessorRegimeId = Tang });
        Assert.Equal(HttpStatusCode.BadRequest, halfOrigin.StatusCode);
        var unknownPredecessor = await client.PostAsJsonAsync("/api/v1/regimes", new { selfName = "x", existenceFrom = "0001", existenceTo = "0002", predecessorRegimeId = Guid.NewGuid(), originTransitionType = "split" });
        Assert.Equal(HttpStatusCode.BadRequest, unknownPredecessor.StatusCode);
    }

    [Fact]
    public async Task Patch_regime_enforces_state_machine_version_and_reason()
    {
        var client = await ClientAsync(withKey: true);
        var (id, version) = await CreateRegimeAsync(client);
        var (destroyer, _) = await CreateRegimeAsync(client);

        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/regimes/{id}", new { version, selfName = "無原因" })).StatusCode);
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/regimes/{id}", new { version, changeReason = "滅亡缺消滅方", status = "destroyed" })).StatusCode);
        Assert.Equal(HttpStatusCode.Conflict, (await client.PatchAsJsonAsync($"/api/v1/regimes/{id}", new { version = version + 5, changeReason = "舊版本", selfName = "x" })).StatusCode);

        var ok = await JsonAsync(await client.PatchAsJsonAsync($"/api/v1/regimes/{id}",
            new { version, changeReason = "為測試標記滅亡", status = "destroyed", destroyedByRegimeId = destroyer }), HttpStatusCode.OK);
        Assert.Equal("destroyed", ok["regime"]!["status"]!.GetValue<string>());
        Assert.Equal(version + 1, ok["regime"]!["version"]!.GetValue<int>());

        // 終止狀態之間不可互轉（禪讓 ≠ 滅亡）
        var back = await client.PatchAsJsonAsync($"/api/v1/regimes/{id}", new { version = version + 1, changeReason = "改成禪讓", status = "abdicated" });
        Assert.Equal(HttpStatusCode.BadRequest, back.StatusCode);
    }

    [Fact]
    public async Task Territory_create_overlap_and_correction_flow()
    {
        var client = await ClientAsync(withKey: true);
        var (regime, _) = await CreateRegimeAsync(client, "0100", "0200");

        var created = await JsonAsync(await client.PostAsJsonAsync($"/api/v1/regimes/{regime}/territories",
            new { validFrom = "0100", validTo = "0150", geometry = Square(110, 30), isIllustrative = true, source = "測試" }), HttpStatusCode.Created);
        Assert.Equal("MultiPolygon", created["geometry"]!["type"]!.GetValue<string>());
        var territoryId = created["id"]!.GetValue<string>();

        // 期間超出政權存續 → 400；I3 正式疆域重疊 → 409；標記爭議可並存 → 201
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PostAsJsonAsync($"/api/v1/regimes/{regime}/territories",
            new { validFrom = "0090", validTo = "0120", geometry = Square(110, 30) })).StatusCode);
        var overlap = await client.PostAsJsonAsync($"/api/v1/regimes/{regime}/territories",
            new { validFrom = "0140", validTo = "0160", geometry = Square(111, 31) });
        Assert.Equal(HttpStatusCode.Conflict, overlap.StatusCode);
        Assert.Equal("application/problem+json", overlap.Content.Headers.ContentType?.MediaType);
        Assert.Equal(HttpStatusCode.Created, (await client.PostAsJsonAsync($"/api/v1/regimes/{regime}/territories",
            new { validFrom = "0140", validTo = "0160", geometry = Square(111, 31), isDisputed = true })).StatusCode);

        // I5 修正：缺原因 → 400；正確修正 → 新版本、舊版本保留並指向新版本
        Assert.Equal(HttpStatusCode.BadRequest, (await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct",
            new { version = 0, geometry = Square(112, 30) })).StatusCode);
        var corrected = await JsonAsync(await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct",
            new { version = 0, reason = "依新考據修正西界", geometry = Square(112, 30) }), HttpStatusCode.OK);
        Assert.Equal(territoryId, corrected["previousId"]!.GetValue<string>());
        var newId = corrected["current"]!["id"]!.GetValue<string>();
        Assert.NotEqual(territoryId, newId);

        // 舊版本不可再修正
        Assert.Equal(HttpStatusCode.Conflict, (await client.PatchAsJsonAsync($"/api/v1/territories/{territoryId}/correct",
            new { version = 0, reason = "再改一次" })).StatusCode);

        // 快照只看現行版本；歷史保留兩版
        var snapshot = await JsonAsync(await client.GetAsync("/api/v1/territories?year=120"), HttpStatusCode.OK);
        var mine = snapshot["features"]!.AsArray().Where(f => f!["properties"]!["regimeId"]!.GetValue<string>() == regime).ToList();
        Assert.Equal(newId, Assert.Single(mine)!["id"]!.GetValue<string>());

        var history = await JsonAsync(await client.GetAsync($"/api/v1/regimes/{regime}/territories"), HttpStatusCode.OK);
        var old = history["features"]!.AsArray().Single(f => f!["id"]!.GetValue<string>() == territoryId)!;
        Assert.Equal(newId, old["properties"]!["supersededBy"]!.GetValue<string>());
        Assert.Equal("依新考據修正西界", old["properties"]!["correctionReason"]!.GetValue<string>());
        Assert.NotNull(old["properties"]!["correctedAt"]);
    }
}
