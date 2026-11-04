using System.Diagnostics;
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
// 逐日快取（Tai 2026-11-04）：滑動視窗，前後各 WORLDLINE_CACHE_WINDOW 個變動區間（預設 10）、
// 往播放方向預先載入 WORLDLINE_CACHE_PREFETCH 個（預設 3）；估算大小上限 WORLDLINE_CACHE_MAX_MB（預設 1536）當保險
var cacheMaxMb = builder.Configuration.GetValue<long?>("WORLDLINE_CACHE_MAX_MB") is { } mb and > 0 ? mb : DateIntervalCache.DefaultMaxBytes / (1024 * 1024);
var cacheWindow = builder.Configuration.GetValue<int?>("WORLDLINE_CACHE_WINDOW") is { } w and >= 0 ? w : DateIntervalCache.DefaultWindowRadius;
var cachePrefetch = Math.Min(cacheWindow, builder.Configuration.GetValue<int?>("WORLDLINE_CACHE_PREFETCH") is { } pf and >= 0 ? pf : DateIntervalCache.DefaultPrefetchCount);
builder.Services.AddSingleton(sp => new DateIntervalCache(cacheMaxMb * 1024 * 1024, cacheWindow, cachePrefetch)
{
    ScopeFactory = () => sp.GetRequiredService<IServiceScopeFactory>().CreateScope(),
});
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

// 啟動預熱（Tai 2026-11-04：不全量預熱，只載入預設日期那一格，視窗中心設在那裡，
// 之後的預先載入往後補幾格；原本全部 591 個變動點 × 4 種預熱會吃到 ~7 GB 被系統砍掉）。
// 日期：WORLDLINE_PREWARM_DATE（空字串＝不預熱），預設前端預設日期 1940-07-15。快取被 Invalidate 後自動重排一次。
var prewarmDate = ParsePrewarmDate(app.Configuration["WORLDLINE_PREWARM_DATE"]);
_ = Task.Run(async () =>
{
    if (prewarmDate is not { } day) return;
    var lifetime = app.Services.GetRequiredService<IHostApplicationLifetime>();
    var stopping = lifetime.ApplicationStopping;
    // 等 Kestrel 就緒，不搶啟動資源
    try { await Task.Delay(500, stopping); } catch (OperationCanceledException) { return; }

    while (!stopping.IsCancellationRequested)
    {
        var cache = app.Services.GetRequiredService<DateIntervalCache>();
        var logger = app.Services.GetRequiredService<ILogger<Program>>();
        var version = cache.Version;
        var sw = Stopwatch.StartNew();
        try
        {
            using var scope = app.Services.CreateScope();
            var db = scope.ServiceProvider.GetRequiredService<WorldLineDbContext>();
            await WorldLine.Api.Features.SovereigntyEndpoints.WarmupAsync(day, db, cache);
            await WorldLine.Api.Features.ConflictsEndpoints.WarmupAsync(day, db, cache);
            logger.LogInformation("背景預熱 {Date} 完成：{Entries} 筆、估計 {MB:F0} MB（視窗 ±{N}、預先載入 {P}、上限 {Max:F0} MB），耗時 {Elapsed:F1} s",
                day, cache.Count, cache.EstimatedBytes / 1048576.0, cache.WindowRadius, cache.PrefetchCount, cache.MaxBytes / 1048576.0, sw.Elapsed.TotalSeconds);
        }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "背景預熱 {Date} 失敗（不影響服務）", day);
        }

        // 等快取版本更新（寫入觸發 Invalidate）後重排一次預熱；每 2 s 輪詢
        while (!stopping.IsCancellationRequested && cache.Version == version)
        {
            try { await Task.Delay(2000, stopping); }
            catch (OperationCanceledException) { return; }
        }
    }
});

app.Run();

/// <summary>讓整合測試的 WebApplicationFactory 可以參照。</summary>
public partial class Program
{
    /// <summary>預設預熱日期：前端預設日期（frontend AtlasState.defaultDate）。</summary>
    internal static readonly DateOnly DefaultPrewarmDate = new(1940, 7, 15);

    /// <summary>解析 WORLDLINE_PREWARM_DATE；未設定用預設，空字串或格式錯＝不預熱。</summary>
    internal static DateOnly? ParsePrewarmDate(string? raw) => raw is null
        ? DefaultPrewarmDate
        : DateOnly.TryParseExact(raw.Trim(), "yyyy-MM-dd", out var d) ? d : null;
}
