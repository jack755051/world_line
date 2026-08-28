using Microsoft.EntityFrameworkCore;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.

builder.Services.AddControllers();
// Learn more about configuring OpenAPI at https://aka.ms/aspnet/openapi
builder.Services.AddOpenApi();

// 憲法 §4 政權狀態機驗證（task 2.1）：無狀態、無外部相依，singleton 即可。
builder.Services.AddSingleton<IRegimeTransitionValidator, RegimeTransitionValidator>();

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

app.UseHttpsRedirection();

app.UseAuthorization();

app.MapControllers();

app.Run();
