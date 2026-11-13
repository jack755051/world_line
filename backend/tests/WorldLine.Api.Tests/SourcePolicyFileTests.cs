using System.Text.Json;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests;

/// <summary>後端的禁用網域必須與全專案唯一的政策檔 data/source-policy.json 一致（docs/source-rules.md）。</summary>
public class SourcePolicyFileTests
{
    private static JsonElement Policy()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null && !File.Exists(Path.Combine(dir.FullName, "data", "source-policy.json"))) dir = dir.Parent;
        Assert.NotNull(dir);
        return JsonDocument.Parse(File.ReadAllText(Path.Combine(dir!.FullName, "data", "source-policy.json"))).RootElement;
    }

    [Fact]
    public void Excluded_hosts_match_policy_file()
    {
        var hosts = Policy().GetProperty("bannedHosts").EnumerateArray().Select(e => e.GetString()!).OrderBy(h => h, StringComparer.Ordinal).ToArray();
        Assert.Equal(hosts, BioSourcePolicy.ExcludedHosts.OrderBy(h => h, StringComparer.Ordinal).ToArray());
    }

    [Fact]
    public void Quote_limit_matches_policy_file() =>
        Assert.Equal(BioSourcePolicy.QuoteMaxChars, Policy().GetProperty("quoteMaxChars").GetInt32());
}
