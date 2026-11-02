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

// 啟動預熱（Tai 2026-11-03 效能：所有變動點依序背景預熱，覆蓋主權×3容差＋衝突圖層；
// 快取被 Invalidate 後自動重排一次預熱，保持播放體驗流暢）。
_ = Task.Run(async () =>
{
    var lifetime = app.Services.GetRequiredService<IHostApplicationLifetime>();
    var stopping = lifetime.ApplicationStopping;
    // 等 Kestrel 就緒，不搶啟動資源
    try { await Task.Delay(500, stopping); } catch (OperationCanceledException) { return; }

    while (!stopping.IsCancellationRequested)
    {
        using var scope = app.Services.CreateScope();
        var db     = scope.ServiceProvider.GetRequiredService<WorldLineDbContext>();
        var cache  = scope.ServiceProvider.GetRequiredService<DateIntervalCache>();
        var logger = scope.ServiceProvider.GetRequiredService<ILogger<Program>>();
        var version = cache.Version;
        var sw = Stopwatch.StartNew();
        int count = 0, total = 0;

        try
        {
            var points = await cache.ChangePointsAsync(db, stopping);
            total = points.Length;

            // 3 種主權容差（0.010 / 0.004 / 0.002）＋衝突 ＝ 4 種快取，確認 MaxEntries 足夠
            const int kinds = 4;
            var needed = total * kinds;
            if (needed > DateIntervalCache.MaxEntries)
            {
                DateIntervalCache.MaxEntries = needed;
                // 各種類平均每筆估計約 1.4 MB（fine 主權 ~3.4 MB、中粗各 ~1 MB、衝突 ~0.1 MB）
                logger.LogInformation(
                    "MaxEntries 已調高至 {Max}（{Points} 個變動點 × {Kinds} 種），估計快取用量約 {EstMB:F0} MB",
                    needed, total, kinds, needed * 1.4);
            }

            foreach (var point in points)
            {
                if (stopping.IsCancellationRequested || cache.Version != version) break;
                try
                {
                    await WorldLine.Api.Features.SovereigntyEndpoints.WarmupAsync(point, db, cache);
                    await WorldLine.Api.Features.ConflictsEndpoints.WarmupAsync(point, db, cache);
                    count++;
                }
                catch (Exception ex)
                {
                    logger.LogWarning(ex, "背景預熱 {Date} 失敗（不影響服務）", point);
                }
                // 短暫讓出，避免長時間佔用執行緒集區
                await Task.Delay(50, CancellationToken.None);
            }
        }
        catch (OperationCanceledException) { return; }
        catch (Exception ex)
        {
            logger.LogWarning(ex, "背景預熱流程發生錯誤（不影響服務）");
        }

        sw.Stop();
        logger.LogInformation("背景預熱完成：{Count}/{Total} 個日期，耗時 {Elapsed:F1} s", count, total, sw.Elapsed.TotalSeconds);

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
public partial class Program;
