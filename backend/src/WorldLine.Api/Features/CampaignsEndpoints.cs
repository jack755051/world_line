using System.Globalization;
using System.Text.Json;
using System.Text.Json.Nodes;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using NpgsqlTypes;
using WorldLine.Api.Common;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Features;

/// <summary>
/// 戰役 C1 唯讀 API（ARCHITECTURE §19.1.3、§19.5 C1，2026-11-11）：<c>GET /api/v1/campaigns/{slug}</c>。
/// - data 與前端靜態檔 <c>wl-campaign-web/0.1</c> 相容（layers 分 fronts／arrows／sites 三個 FeatureCollection），外層照 PRD §7 統一格式。
/// - 只回 retracted_at IS NULL 的列（profile、事件、階段、圖形、citation、參與方都一樣）。
/// - verified 一律由 status='verified' 決定；C1 seed 全部 pending，因此目前都回 false（前端顯示待考證）。
/// - totals 屬 battle_figures（C3），目前回 null；fronts_note／notes 屬 event_gaps（C3），目前回 null／空陣列。
/// </summary>
public static class CampaignsEndpoints
{
    public static void Map(RouteGroupBuilder read)
    {
        read.MapGet("/campaigns/{slug}", Get).WithTags("Campaigns").WithName("GetCampaign")
            .Ok<JsonObject>().Errors(404);
    }

    public static async Task<IResult> Get(string slug, WorldLineDbContext db, CancellationToken ct)
    {
        var profile = await db.BattleProfiles.AsNoTracking()
            .FirstOrDefaultAsync(x => x.Slug == slug && x.RetractedAt == null, ct)
            ?? throw ApiError.NotFound("戰役");
        var ev = await db.HistoricalEvents.AsNoTracking()
            .FirstOrDefaultAsync(x => x.Id == profile.EventId && x.RetractedAt == null, ct)
            ?? throw ApiError.NotFound("戰役");

        var phases = await db.BattlePhases.AsNoTracking()
            .Where(x => x.EventId == ev.Id && x.RetractedAt == null).ToListAsync(ct);
        var phaseIds = phases.Select(p => p.Id).ToList();
        var features = await db.BattleMapFeatures.AsNoTracking()
            .Where(x => phaseIds.Contains(x.PhaseId) && x.RetractedAt == null).ToListAsync(ct);
        var featureIds = features.Select(f => f.Id).ToList();

        var phaseCites = await (
            from c in db.BattlePhaseCitations.AsNoTracking()
            join s in db.Sources.AsNoTracking() on c.SourceId equals s.Id
            where phaseIds.Contains(c.PhaseId) && c.RetractedAt == null
            select new CampaignAssembler.Cite(c.PhaseId, c.Id, c.CreatedAt, s.SourceKind, s.Title, s.Url, c.Quote)).ToListAsync(ct);
        var featureCites = await (
            from c in db.BattleMapFeatureCitations.AsNoTracking()
            join s in db.Sources.AsNoTracking() on c.SourceId equals s.Id
            where featureIds.Contains(c.FeatureId) && c.RetractedAt == null
            select new CampaignAssembler.Cite(c.FeatureId, c.Id, c.CreatedAt, s.SourceKind, s.Title, s.Url, c.Quote)).ToListAsync(ct);

        var start = ev.Occurred.LowerBound;
        var belligerentRows = await (
            from p in db.EventParticipants.AsNoTracking()
            join r in db.Regimes.AsNoTracking() on p.RegimeId equals r.Id
            where p.EventId == ev.Id && p.Role == "belligerent"
            select new { r.Id, r.Slug }).ToListAsync(ct);
        var regimeIds = belligerentRows.Select(x => x.Id).ToList();
        var names = await db.RegimeNames.AsNoTracking()
            .Where(n => regimeIds.Contains(n.RegimeId) && n.IsPrimary && n.RetractedAt == null && n.ObserverRegimeId == null)
            .Select(n => new { n.RegimeId, n.Display, n.OriginalText }).ToListAsync(ct);
        var camps = await db.RegimeAlignments.AsNoTracking()
            .Where(a => regimeIds.Contains(a.RegimeId) && a.RetractedAt == null && a.ValidPeriod.Contains(start))
            .Select(a => new { a.RegimeId, a.Camp }).ToListAsync(ct);
        var belligerents = belligerentRows.Select(b => new CampaignAssembler.Belligerent(
            b.Slug,
            names.Where(n => n.RegimeId == b.Id).Select(n => CampaignAssembler.Text(n.Display, "zh-Hant") ?? n.OriginalText).FirstOrDefault() ?? b.Slug,
            camps.FirstOrDefault(c => c.RegimeId == b.Id)?.Camp)).ToList();

        return ApiResults.Ok(CampaignAssembler.Build(profile, ev, phases, features, phaseCites, featureCites, belligerents));
    }
}

/// <summary>把戰役各表的列組成 wl-campaign-web/0.1 JSON。純函式（不碰 DB），撤回列在這裡再濾一次以防呼叫端漏濾。</summary>
public static class CampaignAssembler
{
    public const string Schema = "wl-campaign-web/0.1";
    public const string SourceSchema = "worldline-db/battle-c1";

    /// <summary>一筆 citation 已 join sources 的結果；OwnerId＝階段或圖形 id。</summary>
    public sealed record Cite(Guid OwnerId, Guid Id, DateTimeOffset CreatedAt, string Type, string Citation, string? Url, string Quote);

    /// <summary>交戰方：Camp 取自 regime_alignments（戰役起日當天），不從交戰關係推導（憲法 §6「陣營」）。</summary>
    public sealed record Belligerent(string Slug, string Name, string? Camp);

    private static readonly JsonSerializerOptions GeoJson = CreateGeoJson();

    private static JsonSerializerOptions CreateGeoJson()
    {
        var o = new JsonSerializerOptions();
        o.Converters.Add(new GeoJsonConverterFactory(new GeometryFactory(new PrecisionModel(), 4326)));
        return o;
    }

    private static string D(DateOnly d) => d.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);

    /// <summary>從多語 jsonb 物件取某語言；沒有就回 null。</summary>
    public static string? Text(string? json, string lang)
    {
        if (string.IsNullOrWhiteSpace(json)) return null;
        using var doc = JsonDocument.Parse(json);
        return doc.RootElement.ValueKind == JsonValueKind.Object
               && doc.RootElement.TryGetProperty(lang, out var v) && v.ValueKind == JsonValueKind.String
            ? v.GetString() : null;
    }

    private static string CampKey(string? camp) => camp switch
    {
        Camps.Allies => "allied",
        null => "unknown",
        _ => camp,
    };

    private static IEnumerable<Cite> Ordered(IEnumerable<Cite> cites) => cites.OrderBy(c => c.CreatedAt).ThenBy(c => c.Id);

    /// <summary>依傳入順序輸出 {type, citation, url, quote}。</summary>
    private static JsonArray Sources(IEnumerable<Cite> cites) => new(cites
        .Select(c => (JsonNode)new JsonObject
        {
            ["type"] = c.Type,
            ["citation"] = c.Citation,
            ["url"] = c.Url,
            ["quote"] = c.Quote,
        }).ToArray());

    public static JsonObject Build(
        BattleProfile profile, HistoricalEvent ev,
        IEnumerable<BattlePhase> phases, IEnumerable<BattleMapFeature> features,
        IEnumerable<Cite> phaseCites, IEnumerable<Cite> featureCites,
        IEnumerable<Belligerent> belligerents)
    {
        var livePhases = phases.Where(p => p.RetractedAt is null && p.EventId == profile.EventId)
            .OrderBy(p => p.Seq).ToList();
        var seqById = livePhases.ToDictionary(p => p.Id, p => p.Seq);
        var liveFeatures = features.Where(f => f.RetractedAt is null && seqById.ContainsKey(f.PhaseId))
            .OrderBy(f => seqById[f.PhaseId]).ThenBy(f => f.FeatureKey, StringComparer.Ordinal).ToList();
        var pc = phaseCites.ToLookup(c => c.OwnerId);
        var fc = featureCites.ToLookup(c => c.OwnerId);
        var verified = profile.Status == BattleStatuses.Verified;

        var start = ev.Occurred.LowerBound;
        var end = ev.Occurred.UpperBound;

        var bellObj = new JsonObject();
        var bellList = belligerents.ToList();
        foreach (var g in bellList.GroupBy(b => CampKey(b.Camp)).OrderBy(g => g.Key, StringComparer.Ordinal))
            bellObj[g.Key] = new JsonArray(g.OrderBy(b => b.Slug, StringComparer.Ordinal).Select(b => (JsonNode)JsonValue.Create(b.Name)!).ToArray());

        var phaseArr = new JsonArray();
        foreach (var p in livePhases)
        {
            var pv = p.Status == BattleStatuses.Verified;
            phaseArr.Add(new JsonObject
            {
                ["seq"] = p.Seq,
                ["key"] = $"{profile.Slug}_p{p.Seq}",
                ["name_zh"] = Text(p.Name, "zh-Hant"),
                ["name_en"] = Text(p.Name, "en"),
                ["start"] = D(p.Period.LowerBound),
                ["end"] = D(p.Period.UpperBound),
                ["start_precision"] = p.StartPrecision == DatePrecisions.Day ? null : p.StartPrecision,
                ["end_precision"] = p.EndPrecision == DatePrecisions.Day ? null : p.EndPrecision,
                ["dates_verified"] = pv,
                ["fronts_note"] = null,
                ["summary_zh"] = Text(p.Summary, "zh-Hant"),
                ["summary_verified"] = pv && p.Summary is not null,
                ["sources"] = Sources(Ordered(pc[p.Id])),
                ["notes"] = new JsonArray(),
            });
        }

        var layers = new JsonObject();
        foreach (var (kind, layer) in new[] { (BattleFeatureKinds.Front, "fronts"), (BattleFeatureKinds.Arrow, "arrows"), (BattleFeatureKinds.Site, "sites") })
        {
            var arr = new JsonArray();
            foreach (var f in liveFeatures.Where(f => f.FeatureKind == kind))
            {
                var props = new JsonObject
                {
                    ["id"] = f.FeatureKey,
                    ["phase"] = seqById[f.PhaseId],
                };
                if (!string.IsNullOrWhiteSpace(f.Props) && JsonNode.Parse(f.Props) is JsonObject extra)
                    foreach (var (k, v) in extra.OrderBy(kv => kv.Key, StringComparer.Ordinal))
                        if (k is not ("id" or "phase" or "group" or "verified" or "sources")) props[k] = v?.DeepClone();
                props["group"] = f.SideCamp ?? "unknown";
                props["verified"] = f.Status == BattleStatuses.Verified;
                props["geom_basis"] = f.GeomBasis;
                props["sources"] = Sources(Ordered(fc[f.Id]));
                arr.Add(new JsonObject
                {
                    ["type"] = "Feature",
                    ["geometry"] = JsonSerializer.SerializeToNode(f.Geom, GeoJson),
                    ["properties"] = props,
                });
            }
            layers[layer] = new JsonObject { ["type"] = "FeatureCollection", ["features"] = arr };
        }

        // 去重後的全部出處（依 citation 字串＋url＋quote），順序：階段在前、圖形在後，各自依建立時間。
        var all = livePhases.SelectMany(p => Ordered(pc[p.Id]))
            .Concat(liveFeatures.SelectMany(f => Ordered(fc[f.Id])))
            .DistinctBy(c => (c.Type, c.Citation, c.Url, c.Quote));

        return new JsonObject
        {
            ["schema"] = Schema,
            ["source_schema"] = SourceSchema,
            ["key"] = profile.Slug,
            ["name_zh"] = Text(profile.Name, "zh-Hant"),
            ["name_en"] = Text(profile.Name, "en"),
            ["start"] = D(start),
            ["end"] = D(end),
            ["end_inclusive"] = D(end.AddDays(-1)),
            ["scale"] = "short",
            ["status"] = profile.Status,
            ["belligerents"] = bellObj,
            ["regime_slugs"] = new JsonArray(bellList.Select(b => b.Slug).Distinct().Order(StringComparer.Ordinal)
                .Select(s => (JsonNode)JsonValue.Create(s)!).ToArray()),
            ["end_verified"] = verified,
            ["note"] = null,
            ["event_ids"] = new JsonArray(JsonValue.Create(ev.Id.ToString())),
            ["totals"] = null,
            ["bounds"] = Bounds(profile.TheaterArea, liveFeatures),
            ["phases"] = phaseArr,
            ["layers"] = layers,
            ["citations"] = Sources(all),
        };
    }

    /// <summary>[[minX,minY],[maxX,maxY]]：優先用 theater_area；沒有就用全部圖形的外框；都沒有回 null。</summary>
    private static JsonNode? Bounds(MultiPolygon? theater, IReadOnlyList<BattleMapFeature> features)
    {
        var env = theater?.EnvelopeInternal;
        if (env is null || env.IsNull)
        {
            env = new Envelope();
            foreach (var f in features) env.ExpandToInclude(f.Geom.EnvelopeInternal);
            if (env.IsNull) return null;
        }
        return new JsonArray(new JsonArray(env.MinX, env.MinY), new JsonArray(env.MaxX, env.MaxY));
    }
}
