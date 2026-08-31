using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.8：史觀主線 preset 查詢端點（唯讀，方案 D——把「哪個傳承序列算正統」跟中立的
/// `regimes`/`regime_transition_events` 客觀轉換邊圖解耦，見 PRD §6）。依賴 task 2.16
/// （`lineage_preset_translations`），`presetName`/`description` 支援 `?locale=`，
/// 跟 2.4/2.6/2.10 同一套慣例。
/// </summary>
[ApiController]
[Route("api/v1")]
public class LineagePresetsController(WorldLineDbContext db) : ControllerBase
{
    [HttpGet("lineage-presets")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<LineagePresetResponse>>), StatusCodes.Status200OK)]
    public async Task<ActionResult<ApiResponse<IEnumerable<LineagePresetResponse>>>> GetAll([FromQuery] string? locale)
    {
        var presets = await db.LineagePresets.ToListAsync();
        var response = await ApplyLocaleAsync(presets, locale);
        return Ok(ApiResponse.Ok<IEnumerable<LineagePresetResponse>>(response));
    }

    /// <summary>取得某個 preset 底下依 `sort_order` 排序的政權序列。</summary>
    [HttpGet("lineage-presets/{id:guid}/regimes")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<LineagePresetRegimeResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<IEnumerable<LineagePresetRegimeResponse>>>> GetRegimes(Guid id)
    {
        if (!await db.LineagePresets.AnyAsync(p => p.Id == id))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.LineagePresetNotFound));
        }

        var members = await db.LineagePresetMembers
            .Where(m => m.PresetId == id)
            .Join(db.Regimes, m => m.RegimeId, r => r.Id, (m, r) => new { m.SortOrder, Regime = r })
            .OrderBy(x => x.SortOrder)
            .ToListAsync();

        var response = members.Select(x => new LineagePresetRegimeResponse
        {
            SortOrder = x.SortOrder,
            Id = x.Regime.Id,
            SelfName = x.Regime.SelfName,
            Status = x.Regime.Status,
            PredecessorRegimeId = x.Regime.PredecessorRegimeId,
            OriginTransitionType = x.Regime.OriginTransitionType,
            DestroyedByRegimeId = x.Regime.DestroyedByRegimeId,
        });

        return Ok(ApiResponse.Ok<IEnumerable<LineagePresetRegimeResponse>>(response));
    }

    private async Task<List<LineagePresetResponse>> ApplyLocaleAsync(List<LineagePreset> presets, string? locale)
    {
        var translated = new Dictionary<Guid, (string PresetName, string? Description)>();

        if (!string.IsNullOrEmpty(locale))
        {
            var ids = presets.Select(p => p.Id).ToList();
            translated = await db.LineagePresetTranslations
                .Where(t => ids.Contains(t.LineagePresetId) && t.Locale == locale)
                .ToDictionaryAsync(t => t.LineagePresetId, t => (t.PresetName, t.Description));
        }

        return presets.Select(p =>
        {
            var hasTranslation = translated.TryGetValue(p.Id, out var t);
            return new LineagePresetResponse
            {
                Id = p.Id,
                PresetName = hasTranslation ? t.PresetName : p.PresetName,
                Description = hasTranslation ? t.Description : p.Description,
                IsDefault = p.IsDefault,
            };
        }).ToList();
    }
}
