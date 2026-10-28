namespace WorldLine.Api.Domain;

/// <summary>政權他稱代稱。I4：必須以外鍵追溯回自稱政權本體，不可為孤兒資料。</summary>
public class RegimeAlias
{
    public Guid Id { get; set; }

    public Guid RegimeId { get; set; }
    public Regime Regime { get; set; } = null!;

    /// <summary>給予此代稱的觀察者政權（例：唐）；null 代表通用他稱。</summary>
    public Guid? ObserverRegimeId { get; set; }
    public Regime? ObserverRegime { get; set; }

    /// <summary>例：「大食」「拂菻」。</summary>
    public string AliasName { get; set; } = null!;

    /// <summary>見 <see cref="AliasPerspective"/>。</summary>
    public string AliasType { get; set; } = AliasPerspective.Contemporary;

    public DateTimeOffset CreatedAt { get; set; }
}
