using Microsoft.EntityFrameworkCore;

namespace WorldLine.Api.Data;

public class WorldLineDbContext(DbContextOptions<WorldLineDbContext> options) : DbContext(options)
{
}
