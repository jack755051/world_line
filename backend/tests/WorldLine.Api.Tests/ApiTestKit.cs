using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace WorldLine.Api.Tests;

/// <summary>以 API 建立測試資料（每個測試用自己的 slug／戰區代碼，共用同一個 PostGIS 容器）。</summary>
public sealed class ApiTestKit(PostGisFixture fx)
{
    public HttpClient W { get; } = fx.Writer();
    public HttpClient R { get; } = fx.Reader();
    public string Tag { get; } = Guid.NewGuid().ToString("N")[..8];

    public static JsonObject Square(double x, double y, double size = 1) => new()
    {
        ["type"] = "Polygon",
        ["coordinates"] = new JsonArray(new JsonArray(
            new JsonArray(x, y), new JsonArray(x + size, y), new JsonArray(x + size, y + size),
            new JsonArray(x, y + size), new JsonArray(x, y))),
    };

    public static async Task<JsonElement> Body(HttpResponseMessage res)
    {
        using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
        return doc.RootElement.Clone();
    }

    public static async Task<JsonElement> Expect(HttpResponseMessage res, HttpStatusCode status, string? code = null)
    {
        var body = await Body(res);
        Assert.True(res.StatusCode == status, $"預期 {status}，實際 {res.StatusCode}：{body}");
        Assert.Equal((int)status, body.GetProperty("statusCode").GetInt32());
        Assert.True(body.TryGetProperty("message", out _));
        if (code is not null) Assert.Equal(code, body.GetProperty("code").GetString());
        return body;
    }

    public async Task<Guid> Id(HttpResponseMessage res, string prop = "id") =>
        (await Expect(res, HttpStatusCode.Created)).GetProperty("data").GetProperty(prop).GetGuid();

    public Task<HttpResponseMessage> PostSource(string kind = "atlas_map", string publisher = "U.S. Military Academy",
        string? license = "us_federal_pd", string title = "WWII Europe atlas") =>
        W.PostAsJsonAsync("/api/v1/sources", new { sourceKind = kind, title, publisher, licenseCode = license });

    public async Task<Guid> Source(string kind = "atlas_map", string? license = "us_federal_pd", string title = "WWII Europe atlas") =>
        await Id(await PostSource(kind, license: license, title: title));

    public async Task<Guid> Regime(string name)
    {
        var res = await W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug = $"{name}-{Tag}",
            names = new[] { new { nameKind = "self", originalText = name, originalLang = "de", display = new Dictionary<string, string> { ["en"] = name }, isPrimary = true } },
        });
        return await Id(res);
    }

    public async Task<Guid> Theater(string code)
    {
        var res = await W.PostAsJsonAsync("/api/v1/theaters", new
        {
            code = $"{code}-{Tag}",
            name = new Dictionary<string, string> { ["zh-Hant"] = "西歐", ["en"] = "Western Europe" },
        });
        return await Id(res);
    }

    public string TheaterCode(string code) => $"{code}-{Tag}";

    public async Task<Guid> Snapshot(Guid theaterId, string asOf, string? attestedStart = null, string? attestedEnd = null)
    {
        object body = attestedStart is null
            ? new { theaterId, asOf, title = new Dictionary<string, string> { ["en"] = $"Snapshot {asOf}" } }
            : new { theaterId, asOf, attestation = "interval", attestedPeriod = new { start = attestedStart, end = attestedEnd } };
        return await Id(await W.PostAsJsonAsync("/api/v1/control-snapshots", body));
    }

    public static JsonObject ControlBody(Guid controller, Guid snapshot, Guid source, string start, string end,
        JsonObject? geometry = null, string controlType = "military_occupation", bool disputed = false, string locator = "WWII Europe Map 15") => new()
    {
        ["controllerRegimeId"] = controller.ToString(),
        ["snapshotId"] = snapshot.ToString(),
        ["controlType"] = controlType,
        ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
        ["geometry"] = geometry ?? Square(0, 45, 2),
        ["isDisputed"] = disputed,
        ["citations"] = new JsonArray(new JsonObject
        {
            ["sourceId"] = source.ToString(), ["locator"] = locator, ["role"] = "primary", ["evidenceNote"] = "圖上明示佔領區界線",
        }),
    };

    public Task<HttpResponseMessage> PostControl(JsonObject body) =>
        W.PostAsync("/api/v1/control-records", new StringContent(body.ToJsonString(), System.Text.Encoding.UTF8, "application/json"));
}
