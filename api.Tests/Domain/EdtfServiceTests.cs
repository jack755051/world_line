using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests.Domain;

/// <summary>
/// task 2.15：task 2.2（EDTF 子集解析＋`NodaTime` 曆法換算）第一批正式單元測試——2.2
/// 動工當時只做了 15 組手動 console 驗證（見 implementation plan），這裡補上自動化
/// 迴歸測試，含閏年邊界案例。
/// </summary>
public class EdtfServiceTests
{
    private readonly EdtfService sut = new();

    [Fact]
    public void TryParse_年精度()
    {
        var result = sut.TryParse("0208");

        Assert.True(result.IsValid);
        Assert.Equal(208, result.Date!.Value.Year);
        Assert.Null(result.Date.Value.Month);
        Assert.Null(result.Date.Value.Day);
        Assert.Equal(EdtfPrecision.Year, result.Date.Value.Precision);
        Assert.Equal(208.000m, result.Date.Value.ToDecimalYear());
    }

    [Fact]
    public void TryParse_年月精度()
    {
        var result = sut.TryParse("0220-11");

        Assert.True(result.IsValid);
        Assert.Equal(11, result.Date!.Value.Month);
        Assert.Equal(EdtfPrecision.Month, result.Date.Value.Precision);
    }

    [Fact]
    public void TryParse_年月日精度()
    {
        var result = sut.TryParse("0220-11-25");

        Assert.True(result.IsValid);
        Assert.Equal(11, result.Date!.Value.Month);
        Assert.Equal(25, result.Date.Value.Day);
        Assert.Equal(EdtfPrecision.Day, result.Date.Value.Precision);
    }

    [Fact]
    public void TryParse_負年份代表西元前_絕對紀年慣例()
    {
        // EDTF/ISO 8601 絕對紀年：西元 0 年＝西元前 1 年，字串裡的負號直接對應絕對紀年
        // 的負數，見 EdtfService 類別文件——這裡驗證秦朝建立年（西元前 221 年）解析出
        // 絕對紀年 -221，不是 -220（差一年是最容易犯錯的地方）。
        var result = sut.TryParse("-0221");

        Assert.True(result.IsValid);
        Assert.Equal(-221, result.Date!.Value.Year);
    }

    [Theory]
    [InlineData("1900-02-29", false)] // 世紀年，不被 400 整除，不是閏年
    [InlineData("2000-02-29", true)] // 世紀年，被 400 整除，是閏年
    [InlineData("2024-02-29", true)] // 一般年份，被 4 整除，是閏年
    [InlineData("2023-02-29", false)] // 一般年份，不被 4 整除，不是閏年
    public void TryParse_閏年邊界案例(string edtf, bool expectedValid)
    {
        var result = sut.TryParse(edtf);

        Assert.Equal(expectedValid, result.IsValid);
    }

    [Theory]
    [InlineData("0220-13-01")] // 月份不存在
    [InlineData("0220-02-30")] // 2 月沒有 30 日
    [InlineData("0220-00-01")] // 月份 0 不合法
    [InlineData("0220-01-00")] // 日期 0 不合法
    public void TryParse_不存在的日期不合法(string edtf)
    {
        var result = sut.TryParse(edtf);

        Assert.False(result.IsValid);
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData(null)]
    public void TryParse_空字串或null不合法(string? edtf)
    {
        var result = sut.TryParse(edtf);

        Assert.False(result.IsValid);
    }

    [Theory]
    [InlineData("abc")] // 完全不是日期格式
    [InlineData("220")] // 年份不是 4 位數
    [InlineData("22000")] // 年份超過 4 位數
    [InlineData("0220/11/25")] // 分隔符號錯誤（不是連字號）
    public void TryParse_不符合支援子集格式的字串不合法(string edtf)
    {
        var result = sut.TryParse(edtf);

        Assert.False(result.IsValid);
    }

    [Fact]
    public void TryParse_問號尾綴代表不確定()
    {
        var result = sut.TryParse("0220?");

        Assert.True(result.IsValid);
        Assert.Equal(EdtfQualifier.Uncertain, result.Date!.Value.Qualifier);
        Assert.Equal(220, result.Date.Value.Year); // 尾綴不影響底層數值本身
    }

    [Fact]
    public void TryParse_波浪號尾綴代表約略推測()
    {
        var result = sut.TryParse("0220~");

        Assert.True(result.IsValid);
        Assert.Equal(EdtfQualifier.Approximate, result.Date!.Value.Qualifier);
    }

    [Fact]
    public void TryParse_沒有尾綴時是確定日期()
    {
        var result = sut.TryParse("0220");

        Assert.True(result.IsValid);
        Assert.Equal(EdtfQualifier.None, result.Date!.Value.Qualifier);
    }

    [Fact]
    public void ToDecimalYear_同一年內較晚的日期換算出較大的小數年份()
    {
        // 對應 task 3.4 種子資料：漢獻帝禪位於魏事件的兩個真實日期（0220-11-25 早於
        // 0220-12-11），換算出的小數年份順序要跟日期順序一致，才能拿來排序/比較。
        var earlier = sut.TryParse("0220-11-25").Date!.Value.ToDecimalYear();
        var later = sut.TryParse("0220-12-11").Date!.Value.ToDecimalYear();

        Assert.True(earlier < later);
        Assert.InRange(earlier, 220m, 221m);
        Assert.InRange(later, 220m, 221m);
    }
}
