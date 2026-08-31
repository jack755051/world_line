using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Features;
using NpgsqlTypes;
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
///
/// **task 2.7（2026-08-31）新增寫入端點**：`Create` 是一般的「新增一筆疆域快照」；
/// `Correct` 是 I5 版本鏈的修正流程——新增一筆新版本、把 `SupersededBy` 指回舊版本，
/// 不覆蓋刪除原記錄（`docs/data-governance.md`「疆域修訂流程」）。兩者都回傳單一
/// GeoJSON `Feature`（不是 `FeatureCollection`）——跟 GET 端點回傳的集合共用同一個
/// attribute 形狀（見 <see cref="ToFeature"/>），前端可以直接把它塞進既有的
/// FeatureCollection 裡，不用另外設計一套回應格式。
/// </summary>
[ApiController]
[Route("api/v1")]
public class TerritoriesController(WorldLineDbContext db) : ControllerBase
{
    /// <summary>依年份查詢當時有效的所有政權疆域（跨政權）。</summary>
    [HttpGet("territories")]
    [ProducesResponseType(typeof(ApiResponse<FeatureCollection>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
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
    [ProducesResponseType(typeof(ApiResponse<FeatureCollection>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
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

    /// <summary>新增一筆疆域快照。`{regimeId}` 是路由參數，跟
    /// `CreateRegimeRelationRequest`/`CreateRegimeAliasRequest` 同一個慣例。</summary>
    [HttpPost("regimes/{regimeId:guid}/territories")]
    [ProducesResponseType(typeof(ApiResponse<Feature>), StatusCodes.Status201Created)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<Feature>>> Create(Guid regimeId, CreateRegimeTerritoryRequest request)
    {
        if (!await db.Regimes.AnyAsync(r => r.Id == regimeId))
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        // I1 精神：時間區間必填，且半開區間 [start,end) 要真的圈出至少一年，跟 task 2.9
        // 關係端點的 RelationEndBeforeStart 同一條檢查邏輯。
        if (request.EndYear <= request.StartYear)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.TerritoryEndBeforeStart));
        }

        var entity = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = regimeId,
            ValidPeriod = new NpgsqlRange<int>(request.StartYear, true, request.EndYear, false),
            Geom = request.Geom,
            IsDisputed = request.IsDisputed,
            CreatedAt = DateTimeOffset.UtcNow,
        };

        db.RegimeTerritories.Add(entity);
        await db.SaveChangesAsync();

        // 沒有「取得單一疆域快照」的端點（跟 task 2.9 關係端點同一個範圍決定：計畫只列了
        // 列表查詢＋新增），Location 指回這個政權的疆域列表。
        return Created($"/api/v1/regimes/{regimeId}/territories",
            ApiResponse.Ok(ToFeature(entity), ApiMessageCodes.CreateSuccess));
    }

    /// <summary>
    /// I5 版本鏈修正。**2026-08-31 修正（原本的設計繞過了 2.7 自己寫的停止條件，事後
    /// 補問使用者才拍板）**：`{id}` 不要求一定是這條修正鏈目前最新的一筆——沿著
    /// `SupersededBy` 一路往前追到真正最新的版本，實際的修正永遠套用在追到的那一筆
    /// 上，不管呼叫端傳的是鏈上哪一筆歷史版本的 id。這樣同一筆原始記錄不會因為呼叫端
    /// 不小心對舊版本下手而分岔出兩條互相不知道對方的修正鏈——鏈本身允許無限層（`{id}`
    /// 可以是第 1 筆、第 2 筆⋯），但任何時間點永遠只有一條，不會分叉。見
    /// <see cref="CorrectRegimeTerritoryRequest"/> 類別文件跟 `RegimeTerritory` 的
    /// `SupersededBy`/`CorrectionReason`/`CorrectedAt` 欄位說明。
    /// </summary>
    [HttpPatch("territories/{id:guid}/correct")]
    [ProducesResponseType(typeof(ApiResponse<Feature>), StatusCodes.Status200OK)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status400BadRequest)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status401Unauthorized)]
    [ProducesResponseType(typeof(ApiResponse<object?>), StatusCodes.Status404NotFound)]
    public async Task<ActionResult<ApiResponse<Feature>>> Correct(Guid id, CorrectRegimeTerritoryRequest request)
    {
        var target = await db.RegimeTerritories.FirstOrDefaultAsync(t => t.Id == id);
        if (target is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.TerritoryNotFound));
        }

        // 追到鏈上真正最新的一筆——`SupersededBy` 是 FK，指到的資料保證存在，這裡不用
        // 再處理「追到一半斷掉」的防禦分支。
        var current = target;
        while (current.SupersededBy is not null)
        {
            current = await db.RegimeTerritories.SingleAsync(t => t.Id == current.SupersededBy);
        }

        if (request.EndYear <= request.StartYear)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.TerritoryEndBeforeStart));
        }

        var replacement = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = current.RegimeId, // 修正不能過戶給別的政權，見 request 類別文件
            ValidPeriod = new NpgsqlRange<int>(request.StartYear, true, request.EndYear, false),
            Geom = request.Geom,
            IsDisputed = request.IsDisputed,
            CreatedAt = DateTimeOffset.UtcNow,
        };

        db.RegimeTerritories.Add(replacement);

        // 舊版本本身不刪除、不覆蓋幾何/時間區間——只補上「被誰取代、為什麼、什麼時候」
        // 三個欄位，原始快照的其餘內容原封不動留著，追溯鏈完整。這裡動的是 current
        // （鏈上真正最新的一筆），不是呼叫端傳的 target——兩者可能是同一筆，也可能不是。
        current.SupersededBy = replacement.Id;
        current.CorrectionReason = request.CorrectionReason;
        current.CorrectedAt = DateTimeOffset.UtcNow;

        await db.SaveChangesAsync();

        return Ok(ApiResponse.Ok(ToFeature(replacement), ApiMessageCodes.UpdateSuccess));
    }

    private static FeatureCollection ToFeatureCollection(IEnumerable<RegimeTerritory> territories)
    {
        var collection = new FeatureCollection();

        // 排序放在記憶體裡做，不是 LINQ-to-SQL 的一部分——NpgsqlRange<int> 的 LowerBound
        // 拿來排序，用 EF Core 轉譯成 SQL 沒有實際測過會不會可靠，這個端點資料量目前很小
        // （種子資料 20 筆內），先求正確、不猜測轉譯行為。
        foreach (var t in territories.OrderBy(t => t.RegimeId).ThenBy(t => t.ValidPeriod.LowerBound))
        {
            collection.Add(ToFeature(t));
        }

        return collection;
    }

    private static Feature ToFeature(RegimeTerritory t)
    {
        var attributes = new AttributesTable
        {
            { "id", t.Id },
            { "regimeId", t.RegimeId },
            { "startYear", t.ValidPeriod.LowerBound },
            { "endYear", t.ValidPeriod.UpperBound },
            { "isDisputed", t.IsDisputed },
        };
        return new Feature(t.Geom, attributes);
    }
}
