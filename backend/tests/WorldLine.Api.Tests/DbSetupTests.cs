using WorldLine.Api.Infrastructure;

namespace WorldLine.Api.Tests;

public class DbSetupTests
{
    [Fact]
    public void Jit_is_turned_off_on_the_connection()
    {
        var cs = DbSetup.WithJitOff("Host=127.0.0.1;Port=5442;Database=x;Username=u;Password=p");
        Assert.Contains("jit=off", new Npgsql.NpgsqlConnectionStringBuilder(cs).Options);
    }

    [Fact]
    public void Existing_options_are_kept_and_existing_jit_setting_wins()
    {
        var kept = new Npgsql.NpgsqlConnectionStringBuilder(DbSetup.WithJitOff("Host=h;Options=-c statement_timeout=5000")).Options!;
        Assert.Contains("statement_timeout=5000", kept);
        Assert.Contains("jit=off", kept);
        var own = new Npgsql.NpgsqlConnectionStringBuilder(DbSetup.WithJitOff("Host=h;Options=-c jit=on")).Options!;
        Assert.Equal("-c jit=on", own);
    }
}
