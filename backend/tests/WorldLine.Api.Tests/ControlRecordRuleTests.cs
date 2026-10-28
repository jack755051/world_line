using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;
using WorldLine.Contracts;

namespace WorldLine.Api.Tests;

/// <summary>POST /control-records 的業務規則（I1、I3、I6、R7）與寫入授權。</summary>
[Collection(PostGisCollection.Name)]
public sealed class ControlRecordRuleTests(PostGisFixture fx)
{
    private async Task<(ApiTestKit k, Guid regime, Guid snapshot, Guid source)> SetupAsync()
    {
        var k = new ApiTestKit(fx);
        var regime = await k.Regime("deutsches-reich");
        var theater = await k.Theater("west-europe");
        var snapshot = await k.Snapshot(theater, "1940-07-15");
        var source = await k.Source();
        return (k, regime, snapshot, source);
    }

    [Fact] // PRD §10 M0 驗收：integration test 驗 I6 拒絕無引用
    public async Task I6_rejects_control_record_without_citation()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var body = ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11");
        body["citations"] = new JsonArray();
        await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.BadRequest, ErrorCodes.CitationRequired);

        body.Remove("citations");
        await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.BadRequest, ErrorCodes.CitationRequired);
    }

    [Fact]
    public async Task I6_rejects_when_only_auxiliary_citations()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var body = ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11");
        body["citations"]![0]!["role"] = "auxiliary_geometry";
        await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.BadRequest, ErrorCodes.CitationRequired);
    }

    [Theory]
    [InlineData(null, "1942-11-11")]
    [InlineData("1940-06-25", null)]
    [InlineData("1942-11-11", "1940-06-25")]
    [InlineData("1940-06-25", "1940-06-25")]
    public async Task I1_requires_bounded_ordered_period(string? start, string? end)
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var body = ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11");
        body["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end };
        await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.BadRequest, ErrorCodes.PeriodRequired);
    }

    [Fact]
    public async Task R7_primary_citation_must_be_map_with_allowed_license_and_locator()
    {
        var (k, regime, snapshot, _) = await SetupAsync();

        var treaty = await k.Source(kind: "treaty", title: "Franco-German Armistice");
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, treaty, "1940-06-25", "1942-11-11")),
            HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);

        var unlicensed = await k.Source(license: null, title: "Unknown-licence map");
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, unlicensed, "1940-06-25", "1942-11-11")),
            HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);

        var ok = await k.Source();
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, ok, "1940-06-25", "1942-11-11", locator: "  ")),
            HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);
    }

    [Fact]
    public async Task R7_auxiliary_dataset_citation_is_allowed_next_to_qualified_primary()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var ain = await k.Source(kind: "dataset", license: "licence_ouverte_2", title: "Ligne de démarcation (Ain)");
        var body = ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11");
        ((JsonArray)body["citations"]!).Add(new JsonObject
        {
            ["sourceId"] = ain.ToString(), ["locator"] = "couche ligne_demarcation", ["role"] = "auxiliary_geometry", ["evidenceNote"] = "界線細部幾何",
        });
        await ApiTestKit.Expect(await k.PostControl(body), HttpStatusCode.Created);
    }

    [Fact]
    public async Task R7_self_made_or_missing_publisher_source_is_rejected()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.PostSource(publisher: "自製"), HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);
        await ApiTestKit.Expect(await k.PostSource(publisher: "Own work"), HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);
        await ApiTestKit.Expect(await k.PostSource(publisher: " "), HttpStatusCode.BadRequest, ErrorCodes.SourceNotQualified);
    }

    [Fact]
    public async Task I3_rejects_overlapping_official_versions_of_same_controller()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11",
            ApiTestKit.Square(10, 10, 2))), HttpStatusCode.Created);

        // 時間與幾何都重疊 → 409
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1941-01-01", "1941-06-01",
            ApiTestKit.Square(11, 11, 2))), HttpStatusCode.Conflict, ErrorCodes.ConflictingOfficialVersion);

        // 明確標記爭議並存 → 允許
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1941-01-01", "1941-06-01",
            ApiTestKit.Square(11, 11, 2), disputed: true)), HttpStatusCode.Created);

        // 只有邊界相接（面積 0）→ 允許
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1941-01-01", "1941-06-01",
            ApiTestKit.Square(12, 10, 2))), HttpStatusCode.Created);

        // 幾何重疊但時間不重疊（半開區間：1942-11-11 起即不重疊）→ 允許
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1942-11-11", "1944-08-25",
            ApiTestKit.Square(10, 10, 2))), HttpStatusCode.Created);
    }

    [Fact]
    public async Task I3_does_not_apply_across_different_controllers()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var italy = await k.Regime("regno-d-italia");
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11",
            ApiTestKit.Square(20, 20, 2))), HttpStatusCode.Created);
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(italy, snapshot, source, "1940-06-25", "1942-11-11",
            ApiTestKit.Square(21, 21, 2))), HttpStatusCode.Created);
    }

    [Fact]
    public async Task Invalid_geometry_and_unknown_control_type_are_rejected()
    {
        var (k, regime, snapshot, source) = await SetupAsync();
        var bowtie = new JsonObject
        {
            ["type"] = "Polygon",
            ["coordinates"] = new JsonArray(new JsonArray(new JsonArray(0, 0), new JsonArray(1, 1), new JsonArray(1, 0), new JsonArray(0, 1), new JsonArray(0, 0))),
        };
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11", bowtie)),
            HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
        // R9：「控制資料缺」不是控制類型
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(regime, snapshot, source, "1940-06-25", "1942-11-11", controlType: "no_data")),
            HttpStatusCode.BadRequest, ErrorCodes.ValidationFailed);
    }

    [Fact]
    public async Task Writes_require_api_key_reads_do_not()
    {
        var k = new ApiTestKit(fx);
        var anon = fx.Reader();
        await ApiTestKit.Expect(await anon.PostAsJsonAsync("/api/v1/sources", new { sourceKind = "map", title = "t", publisher = "p" }),
            HttpStatusCode.Unauthorized, ErrorCodes.Unauthorized);

        var wrong = fx.Reader();
        wrong.DefaultRequestHeaders.Add("X-API-Key", "wrong-key");
        await ApiTestKit.Expect(await wrong.PostAsJsonAsync("/api/v1/control-records", new { }), HttpStatusCode.Unauthorized, ErrorCodes.Unauthorized);

        await ApiTestKit.Expect(await anon.GetAsync("/api/v1/control?date=1940-07-15"), HttpStatusCode.OK);
    }
}
