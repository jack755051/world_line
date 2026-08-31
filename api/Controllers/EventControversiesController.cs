using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.13：事件爭議點 CRUD（`historical_event_controversies`，notes §十.2）。依賴
/// task 2.16：`topic`/`neutralDescription` 支援 `?locale=`，`viewpoints`（誰主張什麼）
/// 不翻譯，同 `RegimesController`/`EventsController` 既有慣例。**路由刻意不用
/// `{eventId:guid}` 約束**，理由同 `EventPerspectivesController`。
/// </summary>
[ApiController]
[Route("api/v1")]
public class EventControversiesController(WorldLineDbContext db) : ControllerBase
{
    [HttpGet("events/{eventId}/controversies")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<EventControversyResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<IEnumerable<EventControversyResponse>>>> GetByEvent(
        string eventId, [FromQuery] string? locale)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == eventId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.EventNotFound));
        }

        var controversies = await db.HistoricalEventControversies
            .Where(c => c.EventId == eventId)
            .ToListAsync();

        var response = await ApplyLocaleAsync(controversies, locale);
        return Ok(ApiResponse.Ok<IEnumerable<EventControversyResponse>>(response));
    }

    /// <summary>新增一筆爭議點——沒有政權/觀察者 FK（爭議點本身是「尚無共識的問題」，
    /// 不歸屬於特定當事方，見 `docs/data-governance.md`），只需要事件存在。</summary>
    [HttpPost("events/{eventId}/controversies")]
    [ProducesResponseType(typeof(ApiResponse<EventControversyResponse>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<EventControversyResponse>>> Create(
        string eventId, CreateEventControversyRequest request)
    {
        if (!await db.HistoricalEvents.AnyAsync(e => e.Id == eventId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.EventNotFound));
        }

        var entity = new HistoricalEventControversy
        {
            Id = Guid.NewGuid(),
            EventId = eventId,
            Topic = request.Topic,
            NeutralDescription = request.NeutralDescription,
            Viewpoints = request.Viewpoints?.GetRawText(),
        };

        db.HistoricalEventControversies.Add(entity);
        await db.SaveChangesAsync();

        var response = (await ApplyLocaleAsync([entity], null)).Single();
        return Created($"/api/v1/events/{eventId}/controversies",
            ApiResponse.Ok(response, ApiMessageCodes.CreateSuccess));
    }

    private async Task<List<EventControversyResponse>> ApplyLocaleAsync(
        List<HistoricalEventControversy> controversies, string? locale)
    {
        var translations = new Dictionary<Guid, HistoricalEventControversyTranslation>();

        if (!string.IsNullOrEmpty(locale))
        {
            var ids = controversies.Select(c => c.Id).ToList();
            translations = await db.HistoricalEventControversyTranslations
                .Where(t => ids.Contains(t.ControversyId) && t.Locale == locale)
                .ToDictionaryAsync(t => t.ControversyId);
        }

        return controversies.Select(c =>
        {
            translations.TryGetValue(c.Id, out var translation);
            return new EventControversyResponse
            {
                Id = c.Id,
                EventId = c.EventId!, // 查詢/建立時都已保證非 null，見上方 Where 篩選/剛指派的值
                Topic = translation?.Topic ?? c.Topic,
                NeutralDescription = translation?.NeutralDescription ?? c.NeutralDescription,
                // JsonDocument 故意不 Dispose，理由同 EventsController.ApplyLocaleAsync()
                // 對 Sections 的處理原則。
                Viewpoints = c.Viewpoints is null ? null : JsonDocument.Parse(c.Viewpoints).RootElement,
            };
        }).ToList();
    }
}
