using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.4：政權查詢端點（唯讀）。依賴 task 2.16（`regime_translations`），支援
/// `?locale=`——省略時回傳 `regimes.self_name` 原文，指定的語系有對應翻譯列時改回傳
/// 翻譯內容，沒有對應翻譯列時一樣 fallback 回原文（PRD §6「多語言內容設計」：加翻譯表
/// 不會讓既有內容自動變雙語，沒寫的內容 fallback 是預期行為，不是缺陷）。
/// </summary>
[ApiController]
[Route("api/v1")]
public class RegimesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>
    /// 政權清單。`year` 省略時回傳全部政權（例如前端要一次建好 id→名稱對照表，不管
    /// 目前地圖顯示哪個年份都能用）；指定 `year` 時只回當年有（未被 I5 取代的）疆域快照
    /// 的政權——跟 task 2.6 疆域端點用同一套「當年有效」判斷，語意一致。
    /// </summary>
    [HttpGet("regimes")]
    public async Task<ActionResult<ApiResponse<IEnumerable<RegimeResponse>>>> GetAll(
        [FromQuery] int? year, [FromQuery] string? locale)
    {
        var query = db.Regimes.AsQueryable();

        if (year is not null)
        {
            var regimeIdsWithTerritoryInYear = db.RegimeTerritories
                .Where(t => t.SupersededBy == null && t.ValidPeriod.Contains(year.Value))
                .Select(t => t.RegimeId);
            query = query.Where(r => regimeIdsWithTerritoryInYear.Contains(r.Id));
        }

        var regimes = await query.ToListAsync();
        var response = await ApplyLocaleAsync(regimes, locale);

        return Ok(ApiResponse.Ok<IEnumerable<RegimeResponse>>(response));
    }

    /// <summary>取得單一政權詳情。</summary>
    [HttpGet("regimes/{id:guid}")]
    public async Task<ActionResult<ApiResponse<RegimeResponse>>> GetById(Guid id, [FromQuery] string? locale)
    {
        var regime = await db.Regimes.FirstOrDefaultAsync(r => r.Id == id);
        if (regime is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var response = (await ApplyLocaleAsync([regime], locale)).Single();
        return Ok(ApiResponse.Ok(response));
    }

    private async Task<List<RegimeResponse>> ApplyLocaleAsync(List<Regime> regimes, string? locale)
    {
        var translatedNames = new Dictionary<Guid, string>();

        if (!string.IsNullOrEmpty(locale))
        {
            var regimeIds = regimes.Select(r => r.Id).ToList();
            translatedNames = await db.RegimeTranslations
                .Where(t => regimeIds.Contains(t.RegimeId) && t.Locale == locale)
                .ToDictionaryAsync(t => t.RegimeId, t => t.SelfName);
        }

        return regimes.Select(r => new RegimeResponse
        {
            Id = r.Id,
            SelfName = translatedNames.TryGetValue(r.Id, out var translated) ? translated : r.SelfName,
            Status = r.Status,
            PredecessorRegimeId = r.PredecessorRegimeId,
            OriginTransitionType = r.OriginTransitionType,
            DestroyedByRegimeId = r.DestroyedByRegimeId,
        }).ToList();
    }
}
