using System.Net;
using System.Text.Json;

namespace WorldLine.Api.Tests;

[Collection(PostGisCollection.Name)]
public sealed class HealthTests(PostGisFixture fx)
{
    [Fact]
    public async Task Healthz_reports_db_healthy_in_envelope()
    {
        var res = await fx.Reader().GetAsync("/healthz");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
        using var doc = JsonDocument.Parse(await res.Content.ReadAsStringAsync());
        Assert.Equal(200, doc.RootElement.GetProperty("statusCode").GetInt32());
        Assert.Equal("Healthy", doc.RootElement.GetProperty("data").GetProperty("checks").GetProperty("db").GetString());
    }

    [Fact]
    public async Task OpenApi_document_is_served()
    {
        var res = await fx.Reader().GetAsync("/openapi/v1.json");
        Assert.Equal(HttpStatusCode.OK, res.StatusCode);
    }
}
