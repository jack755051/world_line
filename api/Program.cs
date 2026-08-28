using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Contracts;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;
using WorldLine.Api.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
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
}

app.UseExceptionHandler();

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
