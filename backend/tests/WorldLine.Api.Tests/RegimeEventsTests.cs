using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests;

/// <summary>
/// 政權相關事件（政權面板「事件」時間線，2026-10-31 試驗）：參與方事件＋衝突／國界紀錄的起訖事件，依日期排序；
/// 沒有引用＝待查證；不存在的政權 404。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class RegimeEventsTests(PostGisFixture fx)
{
    private static async Task<Guid> Event(ApiTestKit k, string kind, string start, object[] participants, params object[] citations)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = kind,
            occurred = new { start, end = DateOnly.Parse(start).AddDays(1).ToString("yyyy-MM-dd") },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = $"{kind} {start}", ["en"] = $"{kind} {start}" },
            participants,
            citations,
        });
        return await k.Id(res);
    }

    [Fact]
    public async Task Lists_participant_and_conflict_events_by_date_with_roles_and_verification()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("reich");
        var pl = await k.Regime("polska");
        var other = await k.Regime("other");
        var frus = await k.Source(kind: "official_record", title: "FRUS 1939 I");
        var treaty = await Event(k, "treaty", "1939-09-28", [new { regimeId = de, role = "signatory" }],
            new { sourceId = frus, locator = "Doc. 514, p. 495", evidenceNote = "boundary treaty" });
        var war = await Event(k, "war", "1939-09-01", []);
        var unrelated = await Event(k, "political", "1939-09-10", [new { regimeId = other, role = "other" }]);
        var res = await k.W.PostAsJsonAsync("/api/v1/conflict-records", new
        {
            regimeAId = de, regimeBId = pl, startEventId = war, endEventId = (Guid?)null,
            location = new { type = "Point", coordinates = new[] { 18.5, 51.5 } }, locationMethod = "共同邊界中點",
        });
        await k.Id(res);

        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{de}/events"), HttpStatusCode.OK)).GetProperty("data");
        var ids = data.EnumerateArray().Select(e => e.GetProperty("id").GetGuid()).ToList();
        Assert.Equal([war, treaty], ids); // 依日期排序；無關事件不列
        Assert.DoesNotContain(unrelated, ids);
        var w = data[0];
        Assert.Equal("pending", w.GetProperty("verification").GetString());
        Assert.Equal("conflict_start", w.GetProperty("roles")[0].GetString());
        var t = data[1];
        Assert.Equal("verified", t.GetProperty("verification").GetString());
        Assert.Equal("signatory", t.GetProperty("roles")[0].GetString());
        Assert.Equal("Doc. 514, p. 495", t.GetProperty("citations")[0].GetProperty("locator").GetString());
        Assert.Equal("1939-09-28", t.GetProperty("occurred").GetProperty("start").GetString());

        // 衝突另一方也看得到開戰事件
        var plData = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{pl}/events"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(war, plData[0].GetProperty("id").GetGuid());
    }

    [Fact]
    public async Task Unknown_regime_is_404()
    {
        var k = new ApiTestKit(fx);
        await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{Guid.NewGuid()}/events"), HttpStatusCode.NotFound);
    }
}
