using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.AspNetCore.Http.Json;
using Microsoft.AspNetCore.ResponseCompression;
using System.IO.Compression;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Microsoft.OpenApi;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using WorldLine.Api.Common;
using WorldLine.Api.Infrastructure;
using WorldLine.Contracts;

var builder = WebApplication.CreateBuilder(args);

builder.Services.Configure<JsonOptions>(o =>
    o.SerializerOptions.Converters.Add(new GeoJsonConverterFactory(new GeometryFactory(new PrecisionModel(), 4326))));
// 綁定失敗（JSON 格式錯、日期格式錯）也走統一錯誤格式
builder.Services.Configure<RouteHandlerOptions>(o => o.ThrowOnBadRequest = true);
builder.Services.AddExceptionHandler<ApiExceptionHandler>();
// UseExceptionHandler() 需要 IProblemDetailsService 才能啟動；實際回應一律由 ApiExceptionHandler 寫成統一格式
builder.Services.AddProblemDetails();

builder.Services.AddOpenApi(o => o.AddDocumentTransformer((doc, _, _) =>
{
    doc.Info.Title = "World Line API";
    doc.Info.Version = "v1";
    doc.Info.Description = "二戰階段歷史地圖 API。讀取公開；寫入需 X-API-Key。日期一律 YYYY-MM-DD，區間為半開 [start, end)。";
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

// 連線字串由 compose 的 ConnectionStrings__WorldLine 提供；未設定時仍註冊（Npgsql 只在實際查詢時連線），健康檢查會回報 Unhealthy。
var connectionString = builder.Configuration.GetConnectionString(DbSetup.ConnectionStringName)
                       ?? "Host=127.0.0.1;Port=5432;Database=appdb_ww2;Username=unset;Password=unset";
builder.Services.AddDbContext<WorldLineDbContext>(o => DbSetup.Configure(o, connectionString));
// 效能（Tai 2026-11-01：播放、跳日期不順）：
// - 回應壓縮：主權圖層一天約 3.4 MB JSON，br／gzip 用最快等級（壓縮本身不能變成瓶頸）
// - 逐日查詢依變動區間快取（DateIntervalCache；寫入即作廢）
builder.Services.AddResponseCompression(o =>
{
    o.EnableForHttps = true;
    o.Providers.Add<BrotliCompressionProvider>();
    o.Providers.Add<GzipCompressionProvider>();
});
builder.Services.Configure<BrotliCompressionProviderOptions>(o => o.Level = CompressionLevel.Fastest);
builder.Services.Configure<GzipCompressionProviderOptions>(o => o.Level = CompressionLevel.Fastest);
builder.Services.AddSingleton<DateIntervalCache>();
builder.Services.AddHealthChecks().AddDbContextCheck<WorldLineDbContext>("db");

var app = builder.Build();

if (app.Configuration.GetValue<bool>("WORLDLINE_MIGRATE_ON_STARTUP"))
{
    using var scope = app.Services.CreateScope();
    await scope.ServiceProvider.GetRequiredService<WorldLineDbContext>().Database.MigrateAsync();
}

app.UseResponseCompression();
app.UseExceptionHandler();
app.UseMiddleware<BumpOnWriteMiddleware>();
app.MapOpenApi("/openapi/{documentName}.json");

app.MapHealthChecks("/healthz", new HealthCheckOptions
{
    ResultStatusCodes =
    {
        [HealthStatus.Healthy] = StatusCodes.Status200OK,
        [HealthStatus.Degraded] = StatusCodes.Status200OK,
        [HealthStatus.Unhealthy] = StatusCodes.Status503ServiceUnavailable,
    },
    ResponseWriter = (http, report) =>
    {
        var dto = new HealthReportDto(report.Status.ToString(),
            report.Entries.ToDictionary(e => e.Key, e => e.Value.Status.ToString()));
        var status = report.Status == HealthStatus.Unhealthy ? 503 : 200;
        return http.Response.WriteAsJsonAsync(new ApiResponse<HealthReportDto>(status, report.Status.ToString(), dto));
    },
});

var api = app.MapGroup("/api/v1");
WorldLine.Api.Features.EndpointRegistry.Map(api);

app.Run();

/// <summary>讓整合測試的 WebApplicationFactory 可以參照。</summary>
public partial class Program;
