using System.Net.Http.Json;
using Microsoft.AspNetCore.Hosting;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.Extensions.Configuration;
using DotNet.Testcontainers.Images;
using Testcontainers.PostgreSql;

namespace WorldLine.Api.Tests;

/// <summary>
/// 每次測試執行啟動一個真實的 PostGIS 容器（PRD §5：I1–I6 必須用真實 PostGIS 測），
/// 用 WebApplicationFactory 起 API，啟動時套用 migration。容器隨測試結束移除，不碰任何既有資料庫。
/// </summary>
public sealed class PostGisFixture : IAsyncLifetime
{
    public const string Image = "postgis/postgis:18-3.6";

    /// <summary>postgis/postgis 官方映像只有 linux/amd64；Apple Silicon 上以模擬執行（與 compose.yaml 一致）。</summary>
    public const string ImagePlatform = "linux/amd64";
    public const string TestApiKey = "test-api-key-not-a-secret";

    private readonly PostgreSqlContainer _db = new PostgreSqlBuilder(new DockerImage(Image, new Platform(ImagePlatform)))
        .WithDatabase("worldline_test")
        .WithUsername("worldline")
        .WithPassword("worldline")
        .Build();

    public WebApplicationFactory<Program> Factory { get; private set; } = null!;
    public string ConnectionString => _db.GetConnectionString();

    public async Task InitializeAsync()
    {
        await _db.StartAsync();
        Factory = new WebApplicationFactory<Program>().WithWebHostBuilder(b =>
        {
            b.UseEnvironment("Testing");
            b.UseSetting("ConnectionStrings:WorldLine", ConnectionString);
            b.UseSetting("WORLDLINE_API_KEY", TestApiKey);
            b.UseSetting("WORLDLINE_MIGRATE_ON_STARTUP", "true");
        });
        _ = Factory.Server; // 觸發啟動（含 migration）
    }

    public HttpClient Reader() => Factory.CreateClient();

    public HttpClient Writer()
    {
        var c = Factory.CreateClient();
        c.DefaultRequestHeaders.Add("X-API-Key", TestApiKey);
        return c;
    }

    public async Task DisposeAsync()
    {
        if (Factory is not null) await Factory.DisposeAsync();
        await _db.DisposeAsync();
    }
}

[CollectionDefinition(Name)]
public sealed class PostGisCollection : ICollectionFixture<PostGisFixture>
{
    public const string Name = "postgis";
}
