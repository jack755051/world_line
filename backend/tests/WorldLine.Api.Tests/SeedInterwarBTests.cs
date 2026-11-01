using System.Net;
using System.Net.Http.Json;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace WorldLine.Api.Tests;

/// <summary>
/// 先重播 WW1 第一、二批與兩次大戰之間 A 批，再依序重播 B 批 data/seed/interwar/batch-b/requests/B1..B3（DRAFT）到測試容器（不是 appdb_ww2）。
/// 前置批次以外的政權、來源、事件先建替身。B1 撤回 A 批迄於 1924-01-01 的 34 筆主權紀錄與魯爾佔領歸屬再延長重送（先撤後增），這裡一併驗證；
/// B2 撤回的開發庫既有西班牙共和國紀錄（SOV_R2860484）在測試容器裡不存在，跳過該撤回請求。
/// 檢查：全部通過 API 驗證、截圖日（1926-01-01、1935-03-01、1937-06-01、1938-03-13）的政權與層級、佔領歸屬、待查證事件沒有引用、衝突起訖。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class SeedInterwarBTests(PostGisFixture fx)
{
    private static readonly string[] Ww1PriorRegimes = ["REGIME_IT", "REGIME_RO", "REGIME_GR", "REGIME_BE", "REGIME_DK", "REGIME_NO", "REGIME_SE", "REGIME_BG", "REGIME_FR3", "REGIME_IT_AEGEAN", "REGIME_PT",
        "REGIME_LU", "REGIME_EE", "REGIME_FI", "REGIME_CS", "REGIME_PL", "REGIME_US"];
    // A 批另外引用的開發庫既有政權（WW1 兩批沒有建）
    private static readonly string[] InterwarPriorRegimes = ["REGIME_DANZIG", "REGIME_DE", "REGIME_HU", "REGIME_LT", "REGIME_LV", "REGIME_SU", "REGIME_TR", "REGIME_UK"];
    // B 批另外引用的開發庫既有政權與事件
    private static readonly string[] InterwarBPriorRegimes = ["REGIME_ES_REP", "REGIME_YU", "REGIME_IE", "REGIME_AL", "REGIME_JP"];
    private static readonly (string Ph, string Date)[] InterwarBPriorEvents = [("EV_SPAIN_1939", "1939-04-01"), ("EV_HATAY", "1939-06-23")];

    private static string SeedRoot()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "compose.yaml"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return Path.Combine(dir!.FullName, "data", "seed");
    }

    private static async Task<Dictionary<string, JsonNode>> Geoms(string file)
    {
        var geoms = new Dictionary<string, JsonNode>();
        foreach (var f in JsonNode.Parse(await File.ReadAllTextAsync(file))!["features"]!.AsArray())
            geoms[f!["id"]!.ToJsonString().Trim('"')] = f["geometry"]!;
        return geoms;
    }

    private static async Task ReplayDirAsync(ApiTestKit k, string dir, Dictionary<string, JsonNode> geoms, Dictionary<string, string> ids, Func<string, bool> skip)
    {
        foreach (var path in Directory.GetFiles(dir, "*.json").Order(StringComparer.Ordinal))
        {
            var name = Path.GetFileName(path);
            if (skip(name)) continue;
            var req = JsonNode.Parse(await File.ReadAllTextAsync(path))!.AsObject();
            var body = req["body"]!.AsObject();
            if (body["slug"] is not null) body["slug"] = $"{body["slug"]}-{k.Tag}";
            if (req["_geometryFrom"] is { } g) body["geometry"] = geoms[g.ToJsonString().Trim('"')].DeepClone();
            string Fill(string s) => Regex.Replace(s, @"\{\{(\w+)\}\}", m => ids.TryGetValue(m.Groups[1].Value, out var v) ? v : throw new Exception($"{name}: 缺少 {m.Groups[1].Value}"));
            var post = Fill((string)req["_post"]!);
            var res = await k.W.PostAsync(post, new StringContent(Fill(body.ToJsonString()), Encoding.UTF8, "application/json"));
            if (post.EndsWith("/retraction"))
            {
                try { await ApiTestKit.Expect(res, HttpStatusCode.OK); }
                catch (Exception e) { throw new Exception($"{name}: {e.Message}", e); }
                continue;
            }
            JsonElement data;
            try { data = (await ApiTestKit.Expect(res, HttpStatusCode.Created)).GetProperty("data"); }
            catch (Exception e) { throw new Exception($"{name}: {e.Message}", e); }
            ids[(string)req["_placeholder"]!] = data.GetProperty("id").GetString()!;
        }
    }

    private static async Task Stub(ApiTestKit k, Dictionary<string, string> ids, string ph)
    {
        var slug = $"{ph.ToLowerInvariant().Replace('_', '-')}-{k.Tag}";
        ids[ph] = (await k.Id(await k.W.PostAsJsonAsync("/api/v1/regimes", new
        {
            slug,
            names = new[] { new { nameKind = "self", originalText = ph, originalLang = "en", display = new Dictionary<string, string> { ["zh-Hant"] = ph, ["en"] = ph }, isPrimary = true } },
        }))).ToString();
    }

    private static async Task<Dictionary<string, string>> ReplayAsync(ApiTestKit k)
    {
        var root = SeedRoot();
        var ids = new Dictionary<string, string>();
        foreach (var ph in Ww1PriorRegimes) await Stub(k, ids, ph);
        ids["SRC_NE_LAND"] = (await k.Source("dataset", "cc0", $"Natural Earth {k.Tag}")).ToString();
        ids["SRC_OHM_US"] = (await k.Source("dataset", "cc0", $"OHM US {k.Tag}")).ToString();
        var b1 = Path.Combine(root, "ww1", "balkans-1908-1914");
        await ReplayDirAsync(k, Path.Combine(b1, "requests"), await Geoms(Path.Combine(b1, "ww1-1908-1914-derived.geojson")), ids,
            name => name.StartsWith("04-retract-") || name.EndsWith("sov_pt_republic.json"));
        var b2 = Path.Combine(root, "ww1", "war-1914-1918");
        var g2 = await Geoms(Path.Combine(b2, "ww1-1914-1918-derived.geojson"));
        foreach (var sub in new[] { "sub1", "sub2", "sub3" })
            await ReplayDirAsync(k, Path.Combine(b2, "requests", sub), g2, ids, _ => false);
        foreach (var ph in InterwarPriorRegimes) await Stub(k, ids, ph);
        var a = Path.Combine(root, "interwar", "batch-a");
        var ga = await Geoms(Path.Combine(a, "interwar-a-derived.geojson"));
        foreach (var sub in new[] { "A1", "A2", "A3" })
            await ReplayDirAsync(k, Path.Combine(a, "requests", sub), ga, ids, _ => false);
        var aIds = new Dictionary<string, string>(ids);
        foreach (var ph in InterwarBPriorRegimes) await Stub(k, ids, ph);
        ids["SRC_OHM"] = (await k.Source("dataset", "cc0", $"OHM {k.Tag}")).ToString();
        foreach (var (ph, date) in InterwarBPriorEvents)
        {
            var end = DateOnly.Parse(date).AddDays(1).ToString("yyyy-MM-dd");
            ids[ph] = (await k.Id(await k.W.PostAsJsonAsync("/api/v1/events", new
            {
                eventKind = "political", occurred = new { start = date, end }, datePrecision = "day",
                summary = new Dictionary<string, string> { ["zh-Hant"] = ph, ["en"] = ph },
                participants = new[] { new { regimeId = ids["REGIME_ES_REP"], role = "signatory" } }, citations = Array.Empty<object>(),
            }))).ToString();
        }
        var b = Path.Combine(root, "interwar", "batch-b");
        var gb = await Geoms(Path.Combine(b, "interwar-b-derived.geojson"));
        foreach (var sub in new[] { "B1", "B2", "B3" })
            await ReplayDirAsync(k, Path.Combine(b, "requests", sub), gb, ids, name => name.EndsWith("04-retract-01-sov_r2860484.json"));
        ids["__A_SOV_SAAR"] = aIds["SOV_SAAR"];
        return ids;
    }

    [Fact]
    public async Task Interwar_batch_b_extends_batch_a_and_maps_regimes_and_occupations_on_screenshot_dates()
    {
        var k = new ApiTestKit(fx);
        var ids = await ReplayAsync(k);

        async Task<Dictionary<string, JsonElement>> On(string date)
        {
            var data = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/sovereignty?date={date}"), HttpStatusCode.OK)).GetProperty("data");
            return data.GetProperty("featureCollection").GetProperty("features").EnumerateArray()
                .Select(f => f.GetProperty("properties"))
                .Where(p => p.GetProperty("regimeSlug").GetString()!.EndsWith(k.Tag))
                .ToDictionary(p => p.GetProperty("recordId").GetString()!);
        }
        async Task<string> Conflicts(string date) => await (await k.R.GetAsync($"/api/v1/conflicts?date={date}")).Content.ReadAsStringAsync();

        // 先撤後增：A 批薩爾紀錄（迄 1924-01-01）撤回，延長紀錄從原起日接手
        var d0 = await On("1923-06-01");
        Assert.DoesNotContain(ids["__A_SOV_SAAR"], d0.Keys);
        Assert.Contains(ids["SOV_SAAR_X"], d0.Keys);
        Assert.Contains(ids["SOV_DE_H_2_X_1"], d0.Keys);
        Assert.Contains(ids["SOV_SU_B"], (await On("1925-06-01")).Keys);

        // 1926-01-01：洛迦諾後、科隆區撤離前；萊茵蘭三區、薩爾；里夫戰爭進行中
        var d1 = await On("1926-01-01");
        Assert.Contains(ids["SOV_DE_H_2_X_3"], d1.Keys);
        Assert.Equal("not_sovereign", d1[ids["SOV_RHZ1_2"]].GetProperty("layerStatus").GetString());
        Assert.True(d1[ids["SOV_RHZ1_2"]].GetProperty("occupation").GetProperty("coOccupied").GetBoolean());
        Assert.Equal("military_administration", d1[ids["SOV_RHZ2"]].GetProperty("occupation").GetProperty("controlKind").GetString());
        Assert.Contains(ids["SOV_RHZ3"], d1.Keys);
        Assert.Contains(ids["SOV_SAAR_X"], d1.Keys);
        Assert.DoesNotContain(ids["SOV_RUHR_X"], d1.Keys);
        Assert.Contains(ids["SOV_AL_REP_A"], d1.Keys);
        Assert.Contains(ids["SOV_GR_REP_B"], d1.Keys);
        Assert.Equal("pending", d1[ids["SOV_DE_H_2_X_3"]].GetProperty("startEvent").GetProperty("verification").GetString());
        Assert.Equal(0, d1[ids["SOV_DE_H_2_X_3"]].GetProperty("startEvent").GetProperty("citations").GetArrayLength());
        var c1 = await Conflicts("1926-01-01");
        Assert.Contains(ids["CF_ES_RIF"], c1);
        Assert.Contains(ids["CF_FR_RIF"], c1);
        Assert.DoesNotContain(ids["CF_ES_RIF"], await Conflicts("1926-06-01"));

        // 1935-03-01：薩爾回歸；義屬利比亞、伊拉克王國、敘利亞共和國；萊茵蘭佔領已結束
        var d2 = await On("1935-03-01");
        Assert.Contains(ids["SOV_DE_I"], d2.Keys);
        Assert.DoesNotContain(ids["SOV_SAAR_X"], d2.Keys);
        Assert.DoesNotContain(ids["SOV_RHZ3"], d2.Keys);
        Assert.Contains(ids["SOV_LY_IT"], d2.Keys);
        Assert.Contains(ids["SOV_IQ_K"], d2.Keys);
        Assert.Equal("not_sovereign", d2[ids["SOV_SY_REP_A"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_ES_REP_B_1"], d2.Keys);
        Assert.Equal("verified", d2[ids["SOV_ES_REP_B_1"]].GetProperty("startEvent").GetProperty("verification").GetString());

        // 1937-06-01：西班牙內戰（畢爾包陷落前）；國民軍區非主權、共和國扣掉國民軍區
        var d3 = await On("1937-06-01");
        Assert.Equal("not_sovereign", d3[ids["SOV_ESNAT_3"]].GetProperty("layerStatus").GetString());
        Assert.Contains(ids["SOV_ES_REP_B_4"], d3.Keys);
        Assert.Contains(ids["SOV_IFS_X"], d3.Keys);
        Assert.Contains(ids["CF_ES_CW"], await Conflicts("1937-06-01"));
        Assert.DoesNotContain(ids["CF_ES_CW"], await Conflicts("1936-07-01"));

        // 1938-03-13（接二戰資料）：北方戰線已結束；哈塔伊 1938-09-02 起
        var d4 = await On("1938-03-13");
        Assert.Contains(ids["SOV_ESNAT_6"], d4.Keys);
        Assert.Contains(ids["SOV_ES_REP_B_7"], d4.Keys);
        Assert.DoesNotContain(ids["SOV_HATAY"], d4.Keys);
        Assert.Equal("not_sovereign", (await On("1938-10-01"))[ids["SOV_HATAY"]].GetProperty("layerStatus").GetString());
    }
}
