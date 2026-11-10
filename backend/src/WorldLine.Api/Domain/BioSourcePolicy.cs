using System.Text;

namespace WorldLine.Api.Domain;

/// <summary>
/// 生平 citation 的來源政策（ARCHITECTURE §16.4.4，B1「硬性排除層」，2026-11-10）。
/// 適用 leader_bio_field_citations、leader_record_citations 與日後的生平 citation 表；只做程式端檢查，寫入流程呼叫。
/// - 硬性排除：Wikipedia／Wikidata／百度、已知被接管網域、只標「自製」的出版者（沿用 gap-830 send_batch.py 與 HANDOFF 的實務規則）。
/// - 等級：T1 已決只收 A／B；C／X 不進 DB（留 seed）。未評等（NULL）允許寫入。DB 另有 CHECK（grade IN ('A','B')）。
/// - 引文 quote：≤ 80 字，只在程式檢查、不加 DB 約束（Tai 2026-11-10 21:52：來源區預設收合，只保留單句短引；原 25 字）。
///   「字」＝NFC 正規化後的字元（Unicode code point，.NET <see cref="Rune"/>；Tai 21:52 取代原 text element 計法）：
///   中文一字＝1、空白與標點各＝1；「é」NFC 後預組合＝1。不用 C# char（UTF-16 碼元）：CJK 擴充 B 區等字會被算成 2；也不用詞數。
/// - 白名單（Q5／T2 未決）：不在此實作；<see cref="PolicyVersion"/> 寫入 citation 的 policy_version，政策變動時據以重審。
/// </summary>
public static class BioSourcePolicy
{
    /// <summary>目前政策版本，寫入 citation.policy_version。規則變動時遞增。</summary>
    public const string PolicyVersion = "bio-2026-11-v0";

    /// <summary>引文上限（NFC 後的字元數，Unicode code point）。</summary>
    public const int QuoteMaxChars = 80;

    /// <summary>可寫入 DB 的等級（T1）。</summary>
    public static readonly IReadOnlySet<string> AllowedGrades = new HashSet<string>(StringComparer.Ordinal) { "A", "B" };

    /// <summary>T1 已定義、但不得進 DB 的等級（留 seed）。</summary>
    public static readonly IReadOnlySet<string> ExcludedGrades = new HashSet<string>(StringComparer.Ordinal) { "C", "X" };

    /// <summary>硬性排除的網域（含子網域）。</summary>
    public static readonly IReadOnlyList<string> ExcludedHosts =
    [
        "wikipedia.org", "wikidata.org", "baidu.com",
        "enciclopediadelecuador.com", // HANDOFF：網域已被接管（轉賭博站）
    ];

    /// <summary>出版者名稱含這些字（不分大小寫）即排除：避免以 Wikipedia／Wikidata／百度百科當出處但沒附網址。</summary>
    private static readonly string[] ExcludedPublisherFragments = ["wikipedia", "wikidata", "百度", "baidu"];

    /// <summary>引文長度（NFC 後的字元數，Unicode code point）。</summary>
    public static int QuoteLength(string quote) =>
        quote.Normalize(NormalizationForm.FormC).EnumerateRunes().Count();

    /// <summary>網址是否屬硬性排除網域；無法解析的網址回 false（由其他檢查處理）。</summary>
    public static bool IsExcludedUrl(string? url)
    {
        if (string.IsNullOrWhiteSpace(url) || !Uri.TryCreate(url.Trim(), UriKind.Absolute, out var u)) return false;
        var host = u.IdnHost.ToLowerInvariant().TrimEnd('.');
        return ExcludedHosts.Any(h => host == h || host.EndsWith("." + h, StringComparison.Ordinal));
    }

    public static bool IsExcludedPublisher(string? publisher) =>
        !string.IsNullOrWhiteSpace(publisher) &&
        (CitationPolicy.IsSelfMadePublisher(publisher) ||
         ExcludedPublisherFragments.Any(f => publisher.Contains(f, StringComparison.OrdinalIgnoreCase)));

    /// <summary>來源本身是否可當生平出處；不合格回原因，合格回 null。</summary>
    public static string? WhyNotQualifiedSource(Source source)
    {
        foreach (var url in new[] { source.Url, source.ArchiveUrl })
            if (IsExcludedUrl(url))
                return $"來源網址「{url}」屬硬性排除網域（{string.Join("、", ExcludedHosts)}）；不可當生平出處。";
        if (IsExcludedPublisher(source.Publisher))
            return $"出版者「{source.Publisher}」屬硬性排除（Wikipedia／Wikidata／百度或只標自製）；不可當生平出處。";
        return null;
    }

    /// <summary>等級檢查：NULL（未評等）可；A／B 可；C／X 依 T1 不進 DB；其他值無效。</summary>
    public static string? WhyGradeRejected(string? grade)
    {
        if (grade is null) return null;
        if (AllowedGrades.Contains(grade)) return null;
        if (ExcludedGrades.Contains(grade)) return $"來源等級 {grade} 不進 DB（T1：只收 A／B，C／X 留在 seed）。";
        return $"來源等級「{grade}」無效；只接受 A、B（或留空）。";
    }

    /// <summary>
    /// 引文檢查。<paramref name="required"/>＝true 時（新 citation 表，如 leader_record_citations）不可空；
    /// false 時（leader_bio_field_citations 舊列相容）可為 NULL，但給了就不可空白。
    /// </summary>
    public static string? WhyQuoteRejected(string? quote, bool required)
    {
        if (quote is null) return required ? "引文 quote 必填。" : null;
        if (string.IsNullOrWhiteSpace(quote)) return "引文 quote 不可空白。";
        var n = QuoteLength(quote);
        return n > QuoteMaxChars ? $"引文 {n} 字，超過 {QuoteMaxChars} 字上限（NFC 後以字元計）。" : null;
    }

    /// <summary>一筆生平 citation 的整體檢查；回所有不合格原因（空清單＝合格）。</summary>
    public static IReadOnlyList<string> Validate(Source source, string? quote, string? grade, bool quoteRequired)
    {
        var errors = new List<string>(3);
        if (WhyNotQualifiedSource(source) is { } s) errors.Add(s);
        if (WhyGradeRejected(grade) is { } g) errors.Add(g);
        if (WhyQuoteRejected(quote, quoteRequired) is { } q) errors.Add(q);
        return errors;
    }
}
