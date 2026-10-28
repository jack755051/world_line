using Microsoft.AspNetCore.Http.Json;
using Microsoft.OpenApi;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using WorldLine.Api.Api;
using WorldLine.Api.Data;

var builder = WebApplication.CreateBuilder(args);

builder.Services.AddControllers();

// GeoJSON：NetTopologySuite 幾何 ↔ GeoJSON（WGS84 / SRID 4326）
builder.Services.Configure<JsonOptions>(o =>
    o.SerializerOptions.Converters.Add(new GeoJsonConverterFactory(new GeometryFactory(new PrecisionModel(), 4326))));

// 統一錯誤格式：RFC 9457 ProblemDetails
builder.Services.AddProblemDetails();
builder.Services.AddExceptionHandler<ProblemExceptionHandler>();

builder.Services.AddOpenApi(o => o.AddDocumentTransformer((doc, _, _) =>
{
    doc.Info.Title = "World Line API";
    doc.Info.Description = "歷史地圖 GIS 平台 API。GET 公開；POST/PATCH 需 X-Api-Key（PRD §5）。年份一律為天文紀年整數（0 = 西元前 1 年）。";
    doc.Components ??= new OpenApiComponents();
    doc.Components.SecuritySchemes ??= new Dictionary<string, IOpenApiSecurityScheme>();
    doc.Components.SecuritySchemes["ApiKey"] = new OpenApiSecurityScheme
    {
        Type = SecuritySchemeType.ApiKey,
        In = ParameterLocation.Header,
        Name = ApiKeyFilter.HeaderName,
        Description = "寫入端點用的 API Key（伺服器端由環境變數 WORLDLINE_API_KEY 設定）",
    };
    return Task.CompletedTask;
}));

// 資料庫（PostgreSQL + PostGIS）。連線字串由 compose 的 ConnectionStrings__DefaultConnection 提供；
// 未設定（例如本機無 DB 時 dotnet run）就不註冊，避免啟動失敗。migration 一律以 `dotnet ef database update` 明確套用，不在啟動時自動執行。
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
if (!string.IsNullOrWhiteSpace(connectionString))
{
    builder.Services.AddDbContext<WorldLineDbContext>(options => DbSetup.Configure(options, connectionString));
}

var app = builder.Build();

app.UseExceptionHandler();
app.UseStatusCodePages();

if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();
}

// HTTPS 轉址只在「非容器」且「實際有設定 https 端點」（例如 launchSettings 的 https profile）時啟用。
// 容器內只開 http（TLS 由前端 Nginx／外部反向代理處理），官方 .NET 映像檔會設 DOTNET_RUNNING_IN_CONTAINER=true。
var runningInContainer = string.Equals(
    Environment.GetEnvironmentVariable("DOTNET_RUNNING_IN_CONTAINER"), "true", StringComparison.OrdinalIgnoreCase);
var configuredUrls = app.Configuration["urls"] ?? string.Empty;
var hasHttpsEndpoint = configuredUrls.Contains("https://", StringComparison.OrdinalIgnoreCase)
    || !string.IsNullOrWhiteSpace(app.Configuration["HTTPS_PORTS"])
    || !string.IsNullOrWhiteSpace(app.Configuration["https_port"]);
if (!runningInContainer && hasHttpsEndpoint)
{
    app.UseHttpsRedirection();
}

app.UseAuthorization();

app.MapControllers();

// 簡易存活檢查，供 compose／nginx 路徑對齊驗證使用
app.MapGet("/api/v1/health", () => Results.Ok(new { status = "ok" })).WithTags("Health");

var api = app.MapGroup("/api/v1");
RegimeEndpoints.Map(api);
TerritoryEndpoints.Map(api);
QueryEndpoints.Map(api);

app.Run();

/// <summary>讓整合測試的 WebApplicationFactory 可以參照。</summary>
public partial class Program;
