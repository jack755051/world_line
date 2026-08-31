using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.IO.Converters;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

// task 2.6：疆域端點要把 NetTopologySuite 的 MultiPolygon 序列化成標準 GeoJSON 給前端
// MapLibre 直接吃——System.Text.Json 預設不認得 NTS 的幾何型別，要掛官方轉換器
// （GeoJSON4STJ，跟 Npgsql.EntityFrameworkCore.PostgreSQL.NetTopologySuite 是同一個
// NTS 生態系但職責不同：一個管資料庫讀寫，一個管 JSON 序列化）。
builder.Services.AddControllers()
    .AddJsonOptions(options => options.JsonSerializerOptions.Converters.Add(new GeoJsonConverterFactory()));
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// task 2.0：[ApiController] 自動觸發的 model-state 驗證失敗（400）也要走統一包裝格式，
// 不能讓它偷跑成 ASP.NET 內建的 ValidationProblemDetails 形狀。
builder.Services.Configure<ApiBehaviorOptions>(options =>
{
    // 2026-08-29 修訂：message 放穩定代碼，框架自動觸發、無法歸因到單一規則的驗證失敗
    // 一律用通用的 VALIDATION_ERROR，逐欄位的詳細原因不再組進 message（見 ApiResponse 的
    // 類別註解，這是換取代碼穩定可依賴的已知取捨）。
    options.InvalidModelStateResponseFactory = _ =>
        new BadRequestObjectResult(ApiResponse.Error(StatusCodes.Status400BadRequest, ApiMessageCodes.ValidationError));
});

// task 2.0：未捕捉例外也要走統一包裝格式（見 ApiExceptionHandler），需搭配下方 UseExceptionHandler()。
builder.Services.AddExceptionHandler<ApiExceptionHandler>();
builder.Services.AddProblemDetails();

// 憲法 §4 政權狀態機驗證（task 2.1）：無狀態、無外部相依，singleton 即可。
builder.Services.AddSingleton<IRegimeTransitionValidator, RegimeTransitionValidator>();

// EDTF 解析（task 2.2）：無狀態（NodaTime 的 CalendarSystem.Iso 本身是靜態單例），singleton 即可。
builder.Services.AddSingleton<IEdtfService, EdtfService>();

var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
    ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");

builder.Services.AddDbContext<WorldLineDbContext>(options =>
    options.UseNpgsql(connectionString, npgsqlOptions => npgsqlOptions.UseNetTopologySuite())
           .UseSnakeCaseNamingConvention());

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.MapOpenApi();

    using var seedScope = app.Services.CreateScope();
    var seedDb = seedScope.ServiceProvider.GetRequiredService<WorldLineDbContext>();
    await seedDb.Database.MigrateAsync();
    await SeedData.SeedAsync(seedDb);
    await RealDataSeed.SeedAsync(seedDb); // 真正查證過、附引用來源的正式史料，見該類別文件說明
}

app.UseExceptionHandler();

app.UseHttpsRedirection();

// task 2.14：寫入端點（POST/PATCH）的最小 API Key 驗證，見 ApiWriteKeyMiddleware。
// 放在 UseAuthorization() 之前——這個 middleware 自己判斷方法/驗證 key，不依賴
// ASP.NET 內建的 authentication/authorization 管線（這個專案沒有配置任何
// authentication scheme，UseAuthorization() 目前是保留給之後真的需要時的預留位置）。
app.UseMiddleware<ApiWriteKeyMiddleware>();

app.UseAuthorization();

app.MapControllers();

app.Run();

// task 2.15：`Program` 用 top-level statements 寫，編譯器產生的類別預設是
// internal——`WebApplicationFactory<Program>`（api.Tests 的 integration test）
// 要從外部組件參考它，必須明確宣告成 public，這是 ASP.NET Core 官方文件記載的標準
// 做法，不影響應用程式本身任何行為。
public partial class Program;
