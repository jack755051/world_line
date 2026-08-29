using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Features;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.6：疆域查詢端點（唯讀，R2/Story 1 核心查詢）。回傳標準 GeoJSON
/// <see cref="FeatureCollection"/>，前端 MapLibre 可以直接當 geojson source 用，
/// 不需要額外轉換（`Geom` 透過 Program.cs 掛的 <c>GeoJsonConverterFactory</c> 自動序列化
/// 成標準 GeoJSON geometry）。不依賴 task 2.16 的多語系翻譯——疆域形狀本身沒有語言問題，
/// 這點跟需要 `?locale=` 的 2.4（政權名稱查詢）不同，所以可以先做，不用等 2.4。
/// </summary>
[ApiController]
[Route("api/v1")]
public class TerritoriesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>依年份查詢當時有效的所有政權疆域（跨政權）。</summary>
    [HttpGet("territories")]
    public async Task<ActionResult<ApiResponse<FeatureCollection>>> GetByYear([FromQuery] int? year)
    {
        if (year is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.YearRequired));
        }

        // 半開區間慣例：[start_year, end_year)，跟 reign_eras（task 2.3）一致。
        // 只回「目前有效」的快照：排除已被 I5 修正鏈取代的舊版本（SupersededBy 非 null
        // 代表這筆已經有更新的修正版本，見 RegimeTerritory 類別註解）。IsDisputed=true 的列
        // 不排除——那是「同期並存的不同史觀」，不是新舊版本關係，前端依 isDisputed 決定要不要
        // 用斜線網底呈現（PRD §5）。
        var territories = await db.RegimeTerritories
            .Where(t => t.SupersededBy == null && t.ValidPeriod.Contains(year.Value))
            .ToListAsync();

        return Ok(ApiResponse.Ok(ToFeatureCollection(territories)));
    }

    /// <summary>取得某政權底下所有目前有效的疆域快照，依起始年排序。</summary>
    [HttpGet("regimes/{regimeId:guid}/territories")]
    public async Task<ActionResult<ApiResponse<FeatureCollection>>> GetByRegime(Guid regimeId)
    {
        var regimeExists = await db.Regimes.AnyAsync(r => r.Id == regimeId);
        if (!regimeExists)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var territories = await db.RegimeTerritories
            .Where(t => t.RegimeId == regimeId && t.SupersededBy == null)
            .ToListAsync();

        return Ok(ApiResponse.Ok(ToFeatureCollection(territories)));
    }

    private static FeatureCollection ToFeatureCollection(IEnumerable<RegimeTerritory> territories)
    {
        var collection = new FeatureCollection();

        // 排序放在記憶體裡做，不是 LINQ-to-SQL 的一部分——NpgsqlRange<int> 的 LowerBound
        // 拿來排序，用 EF Core 轉譯成 SQL 沒有實際測過會不會可靠，這個端點資料量目前很小
        // （種子資料 20 筆內），先求正確、不猜測轉譯行為。
        foreach (var t in territories.OrderBy(t => t.RegimeId).ThenBy(t => t.ValidPeriod.LowerBound))
        {
            var attributes = new AttributesTable
            {
                { "id", t.Id },
                { "regimeId", t.RegimeId },
                { "startYear", t.ValidPeriod.LowerBound },
                { "endYear", t.ValidPeriod.UpperBound },
                { "isDisputed", t.IsDisputed },
            };
            collection.Add(new Feature(t.Geom, attributes));
        }

        return collection;
    }
}
