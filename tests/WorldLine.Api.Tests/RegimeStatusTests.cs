using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests;

/// <summary>憲法 §4：後端唯一信任來源的狀態轉換規則（不需資料庫）。</summary>
public class RegimeStatusTests
{
    [Theory]
    [InlineData(RegimeStatus.Existing, RegimeStatus.Split)]
    [InlineData(RegimeStatus.Existing, RegimeStatus.Abdicated)]
    [InlineData(RegimeStatus.Existing, RegimeStatus.Destroyed)]
    public void Legal_transitions_are_allowed(string from, string to) =>
        Assert.True(RegimeStatus.IsLegalTransition(from, to));

    [Theory]
    [InlineData(RegimeStatus.Split, RegimeStatus.Existing)]
    [InlineData(RegimeStatus.Abdicated, RegimeStatus.Destroyed)]
    [InlineData(RegimeStatus.Destroyed, RegimeStatus.Abdicated)]
    [InlineData(RegimeStatus.Existing, RegimeStatus.Existing)]
    public void Illegal_transitions_are_rejected(string from, string to) =>
        Assert.False(RegimeStatus.IsLegalTransition(from, to));
}
