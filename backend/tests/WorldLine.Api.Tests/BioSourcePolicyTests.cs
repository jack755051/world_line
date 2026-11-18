using WorldLine.Api.Domain;

namespace WorldLine.Api.Tests;

/// <summary>
/// 詳細人物生平 B1（ARCHITECTURE §16.4.4）：BioSourcePolicy 硬性排除層、等級、引文長度。純函式，不連資料庫。
/// </summary>
public class BioSourcePolicyTests
{
    private static Source Src(string? url = "https://catalogue.bnf.fr/ark:/12148/cb1", string publisher = "BnF", string? archive = null) =>
        new() { Title = "t", Publisher = publisher, Url = url, ArchiveUrl = archive, SourceKind = "official_record" };

    [Theory]
    [InlineData("https://en.wikipedia.org/wiki/X")]
    [InlineData("https://zh.m.wikipedia.org/wiki/X")]
    [InlineData("https://WIKIPEDIA.ORG/wiki/X")]
    [InlineData("https://www.wikidata.org/wiki/Q1")]
    [InlineData("https://baike.baidu.com/item/X")]
    [InlineData("http://enciclopediadelecuador.com/x")]
    public void Excluded_hosts_are_rejected(string url)
    {
        Assert.True(BioSourcePolicy.IsExcludedUrl(url));
        Assert.NotNull(BioSourcePolicy.WhyNotQualifiedSource(Src(url)));
    }

    [Theory]
    [InlineData("https://lex.dk/Arvid_Lindman")]
    [InlineData("https://id.loc.gov/authorities/names/n79093022.html")]
    [InlineData("https://notwikipedia.org/x")] // 只比對完整網域或子網域，不做子字串比對
    [InlineData("https://commons.wikimedia.org/wiki/File:X.jpg")] // 照片出處頁不屬硬性排除
    [InlineData(null)]
    [InlineData("not a url")]
    public void Other_hosts_are_not_excluded(string? url) => Assert.False(BioSourcePolicy.IsExcludedUrl(url));

    [Fact]
    public void Archive_url_on_excluded_host_is_also_rejected() =>
        Assert.NotNull(BioSourcePolicy.WhyNotQualifiedSource(Src(archive: "https://en.wikipedia.org/w/index.php?oldid=1")));

    [Theory]
    [InlineData("Wikipedia")]
    [InlineData("English Wikipedia")]
    [InlineData("百度百科")]
    [InlineData("自製")]
    [InlineData(" own work ")]
    public void Excluded_publishers_are_rejected(string publisher) =>
        Assert.NotNull(BioSourcePolicy.WhyNotQualifiedSource(Src(publisher: publisher)));

    [Fact]
    public void Qualified_source_passes() => Assert.Null(BioSourcePolicy.WhyNotQualifiedSource(Src()));

    [Theory]
    [InlineData(null, true)]
    [InlineData("A", true)]
    [InlineData("B", true)]
    [InlineData("C", true)]
    [InlineData("X", false)]
    [InlineData("a", false)]
    [InlineData("D", false)]
    [InlineData("", false)]
    public void Bio_grades_A_B_C_or_unrated(string? grade, bool ok) =>
        Assert.Equal(ok, BioSourcePolicy.WhyGradeRejected(grade) is null);

    [Theory]
    [InlineData(null, true)]
    [InlineData("A", true)]
    [InlineData("B", true)]
    [InlineData("C", false)]
    [InlineData("X", false)]
    public void Leader_record_usage_still_rejects_C(string? grade, bool ok) =>
        Assert.Equal(ok, BioSourcePolicy.WhyGradeRejected(grade, BioSourcePolicy.AllowedGrades) is null);

    [Fact]
    public void X_message_mentions_T1_revision() =>
        Assert.Contains("X 不入庫", BioSourcePolicy.WhyGradeRejected("X"));

    [Fact]
    public void Grade_sets_are_as_decided()
    {
        Assert.Equal(["A", "B"], BioSourcePolicy.AllowedGrades.Order());
        Assert.Equal(["A", "B", "C"], BioSourcePolicy.BioAllowedGrades.Order());
        Assert.Equal(["X"], BioSourcePolicy.ExcludedGrades.Order());
    }

    [Theory]
    [InlineData("一二三四五六七八九十一二三四五六七八九十一二三四五", 25)] // 中文一字＝1
    [InlineData("19. september 1862, Österby", 27)] // 拉丁字母、空白、標點各＝1
    [InlineData("Ö", 1)] // 預組合
    [InlineData("O\u0308", 1)] // O＋組合分音符：NFC 後預組合＝1
    [InlineData("e\u0323\u0301", 2)] // ẹ́ 無單一預組合字：NFC 後 ẹ＋組合尖音＝2（Tai 21:52 改以字元計，不再按 text element）
    [InlineData("𠀀𠀁", 2)] // CJK 擴充 B：UTF-16 各 2 個 char，但算 1 字
    [InlineData("👨\u200D👩\u200D👧", 5)] // ZWJ emoji 序列：3 個 emoji＋2 個 ZWJ＝5 字元
    public void Quote_length_counts_nfc_chars(string quote, int expected) =>
        Assert.Equal(expected, BioSourcePolicy.QuoteLength(quote));

    [Fact]
    public void Quote_limit_is_80_inclusive()
    {
        Assert.Equal(80, BioSourcePolicy.QuoteMaxChars);
        Assert.Null(BioSourcePolicy.WhyQuoteRejected(new string('字', 80), required: true));
        Assert.Contains("81 字", BioSourcePolicy.WhyQuoteRejected(new string('字', 81), required: true));
        // 以 char 計會是 160，但以字元（code point）計為 80：通過。
        Assert.Null(BioSourcePolicy.WhyQuoteRejected(string.Concat(Enumerable.Repeat("𠀀", 80)), required: true));
        // 組合符號 NFC 後預組合：80 個「O＋組合分音符」＝80 字。
        Assert.Null(BioSourcePolicy.WhyQuoteRejected(string.Concat(Enumerable.Repeat("O\u0308", 80)), required: true));
    }

    [Theory]
    [InlineData(null, true, false)]
    [InlineData(null, false, true)] // leader_bio_field_citations 舊列相容：可空
    [InlineData("  ", false, false)]
    [InlineData("", true, false)]
    [InlineData("b. 1862", true, true)]
    public void Quote_required_and_blank_rules(string? quote, bool required, bool ok) =>
        Assert.Equal(ok, BioSourcePolicy.WhyQuoteRejected(quote, required) is null);

    [Fact]
    public void Validate_collects_all_reasons()
    {
        Assert.Empty(BioSourcePolicy.Validate(Src(), "b. 1862", "A", quoteRequired: true));
        var errors = BioSourcePolicy.Validate(Src("https://en.wikipedia.org/wiki/X"), new string('x', 81), "X", quoteRequired: true);
        Assert.Equal(3, errors.Count);
    }

    [Fact]
    public void Policy_version_fits_db_column() =>
        Assert.InRange(BioSourcePolicy.PolicyVersion.Length, 1, 32);
}
