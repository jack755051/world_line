using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.4：政權查詢端點（唯讀）。依賴 task 2.16（`regime_translations`），支援
/// `?locale=`——省略時回傳 `regimes.self_name` 原文，指定的語系有對應翻譯列時改回傳
/// 翻譯內容，沒有對應翻譯列時一樣 fallback 回原文（PRD §6「多語言內容設計」：加翻譯表
/// 不會讓既有內容自動變雙語，沒寫的內容 fallback 是預期行為，不是缺陷）。
///
/// **task 2.5（2026-08-31）新增寫入端點**：`RegimeTransitionValidator`（task 2.1）
/// 是純函式、不查 DB，這裡補上兩層它管不到的東西——(1) 跨政權的 referential 檢查
/// （`predecessorRegimeId`/`destroyedByRegimeId` 引用的政權是否存在、狀態是否合理支撐
/// 這次轉換）；(2) 呼叫驗證器本身擋非法轉換。**刻意不檢查**：「分裂」轉換是否至少要有
/// 2 個子政權掛在同一個 `predecessorRegimeId`——子政權是逐筆個別 POST 建立的，建立
/// 第一筆的當下不可能同步驗證「總共會有幾筆」，這條數量完整性檢查交給 task 2.15 的
/// integration test 或人工檢視，不在單筆寫入端點做（使用者 2026-08-31 確認）。
/// </summary>
[ApiController]
[Route("api/v1")]
public class RegimesController(WorldLineDbContext db, IRegimeTransitionValidator transitionValidator) : ControllerBase
{
    /// <summary>
    /// 政權清單。`year` 省略時回傳全部政權（例如前端要一次建好 id→名稱對照表，不管
    /// 目前地圖顯示哪個年份都能用）；指定 `year` 時只回當年有（未被 I5 取代的）疆域快照
    /// 的政權——跟 task 2.6 疆域端點用同一套「當年有效」判斷，語意一致。
    /// </summary>
    [HttpGet("regimes")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<RegimeResponse>>), StatusCodes.Status200OK)]
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
    [ProducesResponseType(typeof(ApiResponse<RegimeResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
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

    /// <summary>新增政權——一律從 <see cref="RegimeStatus.Active"/> 起步（見
    /// `CreateRegimeRequest` 類別文件），掛在 task 2.14 的 `ApiWriteKeyMiddleware`
    /// 底下（POST 一律要求 `X-API-Key`）。</summary>
    [HttpPost("regimes")]
    [ProducesResponseType(typeof(ApiResponse<RegimeResponse>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    public async Task<ActionResult<ApiResponse<RegimeResponse>>> Create(CreateRegimeRequest request)
    {
        // 2.1 的純函式檢查：predecessorRegimeId/originTransitionType 內部一致性
        // （同時有值或同時為空、originTransitionType 是受控值）。
        var linkage = transitionValidator.ValidateOriginLinkage(request.PredecessorRegimeId, request.OriginTransitionType);
        if (!linkage.IsLegal)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.InvalidOriginLinkage));
        }

        // 2.5 新增的跨政權 referential 檢查——2.1 不查 DB，這裡才查得到。
        if (request.PredecessorRegimeId is not null)
        {
            var predecessor = await db.Regimes.FirstOrDefaultAsync(r => r.Id == request.PredecessorRegimeId);
            if (predecessor is null)
            {
                return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.PredecessorRegimeNotFound));
            }

            // 任務描述給的具體例子：已經 conquered（被滅亡）的政權不能再當分裂/禪讓的
            // 前身——被滅亡是暴力終結，跟「分裂出新政權」或「禪讓給新政權」是不相容的
            // 兩種終局，不會同時發生在同一個政權身上。
            if (predecessor.Status == RegimeStatus.Conquered.ToCode())
            {
                return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.PredecessorAlreadyConquered));
            }
        }

        var entity = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = request.SelfName,
            Status = RegimeStatus.Active.ToCode(),
            PredecessorRegimeId = request.PredecessorRegimeId,
            OriginTransitionType = request.OriginTransitionType,
            DestroyedByRegimeId = null,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        db.Regimes.Add(entity);
        await db.SaveChangesAsync();

        var response = (await ApplyLocaleAsync([entity], null)).Single();
        return CreatedAtAction(nameof(GetById), new { id = entity.Id },
            ApiResponse.Ok(response, ApiMessageCodes.CreateSuccess));
    }

    /// <summary>更新政權狀態（憲法 §4 轉換）——目前唯一用途，見 `UpdateRegimeRequest`
    /// 類別文件。</summary>
    [HttpPatch("regimes/{id:guid}")]
    [ProducesResponseType(typeof(ApiResponse<RegimeResponse>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<RegimeResponse>>> Update(Guid id, UpdateRegimeRequest request)
    {
        var regime = await db.Regimes.FirstOrDefaultAsync(r => r.Id == id);
        if (regime is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        // 2.1 的純函式檢查：只認憲法 §4 那三條合法轉換，全部只能從 active 出發。
        var transition = transitionValidator.ValidateStatusTransition(regime.Status, request.Status);
        if (!transition.IsLegal)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.InvalidStatusTransition));
        }

        // destroyedByRegimeId 跟「是否轉成 conquered」必須一致（見 SeedData.cs 既有慣例：
        // 只有 conquered 的政權才會設這個欄位）——這裡驗證的時間點 request.Status 已經
        // 通過上面的驗證，保證是合法代碼，可以直接用字串相等比對，不用再 TryParse 一次。
        var isConquered = request.Status == RegimeStatus.Conquered.ToCode();
        if (isConquered)
        {
            if (request.DestroyedByRegimeId is null)
            {
                return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.DestroyedByRegimeRequired));
            }

            if (!await db.Regimes.AnyAsync(r => r.Id == request.DestroyedByRegimeId))
            {
                return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.DestroyedByRegimeNotFound));
            }
        }
        else if (request.DestroyedByRegimeId is not null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.DestroyedByRegimeOnlyForConquered));
        }

        regime.Status = request.Status;
        regime.DestroyedByRegimeId = request.DestroyedByRegimeId;
        regime.UpdatedAt = DateTimeOffset.UtcNow;

        await db.SaveChangesAsync();

        var response = (await ApplyLocaleAsync([regime], null)).Single();
        return Ok(ApiResponse.Ok(response, ApiMessageCodes.UpdateSuccess));
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
