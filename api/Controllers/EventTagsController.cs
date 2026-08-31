using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;

namespace WorldLine.Api.Controllers;

/// <summary>task 2.11：事件類型標籤（受控詞彙，取代單一 `event_type` 欄位，見 PRD §6）。
/// 只有這一個唯讀端點——標籤本身是固定分類詞彙表，不開放經由 API 新增/修改，種子資料
/// 已涵蓋（戰爭／政權更替／神話援引），之後真的需要擴充詞彙表再走資料庫遷移，不是應用層
/// CRUD 的範圍。</summary>
[ApiController]
[Route("api/v1")]
public class EventTagsController(WorldLineDbContext db) : ControllerBase
{
    [HttpGet("event-tags")]
    public async Task<ActionResult<ApiResponse<IEnumerable<EventTagResponse>>>> GetAll()
    {
        var tags = await db.EventTags
            .OrderBy(t => t.Id)
            .Select(t => new EventTagResponse { Id = t.Id, TagName = t.TagName })
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<EventTagResponse>>(tags));
    }
}
