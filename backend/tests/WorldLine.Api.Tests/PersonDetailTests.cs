using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Npgsql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 人物 P1（2026-11-07）：照片授權欄位、生平逐欄位引用（接 sources）、撤回重寫、人物詳情含全部任期。
/// </summary>
[Collection(PostGisCollection.Name)]
public sealed class PersonDetailTests(PostGisFixture fx)
{
    private static object Portrait(string license = "pd_expired", string? attribution = "Unknown author, via Wikimedia Commons") => new
    {
        url = "https://upload.wikimedia.org/wikipedia/commons/x/xx/Test.jpg",
        sourceUrl = "https://commons.wikimedia.org/wiki/File:Test.jpg",
        author = "Unknown author",
        licenseCode = license,
        licenseUrl = "https://commons.wikimedia.org/wiki/Template:PD-old-70",
        attribution,
        retrievedOn = "2026-11-07",
    };

    private async Task<Guid> Leader(ApiTestKit k, Guid regimeId, string name, string role, string from, string? to, Guid personId, string? title = null)
    {
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-records", new
        {
            regimeId, name, role, title, validFrom = from, validTo = to, personId, source = "Test official record", verified = true,
        });
        return await k.Id(res);
    }

    [Fact]
    public async Task Bio_with_portrait_and_citations_returns_full_detail_with_all_terms()
    {
        var k = new ApiTestKit(fx);
        var src = await k.Source("official_record", "us_federal_pd", "Test presidential biography");
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-bios", new
        {
            name = "Test Person", nameZh = "測試人物", birthDate = "1882-01-30", birthDatePrecision = "day",
            deathDate = "1945-01-01", deathDatePrecision = "year", wikidataQid = "Q8007", isTest = true,
            portrait = Portrait(),
            citations = new object[]
            {
                new { field = "birthDate", sourceId = src, locator = "para. 1", evidenceNote = "born January 30, 1882", accessedOn = "2026-11-07" },
                new { field = "portrait", sourceId = src, locator = "File page", accessedOn = "2026-11-07" },
            },
        });
        var bioId = await k.Id(res);

        var reg = await k.Regime("person-detail-a");
        await Leader(k, reg, "Test Person", "head_of_state", "1933-03-04", "1945-04-12", bioId, "President");
        await Leader(k, reg, "Test Person", "head_of_government", "1933-03-04", "1945-04-12", bioId);

        var d = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leader-bios/{bioId}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal("year", d.GetProperty("deathDatePrecision").GetString());
        Assert.Equal("Q8007", d.GetProperty("wikidataQid").GetString());
        Assert.Equal("pd_expired", d.GetProperty("portrait").GetProperty("licenseCode").GetString());
        var cits = d.GetProperty("fieldCitations");
        Assert.Equal(2, cits.GetArrayLength());
        Assert.Contains(cits.EnumerateArray(), c => c.GetProperty("field").GetString() == "birthDate"
            && c.GetProperty("source").GetProperty("title").GetString() == "Test presidential biography"
            && c.GetProperty("locator").GetString() == "para. 1");
        var terms = d.GetProperty("terms");
        Assert.Equal(2, terms.GetArrayLength());
        Assert.All(terms.EnumerateArray(), t => Assert.Equal("person-detail-a", t.GetProperty("regimeName").GetProperty("en").GetString()));
        Assert.Equal("1945-04-12", terms[0].GetProperty("validPeriod").GetProperty("end").GetString());

        // GET /leaders 摘要帶照片與卒日精度
        var leaders = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leaders?date=1940-01-01&regime=person-detail-a-{k.Tag}"), HttpStatusCode.OK))
            .GetProperty("data").GetProperty("features");
        Assert.Equal(2, leaders.GetArrayLength());
        var bio = leaders[0].GetProperty("bio");
        Assert.Equal("year", bio.GetProperty("deathDatePrecision").GetString());
        Assert.StartsWith("https://upload.wikimedia.org/", bio.GetProperty("portrait").GetProperty("url").GetString());
    }

    [Theory]
    [InlineData("all_rights_reserved", "Someone")]
    [InlineData("cc_by_nc", "Someone")]
    [InlineData("pd_expired", null)]
    public async Task Portrait_with_disallowed_license_or_missing_attribution_is_rejected(string license, string? attribution)
    {
        var k = new ApiTestKit(fx);
        var res = await k.W.PostAsJsonAsync("/api/v1/leader-bios", new { name = "Bad Portrait", isTest = true, portrait = Portrait(license, attribution) });
        await ApiTestKit.Expect(res, HttpStatusCode.BadRequest);
    }

    [Fact]
    public async Task Citation_requires_locator_existing_source_and_accessed_date()
    {
        var k = new ApiTestKit(fx);
        var bioId = await k.Id(await k.W.PostAsJsonAsync("/api/v1/leader-bios", new { name = "Cite Target", isTest = true }));
        var src = await k.Source("official_record");

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "birthDate", sourceId = src, locator = " ", accessedOn = "2026-11-07" }), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "birthDate", sourceId = Guid.NewGuid(), locator = "p. 1", accessedOn = "2026-11-07" }), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "birthDate", sourceId = src, locator = "p. 1" }), HttpStatusCode.BadRequest);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "shoeSize", sourceId = src, locator = "p. 1", accessedOn = "2026-11-07" }), HttpStatusCode.BadRequest);

        var created = await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "summary", sourceId = src, locator = "§2", accessedOn = "2026-11-07" }), HttpStatusCode.Created);
        var citId = created.GetProperty("data").GetProperty("id").GetGuid();

        // 寫入引用需要 API key
        await ApiTestKit.Expect(await k.R.PostAsJsonAsync($"/api/v1/leader-bios/{bioId}/field-citations",
            new { field = "summary", sourceId = src, locator = "§2", accessedOn = "2026-11-07" }), HttpStatusCode.Unauthorized);

        // 撤回：一次成功，第二次 409；撤回後不再出現在詳情
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bio-field-citations/{citId}/retraction", new { reason = "test" }), HttpStatusCode.OK);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bio-field-citations/{citId}/retraction", new { reason = "test" }), HttpStatusCode.Conflict);
        var d = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leader-bios/{bioId}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(0, d.GetProperty("fieldCitations").GetArrayLength());

        // I5：DB 層不可 DELETE
        await using var c = new NpgsqlConnection(fx.ConnectionString);
        await c.OpenAsync();
        await using var cmd = new NpgsqlCommand($"DELETE FROM leader_bio_field_citations WHERE id = '{citId}'", c);
        await Assert.ThrowsAsync<PostgresException>(() => cmd.ExecuteNonQueryAsync());
    }

    [Fact]
    public async Task Revision_retracts_old_relinks_terms_and_carries_citations()
    {
        var k = new ApiTestKit(fx);
        var src = await k.Source("official_record");
        var oldId = await k.Id(await k.W.PostAsJsonAsync("/api/v1/leader-bios", new
        {
            name = "Revise Me", isTest = true,
            fieldSources = new { birthDate = new { status = "待查證" } },
            citations = new[] { new { field = "name", sourceId = src, locator = "p. 3", accessedOn = "2026-11-07" } },
        }));
        var reg = await k.Regime("person-revise");
        var recId = await Leader(k, reg, "Revise Me", "head_of_state", "1920-01-01", "1925-01-01", oldId);

        var res = await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{oldId}/revisions", new
        {
            reason = "補卒年（原文只到年）",
            bio = new
            {
                name = "Revise Me", isTest = true, deathDate = "1934-01-01", deathDatePrecision = "year",
                citations = new[] { new { field = "deathDate", sourceId = src, locator = "p. 9", accessedOn = "2026-11-07" } },
            },
        });
        var body = await ApiTestKit.Expect(res, HttpStatusCode.Created);
        var nd = body.GetProperty("data");
        var newId = nd.GetProperty("id").GetGuid();
        Assert.NotEqual(oldId, newId);
        Assert.Equal(2, nd.GetProperty("fieldCitations").GetArrayLength());
        Assert.Equal(1, nd.GetProperty("terms").GetArrayLength());
        Assert.Equal(recId, nd.GetProperty("terms")[0].GetProperty("recordId").GetGuid());
        Assert.Equal("待查證", nd.GetProperty("fieldSources").GetProperty("birthDate").GetProperty("status").GetString());

        var od = (await ApiTestKit.Expect(await k.R.GetAsync($"/api/v1/leader-bios/{oldId}"), HttpStatusCode.OK)).GetProperty("data");
        Assert.Equal(JsonValueKind.String, od.GetProperty("retractedAt").ValueKind);
        Assert.Equal(newId, od.GetProperty("supersededBy").GetGuid());
        Assert.Equal(0, od.GetProperty("terms").GetArrayLength());

        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{oldId}/revisions",
            new { reason = "again", bio = new { name = "x", isTest = true } }), HttpStatusCode.Conflict);
        await ApiTestKit.Expect(await k.W.PostAsJsonAsync($"/api/v1/leader-bios/{oldId}/field-citations",
            new { field = "name", sourceId = src, locator = "p", accessedOn = "2026-11-07" }), HttpStatusCode.Conflict);
    }
}
