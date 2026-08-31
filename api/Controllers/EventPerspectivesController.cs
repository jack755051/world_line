using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.12：事件的多重視角敘事 CRUD（`historical_event_perspectives`，PRD §6／notes
/// §十「客觀骨幹 + 各方主觀敘事」）。**路由刻意不用 `{eventId:guid}` 約束**——
/// `historical_events.id` 是手動指定的字串 slug，不是 GUID，跟 `EventsController`
/// 同一個理由，不能照抄 `RegimesController` 的 `:guid` 路由。
/// </summary>
[ApiController]
[Route("api/v1")]
public class EventPerspectivesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>取得某事件的全部視角——**不支援 `?locale=`**，見
    /// `EventPerspectiveResponse` 類別註解（整張表不進翻譯範圍）。</summary>
    [HttpGet("events/{eventId}/perspectives")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<EventPerspectiveResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<IEnumerable<EventPerspectiveResponse>>>> GetByEvent(string eventId)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == eventId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.EventNotFound));
        }

        var perspectives = await db.HistoricalEventPerspectives
            .Where(p => p.EventId == eventId)
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<EventPerspectiveResponse>>(perspectives.Select(ToResponse)));
    }

    /// <summary>新增一筆視角敘事——應用層驗證 `regimeId`/`observerCategoryId` 至少擇一
    /// 非 NULL（PRD §6 原話，見 <see cref="CreateEventPerspectiveRequest"/> 類別
    /// 註解），兩個都有值也允許，不是互斥。</summary>
    [HttpPost("events/{eventId}/perspectives")]
    [ProducesResponseType(typeof(ApiResponse<EventPerspectiveResponse>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<EventPerspectiveResponse>>> Create(
        string eventId, CreateEventPerspectiveRequest request)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == eventId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.EventNotFound));
        }

        if (request.RegimeId is null && request.ObserverCategoryId is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.PerspectivePartyRequired));
        }

        if (request.RegimeId is not null && !await db.Regimes.AnyAsync(r => r.Id == request.RegimeId))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.RegimeNotFound));
        }

        if (request.ObserverCategoryId is not null
            && !await db.ObserverCategories.AnyAsync(c => c.Id == request.ObserverCategoryId))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.ObserverCategoryNotFound));
        }

        var entity = new HistoricalEventPerspective
        {
            Id = Guid.NewGuid(),
            EventId = eventId,
            RegimeId = request.RegimeId,
            ObserverCategoryId = request.ObserverCategoryId,
            LocalName = request.LocalName,
            NarrativeSummary = request.NarrativeSummary,
            OfficialJustification = request.OfficialJustification,
            // 存進 jsonb 欄位前轉回原始文字——GetRawText() 保留呼叫端送來的原始格式，
            // 同 EventsController.Create() 對 Sections 的處理原則。
            PrimarySources = request.PrimarySources?.GetRawText(),
            ClaimedCasualties = request.ClaimedCasualties?.GetRawText(),
        };

        db.HistoricalEventPerspectives.Add(entity);
        await db.SaveChangesAsync();

        // 沒有「取得單一視角」的端點（計畫範圍只有列表查詢 + 新增，見 implementation
        // plan 任務 2.12），Location 指回這個事件的視角列表，同 RegimeRelationsController
        // 的既有慣例。
        return Created($"/api/v1/events/{eventId}/perspectives",
            ApiResponse.Ok(ToResponse(entity), ApiMessageCodes.CreateSuccess));
    }

    private static EventPerspectiveResponse ToResponse(HistoricalEventPerspective p) => new()
    {
        Id = p.Id,
        EventId = p.EventId!, // 查詢/建立時都已保證非 null，見上方 Where(p => p.EventId == eventId) 篩選
        RegimeId = p.RegimeId,
        ObserverCategoryId = p.ObserverCategoryId,
        LocalName = p.LocalName,
        NarrativeSummary = p.NarrativeSummary,
        OfficialJustification = p.OfficialJustification,
        // JsonDocument 故意不 Dispose：RootElement 要活到框架序列化這個回應物件的當下，
        // 同 EventsController.ApplyLocaleAsync() 對 Sections 的處理原則。
        PrimarySources = p.PrimarySources is null ? null : JsonDocument.Parse(p.PrimarySources).RootElement,
        ClaimedCasualties = p.ClaimedCasualties is null ? null : JsonDocument.Parse(p.ClaimedCasualties).RootElement,
    };
}
