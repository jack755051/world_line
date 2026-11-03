using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

namespace WorldLine.Api.Tests;

/// <summary>
/// 領導人生平（leader_bios；2026-11-03 試驗，AI 提案・待拍板）：
/// 一人一筆生平，多任期共用；POST /leader-bios、GET /leader-bios/{id}、
/// PATCH /leader-records/{id}/person 連結任期。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class LeaderBioTests(PostGisFixture fx)
{
    private async Task<(Guid BioId, JsonElement Body)> CreateBio(
        ApiTestKit k,
        string name,
        string? nameZh = null,
        string? birthDate = null,
        string? birthDatePrecision = null,
        string? deathDate = null,
        bool isTest = true,
        object? summary = null)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-bios", new
        {
            name,
            nameZh,
            birthDate,
            birthDatePrecision,
            deathDate,
            summary = summary ?? new Dictionary<string, string> { ["zh-Hant"] = "【測試資料】摘要", ["en"] = "[Test] summary" },
            isTest,
        });
        var body = await ApiTestKit.Expect(res, HttpStatusCode.Created);
        return (body.GetProperty("data").GetProperty("id").GetGuid(), body);
    }

    private async Task<Guid> CreateLeader(ApiTestKit k, Guid regimeId, string name, string role,
        string validFrom, string? validTo = null, Guid? personId = null)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-records", new
        {
            regimeId,
            name,
            role,
            validFrom,
            validTo,
            personId,
            source = "Encyclopædia Britannica",
            verified = true,
        });
        return await k.Id(res);
    }

    [Fact]
    public async Task CreateBio_returns_201_with_correct_fields()
    {
        var k = new ApiTestKit(fx);

        var (bioId, body) = await CreateBio(k,
            name: "Adolf Hitler",
            nameZh: "阿道夫·希特勒",
            birthDate: "1889-04-20",
            birthDatePrecision: "day",
            deathDate: "1945-04-30",
            isTest: true);

        var data = body.GetProperty("data");
        Assert.Equal("Adolf Hitler", data.GetProperty("name").GetString());
        Assert.Equal("阿道夫·希特勒", data.GetProperty("nameZh").GetString());
        Assert.Equal("1889-04-20", data.GetProperty("birthDate").GetString());
        Assert.Equal("day", data.GetProperty("birthDatePrecision").GetString());
        Assert.Equal("1945-04-30", data.GetProperty("deathDate").GetString());
        Assert.True(data.GetProperty("isTest").GetBoolean());
        Assert.NotEqual(Guid.Empty, bioId);
    }

    [Fact]
    public async Task GetBio_returns_200_with_full_data()
    {
        var k = new ApiTestKit(fx);

        var (bioId, _) = await CreateBio(k, "Winston Churchill", nameZh: "溫斯頓·邱吉爾",
            birthDate: "1874-11-30", deathDate: "1965-01-24");

        var res = await k.R.GetAsync($"/api/v1/leader-bios/{bioId}");
        var body = await ApiTestKit.Expect(res, HttpStatusCode.OK);
        var data = body.GetProperty("data");

        Assert.Equal("Winston Churchill", data.GetProperty("name").GetString());
        Assert.Equal("溫斯頓·邱吉爾", data.GetProperty("nameZh").GetString());
        Assert.Equal(bioId, data.GetProperty("id").GetGuid());
    }

    [Fact]
    public async Task GetBio_returns_404_for_unknown_id()
    {
        var k = new ApiTestKit(fx);
        var res = await k.R.GetAsync($"/api/v1/leader-bios/{Guid.NewGuid()}");
        await ApiTestKit.Expect(res, HttpStatusCode.NotFound);
    }

    [Fact]
    public async Task CreateLeaderRecord_with_personId_links_bio()
    {
        var k = new ApiTestKit(fx);
        var de = await k.Regime("de-bio-link-test");
        var (bioId, _) = await CreateBio(k, "Adolf Hitler");

        var recordId = await CreateLeader(k, de, "Adolf Hitler", "head_of_government",
            "1933-01-30", "1945-05-08", personId: bioId);

        // GET /leaders should return personId and bio summary
        var res = await k.R.GetAsync("/api/v1/leaders?date=1939-09-01");
        var body = await ApiTestKit.Expect(res, HttpStatusCode.OK);
        var features = body.GetProperty("data").GetProperty("features").EnumerateArray().ToList();
        var f = features.FirstOrDefault(x => x.GetProperty("recordId").GetGuid() == recordId);

        Assert.True(f.ValueKind != JsonValueKind.Undefined, "feature not found");
        Assert.Equal(bioId, f.GetProperty("personId").GetGuid());
        Assert.Equal(bioId, f.GetProperty("bio").GetProperty("id").GetGuid());
        Assert.Equal("Adolf Hitler", f.GetProperty("bio").GetProperty("name").GetString());
    }

    [Fact]
    public async Task PatchPerson_links_existing_record_to_bio()
    {
        var k = new ApiTestKit(fx);
        var gb = await k.Regime("gb-bio-patch-test");

        // 建立不帶 personId 的任期紀錄
        var recordId = await CreateLeader(k, gb, "Winston Churchill", "head_of_government",
            "1940-05-10");

        // 建立生平
        var (bioId, _) = await CreateBio(k, "Winston Churchill");

        // 連結
        var patchRes = await k.W.PatchAsJsonAsync($"/api/v1/leader-records/{recordId}/person",
            new { personId = bioId });
        var patchBody = await ApiTestKit.Expect(patchRes, HttpStatusCode.OK);
        Assert.Equal(bioId, patchBody.GetProperty("data").GetProperty("personId").GetGuid());

        // 查詢確認 bio 出現在回應中
        var res = await k.R.GetAsync("/api/v1/leaders?date=1943-01-01");
        var body = await ApiTestKit.Expect(res, HttpStatusCode.OK);
        var features = body.GetProperty("data").GetProperty("features").EnumerateArray().ToList();
        var f = features.FirstOrDefault(x => x.GetProperty("recordId").GetGuid() == recordId);
        Assert.True(f.ValueKind != JsonValueKind.Undefined);
        Assert.Equal(bioId, f.GetProperty("bio").GetProperty("id").GetGuid());
    }

    [Fact]
    public async Task PatchPerson_with_null_unlinks_bio()
    {
        var k = new ApiTestKit(fx);
        var us = await k.Regime("us-bio-unlink-test");
        var (bioId, _) = await CreateBio(k, "Franklin Roosevelt");
        var recordId = await CreateLeader(k, us, "Franklin Roosevelt", "head_of_state",
            "1933-03-04", personId: bioId);

        // 解除連結
        var patchRes = await k.W.PatchAsJsonAsync($"/api/v1/leader-records/{recordId}/person",
            new { personId = (Guid?)null });
        await ApiTestKit.Expect(patchRes, HttpStatusCode.OK);

        var res = await k.R.GetAsync("/api/v1/leaders?date=1939-09-01");
        var body = await ApiTestKit.Expect(res, HttpStatusCode.OK);
        var features = body.GetProperty("data").GetProperty("features").EnumerateArray().ToList();
        var f = features.FirstOrDefault(x => x.GetProperty("recordId").GetGuid() == recordId);
        Assert.True(f.ValueKind != JsonValueKind.Undefined);
        Assert.Equal(JsonValueKind.Null, f.GetProperty("personId").ValueKind);
        Assert.Equal(JsonValueKind.Null, f.GetProperty("bio").ValueKind);
    }

    [Fact]
    public async Task CreateBio_validates_invalid_birthDatePrecision()
    {
        var k = new ApiTestKit(fx);
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-bios", new
        {
            name = "Test Person",
            birthDate = "1900-01-01",
            birthDatePrecision = "invalid_precision",
            isTest = true,
        });
        await ApiTestKit.Expect(res, HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task GetLeaders_without_bio_returns_null_personId_and_bio()
    {
        var k = new ApiTestKit(fx);
        var jp = await k.Regime("jp-no-bio-test");
        var recordId = await CreateLeader(k, jp, "Hideki Tojo", "head_of_government", "1941-10-18");

        var res = await k.R.GetAsync("/api/v1/leaders?date=1942-01-01");
        var body = await ApiTestKit.Expect(res, HttpStatusCode.OK);
        var features = body.GetProperty("data").GetProperty("features").EnumerateArray().ToList();
        var f = features.FirstOrDefault(x => x.GetProperty("recordId").GetGuid() == recordId);
        Assert.True(f.ValueKind != JsonValueKind.Undefined);
        Assert.Equal(JsonValueKind.Null, f.GetProperty("personId").ValueKind);
        Assert.Equal(JsonValueKind.Null, f.GetProperty("bio").ValueKind);
    }
}
