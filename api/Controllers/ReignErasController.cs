using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;

namespace WorldLine.Api.Controllers;

/// <summary>task 2.3：紀年年號查詢端點（PRD §5「自建 reign_eras 查詢表」）。唯讀，公開不驗證。</summary>
[ApiController]
[Route("api/v1")]
public class ReignErasController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>依年份查詢當時使用中的所有年號（跨政權）。</summary>
    [HttpGet("reign-eras")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<ReignEraResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    public async Task<ActionResult<ApiResponse<IEnumerable<ReignEraResponse>>>> GetByYear([FromQuery] int? year)
    {
        if (year is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.YearRequired));
        }

        // 半開區間慣例：[start_year, end_year)，跟 regime_territories/regime_relations 一致
        // （見 docs/data-governance.md）。end_year 為 NULL 代表尚未確定結束年，視為持續使用中。
        var eras = await db.ReignEras
            .Where(e => e.StartYear <= year && (e.EndYear == null || year < e.EndYear))
            .OrderBy(e => e.StartYear)
            .Select(ToResponse)
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<ReignEraResponse>>(eras));
    }

    /// <summary>取得某政權底下所有年號，依起始年排序。</summary>
    [HttpGet("regimes/{regimeId:guid}/reign-eras")]
    [ProducesResponseType(typeof(ApiResponse<IEnumerable<ReignEraResponse>>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<IEnumerable<ReignEraResponse>>>> GetByRegime(Guid regimeId)
    {
        var regimeExists = await db.Regimes.AnyAsync(r => r.Id == regimeId);
        if (!regimeExists)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var eras = await db.ReignEras
            .Where(e => e.RegimeId == regimeId)
            .OrderBy(e => e.StartYear)
            .Select(ToResponse)
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<ReignEraResponse>>(eras));
    }

    private static readonly System.Linq.Expressions.Expression<Func<Data.Entities.ReignEra, ReignEraResponse>> ToResponse =
        e => new ReignEraResponse
        {
            Id = e.Id,
            RegimeId = e.RegimeId,
            EraName = e.EraName,
            StartYear = e.StartYear,
            EndYear = e.EndYear,
        };
}
