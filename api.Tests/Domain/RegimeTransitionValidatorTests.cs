using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests.Domain;

/// <summary>
/// task 2.15：task 2.1（憲法 §4 狀態機驗證）第一批正式單元測試——2.1 動工當時只做了
/// 14 組手動 curl/console 驗證（見 implementation plan），沒有留下自動化迴歸測試；這裡
/// 補上，跟前端同一套邏輯的 `regime-status.enum.spec.ts`（`isLegalRegimeStatusTransition()`）
/// 用同一個「窮舉 4×4=16 組」策略，兩邊各自獨立實作、各自窮舉——不是巧合對到同一組
/// 期望值，是這個專案「C#/TypeScript 無法共用同一份 library，只能各自實作、以憲法 §4
/// 為 SSOT」既有原則的後端這一半。
/// </summary>
public class RegimeTransitionValidatorTests
{
    private readonly RegimeTransitionValidator sut = new();

    public static readonly TheoryData<string, string, bool> AllStatusPairs = new()
    {
        // 憲法 §4：合法轉換只有這三條，全部只能從 active 出發。
        { "active", "split", true },
        { "active", "succeeded", true },
        { "active", "conquered", true },
        // 同狀態（不構成轉換）
        { "active", "active", false },
        { "split", "split", false },
        { "succeeded", "succeeded", false },
        { "conquered", "conquered", false },
        // 逆轉（不會有政權從終止狀態變回 active）
        { "split", "active", false },
        { "succeeded", "active", false },
        { "conquered", "active", false },
        // 終止狀態互轉（三個終止狀態之間沒有任何合法轉換）
        { "split", "succeeded", false },
        { "split", "conquered", false },
        { "succeeded", "split", false },
        { "succeeded", "conquered", false },
        { "conquered", "split", false },
        { "conquered", "succeeded", false },
    };

    [Theory]
    [MemberData(nameof(AllStatusPairs))]
    public void ValidateStatusTransition_窮舉全部十六組狀態配對(string from, string to, bool expectedLegal)
    {
        var result = sut.ValidateStatusTransition(from, to);

        Assert.Equal(expectedLegal, result.IsLegal);
        if (!expectedLegal)
        {
            Assert.NotNull(result.Reason);
        }
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("unknown-status")]
    public void ValidateStatusTransition_目前狀態代碼未知時不合法(string? currentStatusCode)
    {
        var result = sut.ValidateStatusTransition(currentStatusCode, "split");

        Assert.False(result.IsLegal);
    }

    [Theory]
    [InlineData(null)]
    [InlineData("")]
    [InlineData("unknown-status")]
    public void ValidateStatusTransition_目標狀態代碼未知時不合法(string? requestedStatusCode)
    {
        var result = sut.ValidateStatusTransition("active", requestedStatusCode);

        Assert.False(result.IsLegal);
    }

    [Fact]
    public void ValidateOriginLinkage_獨立建國_無前身無起源類型_合法()
    {
        var result = sut.ValidateOriginLinkage(null, null);

        Assert.True(result.IsLegal);
    }

    [Fact]
    public void ValidateOriginLinkage_有前身但沒填起源類型_不合法()
    {
        var result = sut.ValidateOriginLinkage(Guid.NewGuid(), null);

        Assert.False(result.IsLegal);
    }

    [Fact]
    public void ValidateOriginLinkage_有起源類型但沒填前身_不合法()
    {
        var result = sut.ValidateOriginLinkage(null, "split");

        Assert.False(result.IsLegal);
    }

    [Theory]
    [InlineData("split")]
    [InlineData("succeeded")]
    public void ValidateOriginLinkage_有前身且起源類型為受控值_合法(string originTransitionType)
    {
        var result = sut.ValidateOriginLinkage(Guid.NewGuid(), originTransitionType);

        Assert.True(result.IsLegal);
    }

    [Theory]
    [InlineData("conquered")] // 被滅亡不是起源方式，是終止方式
    [InlineData("unknown-type")]
    public void ValidateOriginLinkage_起源類型不是受控值_不合法(string originTransitionType)
    {
        var result = sut.ValidateOriginLinkage(Guid.NewGuid(), originTransitionType);

        Assert.False(result.IsLegal);
    }
}
