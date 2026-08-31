using Microsoft.AspNetCore.Mvc.Testing;
using Testcontainers.PostgreSql;

namespace WorldLine.Api.Tests.Integration;

/// <summary>
/// task 2.15：integration test 的共用 host——每個測試執行檔只啟動**一個** PostGIS
/// Testcontainer（見 `IntegrationTestCollection`，所有 integration test 類別共用同一個
/// collection，xUnit 保證同一個 collection 內的測試類別依序執行、不會平行跑，避免多個
/// 測試類別同時打同一個真實資料庫造成競態），不是每個測試類別各自開一個容器——起一個
/// PostGIS 容器要幾秒鐘，乘上十幾個測試類別會讓整組測試跑起來慢到不划算。
///
/// **用真正的 `Program.cs` 啟動流程，不 mock DbContext**：`Program.cs` 在
/// Development 環境會自動跑 migration ＋ `SeedData.SeedAsync()`（見該檔案），這裡
/// 直接沿用同一條路徑，換掉的只有連線字串（指向 Testcontainer）——這樣每個測試都
/// 能拿到跟 `docker compose up` 起本機開發環境時同一份、已經被前面每個任務逐一 curl
/// 驗證過的種子資料，不用為了寫測試另外手刻一套 fixture 資料。
/// </summary>
public class WorldLineApiFactory : WebApplicationFactory<Program>, IAsyncLifetime
{
    /// <summary>掛在 X-API-Key header 上的測試用值——執行期隨機產生（不是寫死的字面值），
    /// 見 `AuthorizedClient()`。</summary>
    public static readonly string WriteApiKey = Guid.NewGuid().ToString("N");

    // 跟 docker-compose.yml 的 postgres service 用同一個 image，確保 PostGIS extension
    // 版本一致——這個 schema 大量依賴 geometry/int4range/btree_gist，換一個隨便的
    // postgres:xx image 會在 migration 階段直接炸掉。
    private readonly PostgreSqlContainer postgres = new PostgreSqlBuilder("postgis/postgis:16-3.4").Build();

    /// <summary>沒帶 `X-API-Key` 的一般用戶端——大部分讀取端點測試用這個。</summary>
    public HttpClient AnonymousClient() => CreateClient();

    /// <summary>帶合法 `X-API-Key` 的用戶端——寫入端點（POST/PATCH）成功案例用這個。</summary>
    public HttpClient AuthorizedClient()
    {
        var client = CreateClient();
        client.DefaultRequestHeaders.Add("X-API-Key", WriteApiKey);
        return client;
    }

    /// <summary>
    /// **不用 `ConfigureWebHost().ConfigureAppConfiguration()` 覆蓋連線字串**——那是
    /// 一般 ASP.NET Core 專案（`IWebHostBuilder`）integration test 的標準做法，但
    /// `Program.cs` 是 minimal hosting model（`WebApplication.CreateBuilder()`），
    /// `WebApplicationFactory&lt;Program&gt;` 靠 `HostFactoryResolver` 攔截、實際上是讓
    /// 真正的 `Program.Main()` 整段跑過一次、只在最後 `builder.Build()` 那一刻才把
    /// 建好的 host 攔下來——`Program.cs` 第 43 行 `builder.Configuration.
    /// GetConnectionString("DefaultConnection")` 在攔截點**之前**就執行完了，
    /// `ConfigureAppConfiguration()` 加的設定來得太晚，實測會直接炸
    /// `InvalidOperationException`（見這個檔案的 git 歷史，一開始就是這樣寫、真的
    /// 跑測試才發現的）。改用環境變數——`WebApplication.CreateBuilder()` 一開始
    /// 就會讀環境變數當設定來源，在 `Program.cs` 讀到這行之前就已經生效，不受這個
    /// 攔截時機問題影響。
    /// </summary>
    async Task IAsyncLifetime.InitializeAsync()
    {
        Environment.SetEnvironmentVariable("API_WRITE_KEY", WriteApiKey);
        Environment.SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Development"); // Program.cs 的自動 migrate+seed 邏輯掛在這個環境判斷底下
        await postgres.StartAsync(); // 先起容器才拿得到真正的連線字串
        Environment.SetEnvironmentVariable("ConnectionStrings__DefaultConnection", postgres.GetConnectionString());
    }

    // WebApplicationFactory 本身已經有 DisposeAsync()（IAsyncDisposable，回傳
    // ValueTask）——xUnit 的 IAsyncLifetime.DisposeAsync() 回傳 Task，兩個簽章不同，
    // 用明確介面實作區分，不要互相蓋過去。
    async Task IAsyncLifetime.DisposeAsync()
    {
        await postgres.DisposeAsync();
        await base.DisposeAsync();
    }
}

/// <summary>見 `WorldLineApiFactory` 類別文件——所有 integration test 類別都掛
/// `[Collection(Name)]`，共用同一個容器實例、依序執行。</summary>
[CollectionDefinition(Name)]
public class IntegrationTestCollection : ICollectionFixture<WorldLineApiFactory>
{
    public const string Name = "WorldLine API integration tests";
}
