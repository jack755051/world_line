using System.Text.Json;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using NpgsqlTypes;
using WorldLine.Api.Domain;
using WorldLine.Contracts;

namespace WorldLine.Api.Common;

/// <summary>DTO ↔ 資料庫型別的轉換與共用驗證。</summary>
public static class Mapping
{
    private static readonly JsonSerializerOptions GeoJson = CreateGeoJsonOptions();

    private static JsonSerializerOptions CreateGeoJsonOptions()
    {
        var o = new JsonSerializerOptions();
        o.Converters.Add(new GeoJsonConverterFactory(new GeometryFactory(new PrecisionModel(), 4326)));
        return o;
    }

    // ── 期間 ──

    /// <summary>I1：起訖兩端都必須有值，且起 &lt; 迄（半開區間）。</summary>
    public static NpgsqlRange<DateOnly> RequireBounded(DatePeriodDto? p, string field)
    {
        if (p?.Start is not { } start || p.End is not { } end)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, $"{field} 必須同時有起日與迄日（I1，半開區間 [start, end)）。", field);
        if (start >= end)
            throw ApiError.BadRequest(ErrorCodes.PeriodRequired, $"{field} 的起日必須早於迄日（半開區間 [start, end)）。", field);
        return new NpgsqlRange<DateOnly>(start, true, end, false);
    }

    /// <summary>選填期間：允許單側無界（例：名稱使用期間），但不可起 ≥ 迄。</summary>
    public static NpgsqlRange<DateOnly>? Optional(DatePeriodDto? p, string field)
    {
        if (p is null || (p.Start is null && p.End is null)) return null;
        if (p.Start is { } s && p.End is { } e && s >= e)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 的起日必須早於迄日。", field);
        return new NpgsqlRange<DateOnly>(
            p.Start ?? default, true, p.Start is null,
            p.End ?? default, false, p.End is null);
    }

    public static DatePeriodDto? ToDto(NpgsqlRange<DateOnly>? r)
    {
        if (r is not { } v || v.IsEmpty) return null;
        return new DatePeriodDto(v.LowerBoundInfinite ? null : v.LowerBound, v.UpperBoundInfinite ? null : v.UpperBound);
    }

    public static IntervalDto ToInterval(NpgsqlRange<DateOnly> valid, NpgsqlRange<DateOnly>? startU, NpgsqlRange<DateOnly>? endU) =>
        new(valid.LowerBound, valid.UpperBound, ToDto(startU), ToDto(endU));

    // ── 多語文字（Q8 待拍板） ──

    public static string RequireLocalized(IReadOnlyDictionary<string, string>? text, string field)
    {
        if (text is null || text.Count == 0)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 至少要有一種語言（{string.Join("、", Languages.Supported)}）。", field);
        return LocalizedToJson(text, field);
    }

    public static string? OptionalLocalized(IReadOnlyDictionary<string, string>? text, string field) =>
        text is null || text.Count == 0 ? null : LocalizedToJson(text, field);

    private static string LocalizedToJson(IReadOnlyDictionary<string, string> text, string field)
    {
        foreach (var (k, v) in text)
        {
            if (!Languages.Supported.Contains(k))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 只接受 {string.Join("、", Languages.Supported)}（收到 {k}）。", field);
            if (string.IsNullOrWhiteSpace(v))
                throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field}.{k} 不可空白。", field);
        }
        return JsonSerializer.Serialize(text);
    }

    public static IReadOnlyDictionary<string, string> ReadLocalized(string json) =>
        JsonSerializer.Deserialize<Dictionary<string, string>>(json) ?? [];

    public static IReadOnlyDictionary<string, string>? ReadLocalizedOrNull(string? json) =>
        json is null ? null : ReadLocalized(json);

    // ── 幾何 ──

    /// <summary>GeoJSON（Polygon／MultiPolygon，WGS84）→ 有效的 MultiPolygon。</summary>
    public static MultiPolygon RequireMultiPolygon(JsonElement? geojson, string field)
    {
        if (geojson is not { ValueKind: JsonValueKind.Object } el)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 必須是 GeoJSON Polygon 或 MultiPolygon。", field);
        Geometry? g;
        try { g = el.Deserialize<Geometry>(GeoJson); }
        catch (JsonException e) { throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 不是合法的 GeoJSON：{e.Message}", field); }

        var multi = g switch
        {
            MultiPolygon mp => mp,
            Polygon p => new MultiPolygon([p], p.Factory),
            _ => throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 只接受 Polygon 或 MultiPolygon。", field),
        };
        multi.SRID = 4326;
        if (multi.IsEmpty || !multi.IsValid)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 幾何無效（自相交或空白）；請在 QGIS 修正拓撲後再送。", field);
        return multi;
    }

    /// <summary>任意有效的 GeoJSON 幾何（事件地點：Point 等），WGS84。</summary>
    public static Geometry RequireGeometry(JsonElement geojson, string field)
    {
        if (geojson.ValueKind != JsonValueKind.Object)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 必須是 GeoJSON 幾何。", field);
        Geometry? g;
        try { g = geojson.Deserialize<Geometry>(GeoJson); }
        catch (JsonException e) { throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 不是合法的 GeoJSON：{e.Message}", field); }
        if (g is null || g.IsEmpty || !g.IsValid)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 幾何無效。", field);
        g.SRID = 4326;
        return g;
    }

    public static JsonElement ToGeoJson(Geometry g) => JsonSerializer.SerializeToElement(g, GeoJson);

    public static string RequireText(string? value, string field, int? maxLength = null)
    {
        if (string.IsNullOrWhiteSpace(value))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 為必填。", field);
        var v = value.Trim();
        if (maxLength is { } max && v.Length > max)
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 長度不可超過 {max}。", field);
        return v;
    }

    public static string RequireOneOf(string? value, IReadOnlyCollection<string> allowed, string field)
    {
        if (value is null || !allowed.Contains(value))
            throw ApiError.BadRequest(ErrorCodes.ValidationFailed, $"{field} 必須是 {string.Join(" | ", allowed)} 之一。", field);
        return value;
    }
}
