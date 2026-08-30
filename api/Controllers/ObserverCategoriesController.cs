using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.12：非政權觀察者的受控類別（`observer_categories`）——目前只有查詢端點，沒有
/// 寫入端點。implementation plan 任務 2.12 明確寫「未來可擴充『中文史料傳統』等類別，
/// 本任務不用先做，等實際需要時再插入」，新增類別目前直接透過資料庫/種子資料操作，
/// 不開放 API 寫入。
/// </summary>
[ApiController]
[Route("api/v1")]
public class ObserverCategoriesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>列出全部觀察者類別——數量少（目前只有一筆），不用分頁/篩選。</summary>
    [HttpGet("observer-categories")]
    public async Task<ActionResult<ApiResponse<IEnumerable<ObserverCategoryResponse>>>> GetAll()
    {
        var categories = await db.ObserverCategories.ToListAsync();
        return Ok(ApiResponse.Ok<IEnumerable<ObserverCategoryResponse>>(
            categories.Select(c => new ObserverCategoryResponse { Id = c.Id, CategoryName = c.CategoryName })));
    }
}
