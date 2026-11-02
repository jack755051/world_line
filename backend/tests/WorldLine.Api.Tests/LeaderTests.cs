using System.Net;
using System.Net.Http.Json;

namespace WorldLine.Api.Tests;

/// <summary>
/// 領導人紀錄（leader_records；2026-11-03 試驗，AI 提案・待拍板）：
/// 每筆記政權在某期間的在任領導人；半開區間 [validFrom, validTo)；撤回走 I5。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class LeaderTests(PostGisFixture fx)
{
    private async Task<System.Guid> CreateLeader(
        ApiTestKit k, System.Guid regimeId,
        string name, string role,
        string validFrom, string? validTo = null,
        string? nameZh = null, string? title = null,
        string? source = null, bool verified = true) =>
        await k.Id(await k.W.PostAsJsonAsync("/api/v1/leader-records", new
        {
            regimeId,
            name,
            nameZh,
            role,
            title,
            validFrom,
            validTo,
            source = source ?? "Encyclopædia Britannica",
            verified,
        }));

    private static async Task<System.Collections.Generic.List<System.Text.Json.JsonElement>> FeaturesOn(
        ApiTestKit k, string date, string? regime = null)
    {
        var url = $"/api/v1/leaders?date={date}";
        if (regime is not null) url += $"&regime={regime}";
        return (await ApiTestKit.Expect(await k.R.GetAsync(url), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("features")
            .EnumerateArray().ToList();
    }

    [Fact]
    public async Task Leader_shown_within_valid_period_and_hidden_outside()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("de-leader-test");

        var id = await CreateLeader(k, de, "Adolf Hitler", "head_of_government",
            "1933-01-30", "1945-05-08",
            nameZh: "阿道夫·希特勒", title: "Reichskanzler",
            source: "Encyclopædia Britannica: Hitler");

        // 期間內可見
        var features = await FeaturesOn(k, "1939-09-01");
        Assert.Contains(features, f => f.GetProperty("recordId").GetGuid() == id);

        // 期間前看不到
        var before = await FeaturesOn(k, "1933-01-29");
        Assert.DoesNotContain(before, f => f.GetProperty("recordId").GetGuid() == id);

        // 半開區間：termination date 當天（訖日）不可見
        var after = await FeaturesOn(k, "1945-05-08");
        Assert.DoesNotContain(after, f => f.GetProperty("recordId").GetGuid() == id);
    }

    [Fact]
    public async Task Leader_validTo_boundary_is_exclusive()
    {
        var k = new ApiTestKit(fx);
        var jp = await k.Regime("jp-leader-test");

        var id = await CreateLeader(k, jp, "Hideki Tojo", "head_of_government",
            "1941-10-18", "1944-07-22",
            source: "Encyclopædia Britannica: Tojo");

        // 前一天仍可見
        var before = await FeaturesOn(k, "1944-07-21");
        Assert.Contains(before, f => f.GetProperty("recordId").GetGuid() == id);

        // 訖日本身不可見（半開 [start, end)）
        var on = await FeaturesOn(k, "1944-07-22");
        Assert.DoesNotContain(on, f => f.GetProperty("recordId").GetGuid() == id);
    }

    [Fact]
    public async Task Leader_open_end_visible_indefinitely()
    {
        var k = new ApiTestKit(fx);
        var it = await k.Regime("it-leader-test");

        var id = await CreateLeader(k, it, "Benito Mussolini", "head_of_government",
            "1922-10-31", null,
            source: "Encyclopædia Britannica: Mussolini");

        // 開放迄日：遠未來也可見
        var features = await FeaturesOn(k, "1943-07-01");
        Assert.Contains(features, f => f.GetProperty("recordId").GetGuid() == id);
    }

    [Fact]
    public async Task Regime_filter_returns_only_matching_leaders()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("de-filter-test");
        var fr = await k.Regime("fr-filter-test");

        var deId = await CreateLeader(k, de, "Paul von Hindenburg", "head_of_state",
            "1925-05-12", "1934-08-02", source: "Encyclopædia Britannica: Hindenburg");
        var frId = await CreateLeader(k, fr, "Albert Lebrun", "head_of_state",
            "1932-05-10", "1940-07-11", source: "Encyclopædia Britannica: Lebrun");

        // regime 篩選只回傳 de 的
        var deSlug = $"de-filter-test-{k.Tag}";
        var features = await FeaturesOn(k, "1933-01-30", deSlug);
        Assert.Contains(features, f => f.GetProperty("recordId").GetGuid() == deId);
        Assert.DoesNotContain(features, f => f.GetProperty("recordId").GetGuid() == frId);
    }

    [Fact]
    public async Task Empty_result_for_date_with_no_leaders()
    {
        var k = new ApiTestKit(fx);
        // 查詢遠古日期，不應有任何領導人
        var features = await FeaturesOn(k, "1800-01-01");
        Assert.Empty(features);
    }

    [Fact]
    public async Task Leader_feature_has_correct_properties()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("de-props-test");

        var id = await CreateLeader(k, de, "Paul von Hindenburg", "head_of_state",
            "1925-05-12", "1934-08-02",
            nameZh: null, title: "Reichspräsident",
            source: "Encyclopædia Britannica: Hindenburg", verified: true);

        var features = await FeaturesOn(k, "1933-01-30");
        var f = features.First(x => x.GetProperty("recordId").GetGuid() == id);

        Assert.Equal("Paul von Hindenburg", f.GetProperty("name").GetString());
        Assert.Equal("head_of_state", f.GetProperty("role").GetString());
        Assert.Equal("Reichspräsident", f.GetProperty("title").GetString());
        Assert.True(f.GetProperty("verified").GetBoolean());
        Assert.Equal("1925-05-12", f.GetProperty("validPeriod").GetProperty("start").GetString());
        Assert.Equal("1934-08-02", f.GetProperty("validPeriod").GetProperty("end").GetString());
    }
}
