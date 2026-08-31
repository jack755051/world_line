using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.9b：地名雙軌查詢端點（唯讀，憲法 §6）。**不做寫入端點**——seed 已覆蓋首都
/// 示範，正式匯入前的來源治理見 `docs/data-governance.md`，這批資料不是靠這個 API
/// 自己長出來的，是考證完才批次匯入的，不需要一般使用情境下的 CRUD 表單。
/// </summary>
[ApiController]
[Route("api/v1")]
public class PlaceNamesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>依年份查詢當時使用中的所有地名。`year` 必填，跟 `reign-eras`（同樣是
    /// 「依年份查 X」語意）一致，不是選填的列表過濾條件。</summary>
    [HttpGet("place-names")]
    public async Task<ActionResult<ApiResponse<IEnumerable<PlaceNameResponse>>>> GetByYear([FromQuery] int? year)
    {
        if (year is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.YearRequired));
        }

        // valid_period 半開區間慣例跟 regime_territories/regime_relations 一致，但整欄本身
        // 可為 NULL——跟 reign_eras.end_year 為 NULL（尚未確定結束年）不同語意：這裡是
        // 「使用期間完全沒考證清楚」，不是「還在使用中」，兩種都算沒有明確排除這個年份，
        // 所以一律納入查詢結果，不是預設排除（見 `PlaceNameResponse` 類別文件）。
        var placeNames = await db.PlaceNames
            .Where(p => p.ValidPeriod == null || p.ValidPeriod.Value.Contains(year.Value))
            .OrderBy(p => p.HistoricalName)
            .Select(ToResponse)
            .ToListAsync();

        return Ok(ApiResponse.Ok<IEnumerable<PlaceNameResponse>>(placeNames));
    }

    /// <summary>取得單一地名詳情。</summary>
    [HttpGet("place-names/{id:guid}")]
    public async Task<ActionResult<ApiResponse<PlaceNameResponse>>> GetById(Guid id)
    {
        var placeName = await db.PlaceNames.Where(p => p.Id == id).Select(ToResponse).FirstOrDefaultAsync();
        if (placeName is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.PlaceNameNotFound));
        }

        return Ok(ApiResponse.Ok(placeName));
    }

    private static readonly System.Linq.Expressions.Expression<Func<PlaceName, PlaceNameResponse>> ToResponse =
        p => new PlaceNameResponse
        {
            Id = p.Id,
            HistoricalName = p.HistoricalName,
            ModernName = p.ModernName,
            StartYear = p.ValidPeriod == null ? (int?)null : p.ValidPeriod.Value.LowerBound,
            EndYear = p.ValidPeriod == null ? (int?)null : p.ValidPeriod.Value.UpperBound,
        };
}
