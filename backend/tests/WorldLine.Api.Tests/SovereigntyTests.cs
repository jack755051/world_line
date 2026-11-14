using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 主權圖層（法理國界，sovereignty_records；2026-10-31 試驗 feature/borders-1938-1940，AI 提案・待拍板）：
/// 與控制區分開；依政權回傳（前端依政權上色），陣營只作補充；起訖事件沒有引用即「待查證」；幾何授權與 OHM 版本釘選。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SovereigntyTests(PostGisFixture fx)
{
    private static JsonObject Body(Guid regime, Guid source, string start, string? end, JsonObject? geometry = null,
        string license = "cc0", string? attribution = null, Guid? startEvent = null, Guid? endEvent = null,
        string status = "de_jure", long? relation = 2704712, int? version = 208)
    {
        var b = new JsonObject
        {
            ["regimeId"] = regime.ToString(),
            ["geometry"] = geometry ?? ApiTestKit.Square(10, 48, 2),
            ["validPeriod"] = new JsonObject { ["start"] = start, ["end"] = end },
            ["layerStatus"] = status,
            ["geometrySourceId"] = source.ToString(),
            ["geometryLocator"] = relation is null ? "n/a" : $"relation/{relation} v{version}",
            ["geometryLicense"] = license,
            ["attribution"] = attribution,
            ["startEventId"] = startEvent?.ToString(),
            ["endEventId"] = endEvent?.ToString(),
            ["provenance"] = new JsonObject { ["memberWayLicenses"] = new JsonObject { ["CC-BY 4.0"] = 25 } },
        };
        if (relation is not null)
        {
            b["ohmRelationId"] = relation;
            b["ohmVersion"] = version;
            b["ohmFetchedAt"] = "2026-10-30T19:22:26Z";
        }
        return b;
    }

    private static Task<HttpResponseMessage> Post(ApiTestKit k, JsonObject body) =>
        k.W.PostAsync("/api/v1/sovereignty-records", new StringContent(body.ToJsonString(), System.Text.Encoding.UTF8, "application/json"));

    private static async Task<Guid> Event(ApiTestKit k, string start, params object[] citations)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "treaty",
            occurred = new { start, end = DateOnly.Parse(start).AddDays(1).ToString("yyyy-MM-dd") },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = "疆界變動", ["en"] = "Border change" },
            citations,
        });
        return await k.Id(res);
    }

    private static async Task<JsonElement?> FeatureOn(ApiTestKit k, string date, Guid record)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(date, data.GetProperty("date").GetString());
        foreach (var f in data.GetProperty("featureCollection").GetProperty("features").EnumerateArray())
            if (f.GetProperty("properties").GetProperty("recordId").GetGuid() == record) return f;
        return null;
    }

    [Fact]
    public async Task Record_is_returned_only_inside_its_half_open_period_with_regime_slug_and_pinned_provenance()
    {
        var k = new ApiTestKit(fx);
        var reich = await k.Regime("reich");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var id = await k.Id(await Post(k, Body(reich, ohm, "1938-03-13", "1938-11-21")));

        Assert.Null(await FeatureOn(k, "1938-03-12", id));
        Assert.Null(await FeatureOn(k, "1938-11-21", id)); // 半開區間
        var f = (await FeatureOn(k, "1938-10-15", id))!.Value;
        var p = f.GetProperty("properties");
        Assert.Equal($"reich-{k.Tag}", p.GetProperty("regimeSlug").GetString());
        Assert.Equal("de_jure", p.GetProperty("layerStatus").GetString());
        var g = p.GetProperty("geometry");
        Assert.Equal(2704712, g.GetProperty("ohmRelationId").GetInt64());
        Assert.Equal(208, g.GetProperty("ohmVersion").GetInt32());
        Assert.Equal("cc0", g.GetProperty("geometryLicense").GetString());
        Assert.Equal(25, g.GetProperty("flags").GetProperty("memberWayLicenses").GetProperty("CC-BY 4.0").GetInt32());
        Assert.Equal("MultiPolygon", f.GetProperty("geometry").GetProperty("type").GetString());
        Assert.Equal(JsonValueKind.Null, p.GetProperty("startEvent").ValueKind);
    }

    [Fact] // 「待查證」：事件沒有合格引用 → pending；有引用 → verified
    public async Task Events_without_citations_are_pending_verification()
    {
        var k = new ApiTestKit(fx);
        var hu = await k.Regime("hungary");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var dgfp = await k.Source(kind: "official_record", license: "us_federal_pd", title: "DGFP D IV");
        var award = await Event(k, "1938-11-02", new { sourceId = dgfp, locator = "Doc. 99, pp. 118–126", evidenceNote = "仲裁文本" });
        var unsourced = await Event(k, "1939-03-14");
        var id = await k.Id(await Post(k, Body(hu, ohm, "1938-11-02", "1939-03-14", startEvent: award, endEvent: unsourced)));

        var p = (await FeatureOn(k, "1938-12-01", id))!.Value.GetProperty("properties");
        Assert.Equal("verified", p.GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal("Doc. 99, pp. 118–126", p.GetProperty("startEvent").GetProperty("citations")[0].GetProperty("locator").GetString());
        Assert.Equal("pending", p.GetProperty("endEvent").GetProperty("verification").GetString());
        Assert.Equal(0, p.GetProperty("endEvent").GetProperty("citations").GetArrayLength());
    }

    [Fact] // 可信程度門檻（docs/source-rules.md §5）：未評等或單一 B → pending；一筆 A，或兩個獨立家族的 B → verified；同一家族的兩個 B 只算一個
    public async Task Event_verification_follows_source_grade_and_independent_families()
    {
        var k = new ApiTestKit(fx);
        var hu = await k.Regime("hungary-grades");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var ungraded = await k.Source(kind: "official_record", title: "ungraded", grade: "");
        var b1 = await k.Source(kind: "peer_reviewed", title: "b1", grade: "B", family: "fam-1");
        var b1b = await k.Source(kind: "peer_reviewed", title: "b1b", grade: "B", family: "fam-1");
        var b2 = await k.Source(kind: "peer_reviewed", title: "b2", grade: "B", family: "fam-2");
        var a = await k.Source(kind: "official_record", title: "a", grade: "A");
        object C(Guid s) => new { sourceId = s, locator = "p. 1", evidenceNote = "n" };
        async Task<string?> V(string from, string to, params object[] cites)
        {
            var ev = await Event(k, from, cites);
            var id = await k.Id(await Post(k, Body(hu, ohm, from, to, startEvent: ev)));
            return (await FeatureOn(k, from, id))!.Value.GetProperty("properties").GetProperty("startEvent").GetProperty("verification").GetString();
        }
        Assert.Equal("pending", await V("1921-01-01", "1921-02-01", C(ungraded)));
        Assert.Equal("pending", await V("1921-02-01", "1921-03-01", C(b1)));
        Assert.Equal("pending", await V("1921-03-01", "1921-04-01", C(b1), C(b1b)));
        Assert.Equal("verified", await V("1921-04-01", "1921-05-01", C(b1), C(b2)));
        Assert.Equal("verified", await V("1921-05-01", "1921-06-01", C(a)));

        // 等級記在每筆引文上：整冊未評等（或是 B），但被引用的那一份文件評為 A → verified；引文等級優先於整冊等級
        object CG(Guid s, string g) => new { sourceId = s, locator = "Doc. 7", evidenceNote = "n", grade = g, gradeBasis = "當事國自己的照會" };
        Assert.Equal("verified", await V("1921-08-01", "1921-09-01", CG(ungraded, "A")));
        Assert.Equal("verified", await V("1921-09-01", "1921-10-01", CG(b1, "A")));
        Assert.Equal("pending", await V("1921-10-01", "1921-11-01", CG(a, "B")));

        // 國界本身的可信程度：只有資料集、沒有起始事件 → needs_check／dataset_only；起始事件已查證 → verified
        var bare = await k.Id(await Post(k, Body(hu, ohm, "1921-06-01", "1921-07-01")));
        var bp = (await FeatureOn(k, "1921-06-01", bare))!.Value.GetProperty("properties");
        Assert.Equal("needs_check", bp.GetProperty("confidence").GetString());
        Assert.Equal("dataset_only", bp.GetProperty("confidenceBasis").GetString());
        // 來歷（sovereignty_record_links）：接續前一筆、形狀相同的紀錄沿用前一筆的可信程度；baseline 另有自己的原因
        var first = await k.Id(await Post(k, Body(hu, ohm, "1922-01-01", "1922-06-01", startEvent: await Event(k, "1922-01-01", C(a)))));
        var second = await k.Id(await Post(k, Body(hu, ohm, "1922-06-01", "1922-09-01")));
        var third = await k.Id(await Post(k, Body(hu, ohm, "1922-09-01", "1923-01-01")));
        await using (var c = new NpgsqlConnection(fx.ConnectionString))
        {
            await c.OpenAsync();
            await using var cmd = new NpgsqlCommand($"INSERT INTO sovereignty_record_links (record_id, kind, continues_record_id) VALUES ('{second}', 'continuation', '{first}'), ('{third}', 'continuation', '{second}'), ('{bare}', 'baseline', NULL)", c);
            await cmd.ExecuteNonQueryAsync();
        }
        var p3 = (await FeatureOn(k, "1922-10-01", third))!.Value.GetProperty("properties");
        Assert.Equal("verified", p3.GetProperty("confidence").GetString());
        Assert.Equal("start_event_one_a", p3.GetProperty("confidenceBasis").GetString());
        Assert.Equal("baseline", (await FeatureOn(k, "1921-06-01", bare))!.Value.GetProperty("properties").GetProperty("confidenceBasis").GetString());

        // 國界本身的引文：期初既有的紀錄沒有事件可補，附一筆 A 級的地圖集圖版 → verified；資料集不能當出處
        var atlas = await k.Source(kind: "atlas_map", title: "Atlas 1907", grade: "A");
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{bare}/citations",
            new { sourceId = ohm, locator = "x", evidenceNote = "n", grade = "A", gradeBasis = "b" }), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{bare}/citations",
            new { sourceId = atlas, locator = "Plate 12", evidenceNote = "圖版所繪疆界與此紀錄相符", grade = "A", gradeBasis = "當時出版的地圖集" }), HttpStatusCode.Created);
        var bc = (await FeatureOn(k, "1921-06-15", bare))!.Value.GetProperty("properties");
        Assert.Equal("verified", bc.GetProperty("confidence").GetString());
        Assert.Equal("record_citation_one_a", bc.GetProperty("confidenceBasis").GetString());
        Assert.Equal("Plate 12", bc.GetProperty("recordCitations")[0].GetProperty("locator").GetString());

        var evA = await Event(k, "1921-07-01", C(a));
        var good = await k.Id(await Post(k, Body(hu, ohm, "1921-07-01", "1921-08-01", startEvent: evA)));
        Assert.Equal("verified", (await FeatureOn(k, "1921-07-01", good))!.Value.GetProperty("properties").GetProperty("confidence").GetString());
    }

    [Fact] // 政權優先於陣營：陣營只作補充（有切片才帶），不影響回傳的要素
    public async Task Camp_is_only_a_supplement()
    {
        var k = new ApiTestKit(fx);
        var it = await k.Regime("italy");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var id = await k.Id(await Post(k, Body(it, ohm, "1929-06-07", "1940-06-24")));
        Assert.Equal(JsonValueKind.Null, (await FeatureOn(k, "1939-01-01", id))!.Value.GetProperty("properties").GetProperty("regimeAlignment").ValueKind);

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{it}/alignments", new
        {
            camp = "axis", validPeriod = new { start = "1939-05-22" },
            citations = new[] { new { sourceId = frus, locator = "p. 1", role = "primary", evidenceNote = "鋼鐵條約" } },
        }), HttpStatusCode.Created);
        var p = (await FeatureOn(k, "1939-10-15", id))!.Value.GetProperty("properties");
        Assert.Equal("axis", p.GetProperty("regimeAlignment").GetProperty("camp").GetString());
        Assert.Equal($"italy-{k.Tag}", p.GetProperty("regimeSlug").GetString());
    }

    [Fact]
    public async Task Same_regime_periods_cannot_overlap_and_retraction_allows_reentry()
    {
        var k = new ApiTestKit(fx);
        var pl = await k.Regime("poland");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var a = await k.Id(await Post(k, Body(pl, ohm, "1924-06-22", "1938-11-01")));
        await ApiTestKit.Expect(await Post(k, Body(pl, ohm, "1938-10-01", "1939-10-06")), HttpStatusCode.Conflict, "CONFLICTING_OFFICIAL_VERSION");
        await k.Id(await Post(k, Body(pl, ohm, "1938-11-01", "1939-10-06"))); // 相接不重疊

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{a}/retraction", new { reason = "幾何換版" }), HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{a}/retraction", new { reason = "again" }), HttpStatusCode.Conflict);
        Assert.Null(await FeatureOn(k, "1938-01-01", a));
        await k.Id(await Post(k, Body(pl, ohm, "1924-06-22", "1938-11-01", version: 215)));
    }

    [Fact] // 效能快取（DateIntervalCache）：同一區間的結果會快取，但任何寫入都讓快取作廢，不會讀到舊資料
    public async Task Cached_dates_see_new_and_retracted_records_immediately()
    {
        var k = new ApiTestKit(fx);
        var hu = await k.Regime("hungary");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var first = await k.Id(await Post(k, Body(hu, ohm, "1920-06-04", "1938-11-02")));
        Assert.NotNull(await FeatureOn(k, "1930-01-01", first)); // 先讀，讓區間進快取
        var second = await k.Id(await Post(k, Body(hu, ohm, "1938-11-02", "1939-03-15")));
        Assert.NotNull(await FeatureOn(k, "1939-01-01", second));
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/sovereignty-records/{first}/retraction", new { reason = "測試快取作廢" }), HttpStatusCode.OK);
        Assert.Null(await FeatureOn(k, "1930-01-01", first));
        // 變動點（前端用來判斷換日期要不要重新載入）含這兩筆紀錄的起訖日
        var cp = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/timeline/change-points"), HttpStatusCode.OK)).GetProperty("data");
        var pts = cp.GetProperty("points").EnumerateArray().Select(x => x.GetString()).ToList();
        Assert.Contains("1938-11-02", pts);
        Assert.Contains("1939-03-15", pts);
        Assert.Equal(pts.OrderBy(x => x, StringComparer.Ordinal).ToList(), pts);
    }

    [Fact] // 回應壓縮：要求 gzip 時回傳壓縮內容
    public async Task Sovereignty_response_is_compressed_when_asked()
    {
        var k = new ApiTestKit(fx);
        var req = new HttpRequestMessage(HttpMethod.Get, "/api/v1/sovereignty?date=1939-01-01");
        req.Headers.AcceptEncoding.ParseAdd("gzip");
        var res = await k.R.SendAsync(req);
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        Assert.Contains("gzip", res.Content.Headers.ContentEncoding);
    }

    [Fact] // 授權：幾何來源授權須在允許清單；cc_by 必須署名；OHM 關係必須釘版本
    public async Task Licence_and_pinning_rules()
    {
        var k = new ApiTestKit(fx);
        var es = await k.Regime("spain");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var nc = await k.Source(kind: "dataset", license: null, title: "CShapes (CC BY-NC-SA)");
        await ApiTestKit.Expect(await Post(k, Body(es, nc, "1939-04-01", "1956-04-07")), HttpStatusCode.BadRequest, "SOURCE_NOT_QUALIFIED");
        await ApiTestKit.Expect(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by")), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        await ApiTestKit.Expect(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by_nc")), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        var noVersion = Body(es, ohm, "1939-04-01", "1956-04-07");
        noVersion.Remove("ohmVersion");
        await ApiTestKit.Expect(await Post(k, noVersion), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        await k.Id(await Post(k, Body(es, ohm, "1939-04-01", "1956-04-07", license: "cc_by", attribution: "© Instituto Geográfico Nacional (CNIG), CC BY 4.0")));
    }

    [Fact]
    public async Task Date_is_required_and_start_must_be_bounded()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/sovereignty"), HttpStatusCode.BadRequest, "VALIDATION_FAILED");
        var ch = await k.Regime("swiss");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        await ApiTestKit.Expect(await Post(k, Body(ch, ohm, null!, "1967-10-03")), HttpStatusCode.BadRequest, "PERIOD_REQUIRED");
        await k.Id(await Post(k, Body(ch, ohm, "1874-09-23", null))); // 迄日未知可無界
    }

    [Fact] // I5：不可刪除；只允許一次寫入撤回，其他欄位不可改
    public async Task I5_guards_on_sovereignty_records()
    {
        var k = new ApiTestKit(fx);
        var dk = await k.Regime("denmark");
        var ohm = await k.Source(kind: "dataset", license: "cc0", title: "OpenHistoricalMap");
        var id = await k.Id(await Post(k, Body(dk, ohm, "1932-01-30", "1944-06-17")));
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        async Task Exec(string sql) { await using var cmd = new NpgsqlCommand(sql, c); await cmd.ExecuteNonQueryAsync(); }
        var ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"DELETE FROM sovereignty_records WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec($"UPDATE sovereignty_records SET geometry_locator = 'x' WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.RestrictViolation, ex.SqlState);
        ex = await Assert.ThrowsAsync<PostgresException>(() => Exec(
            $"INSERT INTO sovereignty_records (regime_id, geom, valid_period, layer_status, geometry_source_id, geometry_locator, geometry_license) " +
            $"SELECT regime_id, geom, daterange('1940-01-01','1941-01-01'), layer_status, geometry_source_id, 'y', geometry_license FROM sovereignty_records WHERE id = '{id}'"));
        Assert.Equal(PostgresErrorCodes.ExclusionViolation, ex.SqlState);
    }
}
