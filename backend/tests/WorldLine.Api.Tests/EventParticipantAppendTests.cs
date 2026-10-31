using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 事後追加事件參與方（方案 A，Tai 2026-10-31）：POST /api/v1/events/{id}/participants。
/// 只新增（原參與方、引用不動）、理由必填、重複 409、事件或政權不存在 404／400；追加的列仍不可改、不可刪（I5）。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class EventParticipantAppendTests(PostGisFixture fx)
{
    private static async Task<Guid> Event(ApiTestKit k, Guid belligerent) =>
        await k.Id(await k.W.PostAsJsonAsync("/api/v1/events", new
        {
            eventKind = "war",
            occurred = new { start = "1942-11-08", end = "1942-11-09" },
            datePrecision = "day",
            summary = new Dictionary<string, string> { ["zh-Hant"] = "火炬行動", ["en"] = "Operation Torch" },
            participants = new[] { new { regimeId = belligerent, role = "belligerent" } },
        }));

    private static Task<HttpResponseMessage> Append(ApiTestKit k, Guid ev, Guid? regime, string? role, bool note = true) =>
        k.W.PostAsJsonAsync($"/api/v1/events/{ev}/participants", new
        {
            regimeId = regime, role,
            note = note ? new Dictionary<string, string> { ["zh-Hant"] = "美軍為登陸主力（FRUS 1942 II）", ["en"] = "US forces led the landings" } : null,
        });

    [Fact]
    public async Task Appends_participant_keeps_existing_ones_and_records_reason()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk");
        var us = await k.Regime("us");
        var ev = await Event(k, uk);
        var body = await ApiTestKit.Expect(await Append(k, ev, us, "belligerent"), HttpStatusCode.Created);
        var parts = body.GetProperty("data").GetProperty("participants").EnumerateArray().ToList();
        Assert.Equal(2, parts.Count);
        var orig = parts.Single(p => p.GetProperty("regimeId").GetGuid() == uk);
        Assert.Equal(JsonValueKind.Null, orig.GetProperty("addedAt").ValueKind);
        var added = parts.Single(p => p.GetProperty("regimeId").GetGuid() == us);
        Assert.Equal("belligerent", added.GetProperty("role").GetString());
        Assert.NotEqual(JsonValueKind.Null, added.GetProperty("addedAt").ValueKind);
        Assert.Contains("FRUS", added.GetProperty("additionNote").GetProperty("zh-Hant").GetString());

        // 政權事件清單也看得到（參與方角色）
        var list = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{us}/events"), HttpStatusCode.OK)).GetProperty("data");
        var item = list.EnumerateArray().Single(e => e.GetProperty("id").GetGuid() == ev);
        var adds = item.GetProperty("additions").EnumerateArray().ToList();
        var add = Assert.Single(adds);
        Assert.Equal("belligerent", add.GetProperty("role").GetString());
        Assert.Contains("FRUS", add.GetProperty("note").GetProperty("zh-Hant").GetString());
        // 隨事件寫入的參與方：沒有追加紀錄
        var ukList = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/regimes/{uk}/events"), HttpStatusCode.OK)).GetProperty("data");
        var ukItem = ukList.EnumerateArray().Single(e => e.GetProperty("id").GetGuid() == ev);
        Assert.True(!ukItem.TryGetProperty("additions", out var ua) || ua.ValueKind == JsonValueKind.Null);
    }

    [Fact]
    public async Task Rejects_duplicate_unknown_and_missing_reason()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk");
        var us = await k.Regime("us");
        var ev = await Event(k, uk);
        await ApiTestKit.Expect(await Append(k, ev, uk, "belligerent"), HttpStatusCode.Conflict);
        await ApiTestKit.Expect(await Append(k, Guid.CreateVersion7(), us, "belligerent"), HttpStatusCode.NotFound);
        await ApiTestKit.Expect(await Append(k, ev, Guid.CreateVersion7(), "belligerent"), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Append(k, ev, us, "general"), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await Append(k, ev, us, "belligerent", note: false), HttpStatusCode.BadRequest);
        // 同一政權不同角色可以
        await ApiTestKit.Expect(await Append(k, ev, us, "signatory"), HttpStatusCode.Created);
        await ApiTestKit.Expect(await Append(k, ev, us, "signatory"), HttpStatusCode.Conflict);
    }

    [Fact]
    public async Task Appended_rows_are_still_immutable()
    {
        var k = new ApiTestKit(fx);
        var uk = await k.Regime("uk");
        var us = await k.Regime("us");
        var ev = await Event(k, uk);
        await ApiTestKit.Expect(await Append(k, ev, us, "belligerent"), HttpStatusCode.Created);
        await using var conn = new NpgsqlConnection(fx.ConnectionString);
        await conn.OpenAsync();
        await using var upd = new NpgsqlCommand($"UPDATE event_participants SET addition_note = '{{}}'::jsonb WHERE event_id = '{ev}' AND regime_id = '{us}'", conn);
        await Assert.ThrowsAsync<PostgresException>(() => upd.ExecuteNonQueryAsync());
        await using var del = new NpgsqlCommand($"DELETE FROM event_participants WHERE event_id = '{ev}'", conn);
        await Assert.ThrowsAsync<PostgresException>(() => del.ExecuteNonQueryAsync());
    }
}
