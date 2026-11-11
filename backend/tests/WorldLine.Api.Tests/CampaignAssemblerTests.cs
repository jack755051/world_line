using System.Text.Json;
using System.Text.Json.Nodes;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using NpgsqlTypes;
using WorldLine.Api.Domain;
using WorldLine.Api.Features;

namespace WorldLine.Api.Tests;

/// <summary>
/// 戰役 C1 唯讀 API 的組裝邏輯（ARCHITECTURE §19.1.3、§19.5 C1）。純單元測試：不需要資料庫、不啟動容器。
/// 以 data/seed/battles/dunkirk_1940.seed.json 建列，比對輸出與前端靜態檔 wl-campaign-web/0.1 的結構相容。
/// </summary>
public sealed class CampaignAssemblerTests
{
    private static readonly JsonSerializerOptions GeoJson = CreateGeoJson();

    private static JsonSerializerOptions CreateGeoJson()
    {
        var o = new JsonSerializerOptions();
        o.Converters.Add(new GeoJsonConverterFactory(new GeometryFactory(new PrecisionModel(), 4326)));
        return o;
    }

    private static string RepoRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "ARCHITECTURE.md"))) dir = dir.Parent;
        return dir?.FullName ?? throw new InvalidOperationException("找不到 repo 根目錄");
    }

    private static JsonNode Load(params string[] rel) => JsonNode.Parse(File.ReadAllText(Path.Combine([RepoRoot(), .. rel])))!;

    private static DateOnly Day(JsonNode? n) => DateOnly.Parse(n!.GetValue<string>());

    private sealed record Rows(
        BattleProfile Profile, HistoricalEvent Event, List<BattlePhase> Phases, List<BattleMapFeature> Features,
        List<CampaignAssembler.Cite> PhaseCites, List<CampaignAssembler.Cite> FeatureCites);

    /// <summary>把 seed 轉成實體列（模擬寫庫後的樣子；不碰 DB）。</summary>
    private static Rows FromSeed()
    {
        var seed = Load("data", "seed", "battles", "dunkirk_1940.seed.json");
        var sources = seed["sources"]!.AsArray().ToDictionary(s => s!["key"]!.GetValue<string>());
        var t0 = new DateTimeOffset(2026, 11, 11, 0, 0, 0, TimeSpan.Zero);
        var n = 0;
        List<CampaignAssembler.Cite> Cites(Guid owner, JsonNode? arr) => arr!.AsArray().Select(c =>
        {
            var s = sources[c!["source_key"]!.GetValue<string>()]!;
            return new CampaignAssembler.Cite(owner, Guid.NewGuid(), t0.AddSeconds(n++),
                s["source_kind"]!.GetValue<string>(), s["title"]!.GetValue<string>(), s["url"]?.GetValue<string>(),
                c["quote"]!.GetValue<string>());
        }).ToList();

        var ev = seed["event"]!;
        var eventId = Guid.Parse(ev["id"]!.GetValue<string>());
        var e = new HistoricalEvent
        {
            Id = eventId, EventKind = "battle",
            Occurred = new NpgsqlRange<DateOnly>(Day(ev["occurred"]!["start"]), true, Day(ev["occurred"]!["end"]), false),
        };
        var pr = seed["profile"]!;
        var profile = new BattleProfile
        {
            EventId = eventId, Slug = pr["slug"]!.GetValue<string>(), Name = pr["name"]!.ToJsonString(),
            TheaterArea = (MultiPolygon?)JsonSerializer.Deserialize<Geometry>(pr["theater_area"]!.ToJsonString(), GeoJson),
            Status = pr["status"]!.GetValue<string>(),
        };
        var phaseCites = new List<CampaignAssembler.Cite>();
        var phases = seed["phases"]!.AsArray().Select(p =>
        {
            var id = Guid.Parse(p!["id"]!.GetValue<string>());
            phaseCites.AddRange(Cites(id, p["citations"]));
            return new BattlePhase
            {
                Id = id, EventId = eventId, Seq = p["seq"]!.GetValue<int>(), Name = p["name"]!.ToJsonString(),
                Period = new NpgsqlRange<DateOnly>(Day(p["period"]!["start"]), true, Day(p["period"]!["end"]), false),
                StartPrecision = p["start_precision"]!.GetValue<string>(), EndPrecision = p["end_precision"]!.GetValue<string>(),
                Summary = p["summary"]?.ToJsonString(), Status = p["status"]!.GetValue<string>(),
            };
        }).ToList();
        var featureCites = new List<CampaignAssembler.Cite>();
        var features = seed["features"]!.AsArray().Select(f =>
        {
            var id = Guid.Parse(f!["id"]!.GetValue<string>());
            featureCites.AddRange(Cites(id, f["citations"]));
            return new BattleMapFeature
            {
                Id = id, PhaseId = Guid.Parse(f["phase_id"]!.GetValue<string>()),
                FeatureKey = f["feature_key"]!.GetValue<string>(), FeatureKind = f["feature_kind"]!.GetValue<string>(),
                SideCamp = f["side_camp"]?.GetValue<string>(),
                Geom = JsonSerializer.Deserialize<Geometry>(f["geom"]!.ToJsonString(), GeoJson)!,
                Props = f["props"]?.ToJsonString(), GeomBasis = f["geom_basis"]!.GetValue<string>(),
                Status = f["status"]!.GetValue<string>(),
            };
        }).ToList();
        return new Rows(profile, e, phases, features, phaseCites, featureCites);
    }

    private static JsonObject Build(Rows r, IEnumerable<CampaignAssembler.Belligerent>? b = null) =>
        CampaignAssembler.Build(r.Profile, r.Event, r.Phases, r.Features, r.PhaseCites, r.FeatureCites, b ?? []);

    [Fact]
    public void Dunkirk_seed_output_matches_static_json_structure()
    {
        var web = Load("frontend", "public", "campaigns", "dunkirk_1940.json");
        var api = Build(FromSeed());

        Assert.Equal("wl-campaign-web/0.1", api["schema"]!.GetValue<string>());
        foreach (var k in new[] { "key", "name_zh", "name_en", "start", "end", "end_inclusive" })
            Assert.Equal(web[k]!.GetValue<string>(), api[k]!.GetValue<string>());

        var wp = web["phases"]!.AsArray();
        var ap = api["phases"]!.AsArray();
        Assert.Equal(wp.Count, ap.Count);
        for (var i = 0; i < wp.Count; i++)
            foreach (var k in new[] { "key", "name_zh", "start", "end", "summary_zh" })
                Assert.Equal(wp[i]![k]!.GetValue<string>(), ap[i]![k]!.GetValue<string>());

        foreach (var layer in new[] { "fronts", "arrows", "sites" })
        {
            var wf = web["layers"]![layer]!["features"]!.AsArray();
            var af = api["layers"]![layer]!["features"]!.AsArray();
            Assert.Equal("FeatureCollection", api["layers"]![layer]!["type"]!.GetValue<string>());
            Assert.Equal(
                wf.Select(f => f!["properties"]!["id"]!.GetValue<string>()).Order(StringComparer.Ordinal),
                af.Select(f => f!["properties"]!["id"]!.GetValue<string>()));
            var wById = wf.ToDictionary(f => f!["properties"]!["id"]!.GetValue<string>());
            foreach (var f in af)
            {
                var w = wById[f!["properties"]!["id"]!.GetValue<string>()]!;
                Assert.True(JsonNode.DeepEquals(w["geometry"]!["coordinates"], f["geometry"]!["coordinates"]));
                Assert.Equal(w["properties"]!["phase"]!.GetValue<int>(), f["properties"]!["phase"]!.GetValue<int>());
                Assert.Equal(w["properties"]!["group"]!.GetValue<string>(), f["properties"]!["group"]!.GetValue<string>());
            }
        }
    }

    [Fact]
    public void Pending_rows_are_never_reported_as_verified()
    {
        var api = Build(FromSeed());
        Assert.Equal("pending", api["status"]!.GetValue<string>());
        Assert.False(api["end_verified"]!.GetValue<bool>());
        Assert.All(api["phases"]!.AsArray(), p => Assert.False(p!["dates_verified"]!.GetValue<bool>()));
        foreach (var layer in new[] { "fronts", "arrows", "sites" })
            Assert.All(api["layers"]![layer]!["features"]!.AsArray(), f => Assert.False(f!["properties"]!["verified"]!.GetValue<bool>()));
        Assert.Null(api["totals"]);
    }

    [Fact]
    public void Verified_status_is_reflected()
    {
        var r = FromSeed();
        r.Phases[0].Status = BattleStatuses.Verified;
        r.Features[0].Status = BattleStatuses.Verified;
        var api = Build(r);
        Assert.True(api["phases"]![0]!["dates_verified"]!.GetValue<bool>());
        var key = r.Features[0].FeatureKey;
        var f = api["layers"]!["fronts"]!["features"]!.AsArray().Single(x => x!["properties"]!["id"]!.GetValue<string>() == key);
        Assert.True(f!["properties"]!["verified"]!.GetValue<bool>());
    }

    [Fact]
    public void Retracted_rows_and_citations_are_excluded()
    {
        var r = FromSeed();
        var now = DateTimeOffset.UnixEpoch;
        var retractedPhase = r.Phases.Single(p => p.Seq == 5);
        retractedPhase.RetractedAt = now;
        retractedPhase.RetractionReason = "test";
        var feature = r.Features.First(f => f.PhaseId != retractedPhase.Id);
        feature.RetractedAt = now;
        feature.RetractionReason = "test";
        // citation 的撤回在查詢端過濾（retracted_at IS NULL）；組裝端只拿得到未撤回的。這裡驗證撤回階段的 citation 不外漏。
        var api = Build(r);

        Assert.Equal(4, api["phases"]!.AsArray().Count);
        Assert.DoesNotContain(api["phases"]!.AsArray(), p => p!["seq"]!.GetValue<int>() == 5);
        var ids = new[] { "fronts", "arrows", "sites" }
            .SelectMany(l => api["layers"]![l]!["features"]!.AsArray())
            .Select(f => f!["properties"]!["id"]!.GetValue<string>()).ToList();
        Assert.DoesNotContain(feature.FeatureKey, ids);
        Assert.DoesNotContain(ids, id => id.StartsWith("dunkirk_1940_p5-", StringComparison.Ordinal));
        var p5Quotes = r.PhaseCites.Where(c => c.OwnerId == retractedPhase.Id).Select(c => c.Quote).ToHashSet();
        var otherQuotes = r.PhaseCites.Where(c => c.OwnerId != retractedPhase.Id).Select(c => c.Quote)
            .Concat(r.FeatureCites.Select(c => c.Quote)).ToHashSet();
        Assert.DoesNotContain(api["citations"]!.AsArray(),
            c => p5Quotes.Contains(c!["quote"]!.GetValue<string>()) && !otherQuotes.Contains(c["quote"]!.GetValue<string>()));
    }

    [Fact]
    public void Belligerents_grouped_by_alignment_camp()
    {
        var api = Build(FromSeed(),
        [
            new("united-kingdom", "英國", Camps.Allies),
            new("deutsches-reich", "德國", Camps.Axis),
            new("kingdom-of-belgium", "比利時", null),
        ]);
        Assert.Equal(["英國"], api["belligerents"]!["allied"]!.AsArray().Select(x => x!.GetValue<string>()));
        Assert.Equal(["德國"], api["belligerents"]!["axis"]!.AsArray().Select(x => x!.GetValue<string>()));
        Assert.Equal(["比利時"], api["belligerents"]!["unknown"]!.AsArray().Select(x => x!.GetValue<string>()));
        Assert.Equal(["deutsches-reich", "kingdom-of-belgium", "united-kingdom"],
            api["regime_slugs"]!.AsArray().Select(x => x!.GetValue<string>()));
    }

    [Fact]
    public void Bounds_fall_back_to_feature_extent()
    {
        var r = FromSeed();
        var withArea = Build(r)["bounds"]!;
        var web = Load("frontend", "public", "campaigns", "dunkirk_1940.json");
        Assert.True(JsonNode.DeepEquals(web["bounds"], withArea));

        r.Profile.TheaterArea = null;
        var b = Build(r)["bounds"]!.AsArray();
        Assert.Equal(2, b.Count);
        Assert.True(b[0]![0]!.GetValue<double>() < b[1]![0]!.GetValue<double>());
    }
}
