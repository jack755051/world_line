using Microsoft.EntityFrameworkCore;

namespace WorldLine.Api.Infrastructure;

public static class DbSetup
{
    public const string ConnectionStringName = "WorldLine";

    public static void Configure(DbContextOptionsBuilder options, string connectionString) =>
        options
            .UseNpgsql(connectionString, npgsql =>
            {
                npgsql.UseNetTopologySuite();
                npgsql.MigrationsHistoryTable("__ef_migrations_history");
            })
            .UseSnakeCaseNamingConvention();
}
