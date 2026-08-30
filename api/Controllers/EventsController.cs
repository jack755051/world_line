using System.Text.Json;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Data.Entities;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Controllers;

/// <summary>
/// task 2.10：事件骨幹 CRUD。依賴 task 2.16（<c>historical_event_translations</c>），
/// `name` 支援 `?locale=`，跟 2.4/2.6 同一套慣例——省略時回原文，指定語系有對應翻譯列時
/// 回翻譯內容，沒有對應翻譯列時一樣 fallback 回原文。**`sections` JSONB 不支援翻譯**：
/// `historical_event_translations` 目前只有 `Name` 欄位（見該實體的類別註解——sections
/// 要不要連帶翻譯、翻譯結構長怎樣尚未拍板），這裡 `?locale=` 只影響 `name`，`sections`
/// 一律回資料庫原始內容，不受 `?locale=` 影響——這不是遺漏，是這個任務動工前需要先決定
/// 的問題裡，範圍最小、不需要新增 schema 就能回答的那個答案：沒有 `historical_event_
/// translations.sections` 這個欄位，`sections` 目前就是不可翻譯，之後真的要做才加欄位。
///
/// **`POST` 請求 body 範圍**見 <see cref="CreateHistoricalEventRequest"/> 的類別註解。
///
/// **2026-08-30 追加 `GET /regimes/{regimeId}/events`**（PRD Story 2 AC#3「互動清單」
/// 離散事件那一半）：見 <see cref="GetInteractionsByRegime"/> 的方法註解。
/// </summary>
[ApiController]
[Route("api/v1")]
public class EventsController(WorldLineDbContext db, IEdtfService edtfService) : ControllerBase
{
    /// <summary>依年份查詢當時「有效」的事件——跟 territories/reign_eras 用 INT4RANGE
    /// 半開區間同一個語意，換算成事件的 decimal 精度版本：事件區間跟查詢年份代表的整年
    /// [year, year+1) 有重疊就算。single-day/single-year 事件（StartDecimal ==
    /// EndDecimal）套用同一個判斷式一樣成立，不需要另外特判。</summary>
    [HttpGet("events")]
    public async Task<ActionResult<ApiResponse<IEnumerable<HistoricalEventResponse>>>> GetByYear(
        [FromQuery] int? year, [FromQuery] string? locale)
    {
        if (year is null)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.YearRequired));
        }

        var events = await db.HistoricalEvents
            .Where(e => e.StartDecimal < year + 1 && e.EndDecimal >= year)
            .ToListAsync();

        var response = await ApplyLocaleAsync(events, locale);
        return Ok(ApiResponse.Ok<IEnumerable<HistoricalEventResponse>>(response));
    }

    /// <summary>取得單一事件詳情。**路由刻意不用 <c>{id:guid}</c> 約束**——
    /// <c>historical_events.id</c> 是手動指定的字串 slug，不是 GUID（見
    /// <c>HistoricalEvent.Id</c> 的類別註解），跟 <c>RegimesController</c> 的
    /// <c>{id:guid}</c> 不是同一種資源識別碼型別，不能照抄。</summary>
    [HttpGet("events/{id}")]
    public async Task<ActionResult<ApiResponse<HistoricalEventResponse>>> GetById(string id, [FromQuery] string? locale)
    {
        var historicalEvent = await db.HistoricalEvents.FirstOrDefaultAsync(e => e.Id == id);
        if (historicalEvent is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.EventNotFound));
        }

        var response = (await ApplyLocaleAsync([historicalEvent], locale)).Single();
        return Ok(ApiResponse.Ok(response));
    }

    /// <summary>新增事件骨幹——這個 API 的第一個真正落地的寫入端點，掛在 task 2.14 的
    /// <c>ApiWriteKeyMiddleware</c> 底下（POST 一律要求 <c>X-API-Key</c>）。</summary>
    [HttpPost("events")]
    public async Task<ActionResult<ApiResponse<HistoricalEventResponse>>> Create(CreateHistoricalEventRequest request)
    {
        // Id 是呼叫端指定的 slug，不是資料庫自動產生——DB 的主鍵約束本來就會擋重複，但那樣
        // 會直接炸成未分類的 500，這裡先手動查一次，回傳有意義的 409 而不是讓例外處理器接手。
        if (await db.HistoricalEvents.AnyAsync(e => e.Id == request.Id))
        {
            return Conflict(ApiResponse.Error(StatusCodes.Status409Conflict, ApiMessageCodes.EventIdAlreadyExists));
        }

        var startResult = edtfService.TryParse(request.StartEdtf);
        if (!startResult.IsValid)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.InvalidEdtf));
        }

        var endResult = edtfService.TryParse(request.EndEdtf);
        if (!endResult.IsValid)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.InvalidEdtf));
        }

        // 四捨五入到 3 位小數——跟 historical_events.start_decimal/end_decimal 的
        // numeric(8,3) 欄位精度對齊。不先在這裡對齊的話，這個方法建出來的回應物件會是
        // ToDecimalYear() 算出來的完整精度，但 SaveChangesAsync() 之後資料庫實際存的是
        // 四捨五入過的版本——同一筆資料，POST 當下回的值跟之後 GET 回來的值會對不起來
        // （已用真實容器驗證過這個落差，見 implementation plan 任務 2.10）。
        var startDecimal = Math.Round(startResult.Date!.Value.ToDecimalYear(), 3);
        var endDecimal = Math.Round(endResult.Date!.Value.ToDecimalYear(), 3);

        // task 2.10 明確要求的額外檢查：EdtfService.TryParse 只驗證單一字串本身的語法
        // 合法性，不驗證跨欄位邏輯，這裡補上「結束不能早於開始」，避免使用者填反開始/
        // 結束時間——憲法/PRD 沒有逐字講這條，但屬於基本資料完整性，不需要另外拍板。
        if (endDecimal < startDecimal)
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.EventEndBeforeStart));
        }

        if (request.ParentEventId is not null
            && !await db.HistoricalEvents.AnyAsync(e => e.Id == request.ParentEventId))
        {
            return BadRequest(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.ParentEventNotFound));
        }

        var entity = new HistoricalEvent
        {
            Id = request.Id,
            Name = request.Name,
            ParentEventId = request.ParentEventId,
            StartEdtf = request.StartEdtf,
            EndEdtf = request.EndEdtf,
            StartDecimal = startDecimal,
            EndDecimal = endDecimal,
            // 存進 jsonb 欄位前轉回原始文字——GetRawText() 保留呼叫端送來的原始格式，不是
            // 重新序列化 JsonElement 出一份新的（避免不必要的格式差異，例如欄位順序、空白）。
            Sections = request.Sections?.GetRawText(),
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        db.HistoricalEvents.Add(entity);
        await db.SaveChangesAsync();

        var response = (await ApplyLocaleAsync([entity], null)).Single();
        return CreatedAtAction(nameof(GetById), new { id = entity.Id },
            ApiResponse.Ok(response, ApiMessageCodes.CreateSuccess));
    }

    /// <summary>PRD Story 2 AC#3「互動清單」的離散事件那一半（持續性關係見
    /// <c>RegimeRelationsController</c>）——取得某政權跟其他政權之間，有文獻記錄的離散
    /// 互動事件（戰爭、禪讓等）。**「有記錄的互動」不是任意兩個政權剛好同時期存在**，
    /// schema 裡沒有一張通用的「事件參與者」關聯表，這裡合併兩個各自可靠但範圍不同的
    /// 資料來源，任一個成立就算：
    /// 1. **政權轉換事件**（<c>regime_transition_events</c>）：這個政權自己的起源/滅亡
    ///    事件（`regimes.predecessor_regime_id`/`destroyed_by_regime_id` 反查出另一方是
    ///    誰），或反過來——別的政權因為這個政權而轉換（這個政權是別人的 predecessor 或
    ///    destroyer）。只涵蓋「導致政權誕生/滅亡」的轉換性事件。
    /// 2. **多重視角敘事**（<c>historical_event_perspectives</c>）：同一個事件底下，這個
    ///    政權跟另一個政權都留下了各自的視角記錄，視為兩者在這個事件裡有互動——涵蓋一般
    ///    的戰役/事件（不限於轉換性事件），但受限於視角資料目前還很稀疏（見
    ///    implementation plan 任務 3.7 的補充說明），只有雙方都留下視角的事件才配對得
    ///    出來，不是「這個政權有視角就算」。
    ///
    /// **2026-08-31（使用者提案，task 3.12 後續調整）：`year` 改成選填**——原本這個
    /// 端點只服務「聚焦政權在目前這一年的互動」，`year` 必填；使用者提案把地圖 overlay
    /// 的互動記錄改成「這個政權全部已知事件，依時間排序，不拘泥於當年」，需要能查「不限
    /// 年份」的版本。省略 `year` 時兩個內部方法都跳過年份篩選，回傳這個政權全部已知
    /// 互動；帶 `year` 時維持原本語意不變（既有呼叫端，例如任何之後真的需要「只看這一年」
    /// 的用途，不受影響）。</summary>
    [HttpGet("regimes/{regimeId:guid}/events")]
    public async Task<ActionResult<ApiResponse<IEnumerable<RegimeEventInteractionResponse>>>> GetInteractionsByRegime(
        Guid regimeId, [FromQuery] int? year)
    {
        var regime = await db.Regimes.FirstOrDefaultAsync(r => r.Id == regimeId);
        if (regime is null)
        {
            return NotFound(ApiResponse.Error(StatusCodes.Status404NotFound, ApiMessageCodes.RegimeNotFound));
        }

        var interactions = new List<RegimeEventInteractionResponse>();
        await AddTransitionInteractionsAsync(interactions, regimeId, regime, year);
        await AddPerspectiveInteractionsAsync(interactions, regimeId, year);

        return Ok(ApiResponse.Ok<IEnumerable<RegimeEventInteractionResponse>>(interactions));
    }

    private async Task AddTransitionInteractionsAsync(
        List<RegimeEventInteractionResponse> interactions, Guid regimeId, Regime regime, int? year)
    {
        // 這個政權自己的轉換事件——另一方從 regimes 的傳承欄位反查（見類別註解，
        // regime_transition_events 本身只連轉換的一方，不會直接告訴我們另一方是誰）。
        var ownTransitionsQuery = db.RegimeTransitionEvents
            .Where(t => t.RegimeId == regimeId)
            .Join(db.HistoricalEvents, t => t.EventId, e => e.Id, (t, e) => new { t.TransitionKind, Event = e });
        if (year is not null)
        {
            ownTransitionsQuery = ownTransitionsQuery.Where(x => x.Event.StartDecimal < year + 1 && x.Event.EndDecimal >= year);
        }
        var ownTransitions = await ownTransitionsQuery.ToListAsync();

        foreach (var t in ownTransitions)
        {
            var otherRegimeId = t.TransitionKind == "origin" ? regime.PredecessorRegimeId : regime.DestroyedByRegimeId;
            if (otherRegimeId is null)
            {
                continue; // 有轉換事件記錄，但傳承欄位沒填另一方（理論上不該發生，資料不一致才會走到這）
            }
            interactions.Add(new RegimeEventInteractionResponse
            {
                EventId = t.Event.Id,
                EventName = t.Event.Name,
                OtherRegimeId = otherRegimeId.Value,
                StartEdtf = t.Event.StartEdtf,
                EndEdtf = t.Event.EndEdtf,
                StartDecimal = t.Event.StartDecimal,
                EndDecimal = t.Event.EndDecimal,
            });
        }

        // 反過來：其他政權因為這個政權而轉換（這個政權是別人的 predecessor 或
        // destroyer），從對方的 regime_transition_events 找出對應事件。
        var regimesCausedByThis = await db.Regimes
            .Where(r => r.PredecessorRegimeId == regimeId || r.DestroyedByRegimeId == regimeId)
            .ToListAsync();

        foreach (var other in regimesCausedByThis)
        {
            var kind = other.PredecessorRegimeId == regimeId ? "origin" : "destruction";
            var transitionEvent = await db.RegimeTransitionEvents
                .Where(t => t.RegimeId == other.Id && t.TransitionKind == kind)
                .Join(db.HistoricalEvents, t => t.EventId, e => e.Id, (t, e) => e)
                .FirstOrDefaultAsync();

            if (transitionEvent is null)
            {
                continue;
            }
            if (year is not null && (transitionEvent.StartDecimal >= year + 1 || transitionEvent.EndDecimal < year))
            {
                continue;
            }

            interactions.Add(new RegimeEventInteractionResponse
            {
                EventId = transitionEvent.Id,
                EventName = transitionEvent.Name,
                OtherRegimeId = other.Id,
                StartEdtf = transitionEvent.StartEdtf,
                EndEdtf = transitionEvent.EndEdtf,
                StartDecimal = transitionEvent.StartDecimal,
                EndDecimal = transitionEvent.EndDecimal,
            });
        }
    }

    private async Task AddPerspectiveInteractionsAsync(
        List<RegimeEventInteractionResponse> interactions, Guid regimeId, int? year)
    {
        var eventIdsWithOwnPerspective = await db.HistoricalEventPerspectives
            .Where(p => p.RegimeId == regimeId && p.EventId != null)
            .Select(p => p.EventId!)
            .ToListAsync();

        if (eventIdsWithOwnPerspective.Count == 0)
        {
            return;
        }

        // 同一批事件裡，其他政權（非自己、非 null）也留下視角的那些列——這是判斷「兩個
        // 政權在這個事件裡有互動」的依據，不是單方面有視角就算。
        var otherPerspectivesQuery = db.HistoricalEventPerspectives
            .Where(p => p.EventId != null && eventIdsWithOwnPerspective.Contains(p.EventId)
                && p.RegimeId != null && p.RegimeId != regimeId)
            .Join(db.HistoricalEvents, p => p.EventId, e => e.Id, (p, e) => new { Perspective = p, Event = e });
        if (year is not null)
        {
            otherPerspectivesQuery = otherPerspectivesQuery.Where(x => x.Event.StartDecimal < year + 1 && x.Event.EndDecimal >= year);
        }
        var otherPerspectives = await otherPerspectivesQuery.ToListAsync();

        foreach (var x in otherPerspectives)
        {
            interactions.Add(new RegimeEventInteractionResponse
            {
                EventId = x.Event.Id,
                EventName = x.Event.Name,
                OtherRegimeId = x.Perspective.RegimeId!.Value,
                StartEdtf = x.Event.StartEdtf,
                EndEdtf = x.Event.EndEdtf,
                StartDecimal = x.Event.StartDecimal,
                EndDecimal = x.Event.EndDecimal,
            });
        }
    }

    private async Task<List<HistoricalEventResponse>> ApplyLocaleAsync(List<HistoricalEvent> events, string? locale)
    {
        var translatedNames = new Dictionary<string, string>();

        if (!string.IsNullOrEmpty(locale))
        {
            var ids = events.Select(e => e.Id).ToList();
            translatedNames = await db.HistoricalEventTranslations
                .Where(t => ids.Contains(t.EventId) && t.Locale == locale)
                .ToDictionaryAsync(t => t.EventId, t => t.Name);
        }

        return events.Select(e => new HistoricalEventResponse
        {
            Id = e.Id,
            Name = translatedNames.TryGetValue(e.Id, out var translated) ? translated : e.Name,
            ParentEventId = e.ParentEventId,
            StartEdtf = e.StartEdtf,
            EndEdtf = e.EndEdtf,
            StartDecimal = e.StartDecimal,
            EndDecimal = e.EndDecimal,
            // JsonDocument 故意不 Dispose：RootElement 要活到框架序列化這個回應物件的當下
            // （在這個方法回傳之後才會發生），提早 Dispose 會讓 JsonElement 失效。是已知、
            // 可接受的取捨（只是延後歸還 pooled memory 給 GC 處理），不是忘記處理。
            Sections = e.Sections is null ? null : JsonDocument.Parse(e.Sections).RootElement,
            OriginPoint = e.OriginPoint,
            InfluenceArea = e.InfluenceArea,
            Routes = e.Routes,
        }).ToList();
    }
}
