var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

var app = builder.Build();

// Configure the HTTP request pipeline.
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
app.MapGet("/api/v1/health", () => Results.Ok(new { status = "ok" }));

app.Run();
