using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.9a：政權代稱（Alias）CRUD——PRD Story 3「觀察視角切換與名稱可追溯性」的資料
/// 來源。`{regimeId}` 是代稱指回的自稱本體（`regime_aliases.regime_id`，I4 FK，不可為
/// 孤兒資料），跟 `RegimeRelationsController`／`EventsController` 同一套「路由參數就是
/// 主體、body 只填另一端」的慣例。**依賴 task 2.16**：`alias_name` 在翻譯範圍內，同
/// task 2.4 支援 `?locale=`。
/// </summary>
[ApiController]
[Route("api/v1")]
public class RegimeAliasesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>取得某政權的所有代稱——不分年份/觀察視角，一次全部回傳（代稱本身沒有
    /// 時間區間欄位，跟疆域/事件不同，不需要 `?year=`）。</summary>
    [HttpGet("regimes/{regimeId:guid}/aliases")]
    public async Task<ActionResult<ApiResponse<IEnumerable<RegimeAliasResponse>>>> GetByRegime(
        Guid regimeId, [FromQuery] string? locale)
    {
        if (!await db.Regimes.AnyAsync(r => r.Id == regimeId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var aliases = await db.RegimeAliases.Where(a => a.RegimeId == regimeId).ToListAsync();
        var response = await ApplyLocaleAsync(aliases, locale);

        return Ok(ApiResponse.Ok<IEnumerable<RegimeAliasResponse>>(response));
    }

    /// <summary>新增一筆代稱。I4 校驗：`{regimeId}`（代稱指回的自稱本體）必須存在；
    /// `observerRegimeId`（若有指定）也必須是存在的政權，不能引用不存在的觀察視角。</summary>
    [HttpPost("regimes/{regimeId:guid}/aliases")]
    public async Task<ActionResult<ApiResponse<RegimeAliasResponse>>> Create(
        Guid regimeId, CreateRegimeAliasRequest request)
    {
        if (!await db.Regimes.AnyAsync(r => r.Id == regimeId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        if (request.ObserverRegimeId is not null && !await db.Regimes.AnyAsync(r => r.Id == request.ObserverRegimeId))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.ObserverRegimeNotFound));
        }

        if (!RegimeAliasType.IsValid(request.AliasType))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.InvalidAliasType));
        }

        var entity = new RegimeAlias
        {
            Id = Guid.NewGuid(),
            RegimeId = regimeId,
            ObserverRegimeId = request.ObserverRegimeId,
            AliasName = request.AliasName,
            AliasType = request.AliasType,
            CreatedAt = DateTimeOffset.UtcNow,
        };

        db.RegimeAliases.Add(entity);
        await db.SaveChangesAsync();

        // 沒有「取得單一代稱」的端點（跟 task 2.9 關係端點同一個範圍決定：計畫只列了
        // 列表查詢＋新增），Location 指回這個政權的代稱列表。
        return Created($"/api/v1/regimes/{regimeId}/aliases",
            ApiResponse.Ok(ToResponse(entity), ApiMessageCodes.CreateSuccess));
    }

    private async Task<List<RegimeAliasResponse>> ApplyLocaleAsync(List<RegimeAlias> aliases, string? locale)
    {
        var translatedNames = new Dictionary<Guid, string>();

        if (!string.IsNullOrEmpty(locale))
        {
            var aliasIds = aliases.Select(a => a.Id).ToList();
            translatedNames = await db.RegimeAliasTranslations
                .Where(t => aliasIds.Contains(t.RegimeAliasId) && t.Locale == locale)
                .ToDictionaryAsync(t => t.RegimeAliasId, t => t.AliasName);
        }

        return aliases.Select(a => new RegimeAliasResponse
        {
            Id = a.Id,
            RegimeId = a.RegimeId,
            ObserverRegimeId = a.ObserverRegimeId,
            AliasName = translatedNames.TryGetValue(a.Id, out var translated) ? translated : a.AliasName,
            AliasType = a.AliasType,
        }).ToList();
    }

    private static RegimeAliasResponse ToResponse(RegimeAlias alias) => new()
    {
        Id = alias.Id,
        RegimeId = alias.RegimeId,
        ObserverRegimeId = alias.ObserverRegimeId,
        AliasName = alias.AliasName,
        AliasType = alias.AliasType,
    };
}
