using System.Net;
using System.Net.Http.Json;
using System.Text.Json.Nodes;

namespace WorldLine.Api.Tests;

/// <summary>
/// GET /timeline/change-points 的 controlPoints（移植自 992baba 的 ChangeDatesTests）：前端依控制區變動點區段快取 /control。
/// 區段內任兩天的 /control 回應必須除了 date 以外完全相同；漏掉任何變動點，前端就會沿用錯誤的資料。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class ControlChangePointsTests(PostGisFixture fx)
{
    private static async Task<(List<string> Points, List<string> Control)> ChangePoints(ApiTestKit k)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync("/api/v1/timeline/change-points"), HttpStatusCode.OK)).GetProperty("data");
        List<string> L(string n) => data.GetProperty(n).EnumerateArray().Select(x => x.GetString()!).ToList();
        return (L("points"), L("controlPoints"));
    }

    private static async Task<string> WithoutDate(ApiTestKit k, string path, string date)
    {
        var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/{path}?date={date}"), HttpStatusCode.OK)).GetProperty("data");
        var obj = JsonNode.Parse(data.GetRawText())!.AsObject();
        Assert.Equal(date, obj["date"]!.GetValue<string>());
        obj.Remove("date");
        return obj.ToJsonString();
    }

    [Fact]
    public async Task Control_points_cover_control_records_snapshots_and_alignments_and_dates_inside_a_segment_get_identical_control_responses()
    {
        var k = new ApiTestKit(fx);
        var a = await k.Regime("ccp-a");
        var b = await k.Regime("ccp-b");
        var atlas = await k.Source();
        var frus = await k.Source(kind: "official_record", title: "FRUS 1890");
        // 陣營切片：1890-05-01 起（迄日無界）
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/regimes/{a}/alignments", new
        {
            camp = "axis", validPeriod = new { start = "1890-05-01" },
            citations = new[] { new { sourceId = frus, locator = "p. 1", role = "primary", evidenceNote = "測試" } },
        }), HttpStatusCode.Created);
        // 控制紀錄 [1890-04-02, 1890-06-15)，快照 1890-04-10（as_of 當天與隔天都是變動點）
        var th = await k.Theater("ccp");
        var snap = await k.Snapshot(th, "1890-04-10");
        await ApiTestKit.Expect(await k.PostControl(ApiTestKit.ControlBody(b, snap, atlas, "1890-04-02", "1890-06-15", geometry: ApiTestKit.Square(124, -40, 2))), HttpStatusCode.Created);

        var (points, control) = await ChangePoints(k);
        Assert.Equal(control.Order(StringComparer.Ordinal), control);
        Assert.Equal(control.Distinct().Count(), control.Count);
        foreach (var d in new[] { "1890-05-01", "1890-04-02", "1890-06-15", "1890-04-10", "1890-04-11" })
            Assert.Contains(d, control);
        Assert.Contains("1890-05-01", points); // 陣營也影響主權圖層

        // 控制區變動點區段內（1890-04-11 ～ 下一個變動點的前一天）/control 回應除了 date 以外相同
        var start = "1890-04-11";
        var next = control.First(d => string.CompareOrdinal(d, start) > 0);
        var last = DateOnly.Parse(next).AddDays(-1).ToString("yyyy-MM-dd");
        Assert.NotEqual(start, last);
        Assert.Equal(await WithoutDate(k, "control", start), await WithoutDate(k, "control", last));
        // 跨過快照日：戰區狀態改變
        Assert.NotEqual(await WithoutDate(k, "control", "1890-04-09"), await WithoutDate(k, "control", "1890-04-10"));
    }
}
