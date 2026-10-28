using Microsoft.EntityFrameworkCore;

namespace WorldLine.Api.Infrastructure;

public sealed class WorldLineDbContext(DbContextOptions<WorldLineDbContext> options) : DbContext(options)
{
    protected override void OnModelCreating(ModelBuilder b)
    {
        b.HasPostgresExtension("postgis");
        b.HasPostgresExtension("btree_gist");
    }
}
