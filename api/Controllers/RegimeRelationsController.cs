using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NpgsqlTypes;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.9：政權持續性關係 CRUD（`regime_relations`——貿易/朝貢/和親/同盟等沒有單一
/// 時間點、更像持續狀態的政權互動，跟有明確起訖的 `historical_events` 拆開，見 PRD §6
/// 「政權互動依離散事件 vs 持續關係拆兩張表」）。
/// </summary>
[ApiController]
[Route("api/v1")]
public class RegimeRelationsController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>取得某政權在某年份有效的持續性關係——關係表本身是對稱的
    /// （`regime_a_id`/`regime_b_id`，沒有主從之分），這裡回傳這個政權出現在任一端的
    /// 所有關係列。`year` 比照 territories/events：查詢時間點是必填，不是選填的列表
    /// 過濾條件。</summary>
    [HttpGet("regimes/{regimeId:guid}/relations")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<RegimeRelationResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<IEnumerable<RegimeRelationResponse>>>> GetByRegimeAndYear(
        Guid regimeId, [FromQuery] int? year)
    {
        if (year is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.YearRequired));
        }

        if (!await db.Regimes.AnyAsync(r => r.Id == regimeId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var relations = await db.RegimeRelations
            .Where(r => (r.RegimeAId == regimeId || r.RegimeBId == regimeId) && r.ValidPeriod.Contains(year.Value))
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<RegimeRelationResponse>>(relations.Select(ToResponse)));
    }

    /// <summary>新增一筆持續性關係，`{regimeId}` 是關係的一端，request body 指定另一端
    /// 是誰（見 <see cref="CreateRegimeRelationRequest"/> 的類別註解）。</summary>
    [HttpPost("regimes/{regimeId:guid}/relations")]
    [ProducesResponseType(typeof(ApiResponse<RegimeRelationResponse>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<RegimeRelationResponse>>> Create(
        Guid regimeId, CreateRegimeRelationRequest request)
    {
        if (!await db.Regimes.AnyAsync(r => r.Id == regimeId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        if (regimeId == request.OtherRegimeId)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.RelationSameRegime));
        }

        if (!await db.Regimes.AnyAsync(r => r.Id == request.OtherRegimeId))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.RelationOtherRegimeNotFound));
        }

        // I1 精神：時間區間必填，且半開區間 [start,end) 要真的圈出至少一年，結束年份沒有
        // 晚於開始年份的話代表使用者填反了，或這筆關係語意上不存在（起訖同一年）。
        if (request.EndYear <= request.StartYear)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.RelationEndBeforeStart));
        }

        var entity = new RegimeRelation
        {
            Id = Guid.NewGuid(),
            RegimeAId = regimeId,
            RegimeBId = request.OtherRegimeId,
            RelationType = request.RelationType,
            ValidPeriod = new NpgsqlRange<int>(request.StartYear, true, request.EndYear, false),
            Route = request.Route,
            Description = request.Description,
            CreatedAt = DateTimeOffset.UtcNow,
        };

        db.RegimeRelations.Add(entity);
        await db.SaveChangesAsync();

        // 沒有「取得單一關係」的端點（計畫範圍只有列表查詢 + 新增，見 implementation
        // plan 任務 2.9），Location 指回這筆關係所屬的集合（這個政權的關係列表），不是
        // 指向一個不存在的單筆資源端點。
        return Created($"/api/v1/regimes/{regimeId}/relations",
            ApiResponse.Ok(ToResponse(entity), ApiMessageCodes.CreateSuccess));
    }

    private static RegimeRelationResponse ToResponse(RegimeRelation relation) => new()
    {
        Id = relation.Id,
        RegimeAId = relation.RegimeAId,
        RegimeBId = relation.RegimeBId,
        RelationType = relation.RelationType,
        StartYear = relation.ValidPeriod.LowerBound,
        EndYear = relation.ValidPeriod.UpperBound,
        Description = relation.Description,
        Route = relation.Route,
    };
}
