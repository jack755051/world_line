using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Api;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;
using WorldLine.Api.Edtf;

namespace WorldLine.Api.Seed;

/// <summary>
/// 二戰示範資料（憲法 2026-10-28：二戰為第一階段，主範圍 1937-07-07～1945-09-02，滿洲國 1931 起為前情）。
/// 日期為公認史實；疆域與佔領區一律為粗略示意多邊形（is_illustrative = true，source 註明），非史料考據。
/// 只新增不存在的資料，不更新、不刪除（I5）。由 <see cref="DemoSeeder.RunAsync"/> 呼叫。
/// </summary>
public static class Ww2Seeder
{
    public const string IllustrativeSource = "示意多邊形（非史料考據，僅供開發展示；二戰示範資料）";

    public static readonly Guid Germany = new("0b1e0000-0000-4000-8000-000000000101");
    public static readonly Guid Japan = new("0b1e0000-0000-4000-8000-000000000102");
    public static readonly Guid Italy = new("0b1e0000-0000-4000-8000-000000000103");
    public static readonly Guid UnitedKingdom = new("0b1e0000-0000-4000-8000-000000000104");
    public static readonly Guid UnitedStates = new("0b1e0000-0000-4000-8000-000000000105");
    public static readonly Guid SovietUnion = new("0b1e0000-0000-4000-8000-000000000106");
    public static readonly Guid RepublicOfChina = new("0b1e0000-0000-4000-8000-000000000107");
    public static readonly Guid Manchukuo = new("0b1e0000-0000-4000-8000-000000000108");
    public static readonly Guid VichyFrance = new("0b1e0000-0000-4000-8000-000000000109");
    public static readonly Guid FrenchRepublic = new("0b1e0000-0000-4000-8000-000000000110");
    public static readonly Guid Austria = new("0b1e0000-0000-4000-8000-000000000111");

    public static readonly Guid Axis = new("0b1e0000-0000-4000-8000-000000000201");
    public static readonly Guid Allies = new("0b1e0000-0000-4000-8000-000000000202");

    private static readonly GeometryFactory F = new(new PrecisionModel(), 4326);

    private static MultiPolygon Poly(params (double X, double Y)[] pts) =>
        F.CreateMultiPolygon([F.CreatePolygon(pts.Select(p => new Coordinate(p.X, p.Y)).ToArray())]);

    // ---- 粗略示意輪廓（經度, 緯度）----
    private static readonly (double, double)[] GermanyPre1938 =
        [(6, 51), (6, 47.5), (13, 47.5), (15, 51), (14, 54), (9, 55), (6, 53.5), (6, 51)];
    private static readonly (double, double)[] GreaterGermany =
        [(6, 51), (6, 47.5), (9.5, 47.3), (10, 46.4), (14, 46.4), (17, 48), (15, 49), (15, 51), (14, 54), (9, 55), (6, 53.5), (6, 51)];
    private static readonly (double, double)[] AustriaArea =
        [(9.5, 47.3), (10, 46.4), (14, 46.4), (17, 48), (15, 49), (13, 48.6), (13, 47.5), (9.5, 47.3)];
    private static readonly (double, double)[] ItalyArea =
        [(7, 44), (8, 46.5), (13.5, 46.5), (13.5, 45.5), (12.5, 44), (16, 41.5), (18.5, 40), (16, 38), (15.5, 40), (12, 42), (10.5, 43.5), (7, 44)];
    private static readonly (double, double)[] GreatBritain =
        [(-5.8, 50), (1.8, 51), (1.8, 52.9), (-2, 55.8), (-1.8, 57.6), (-3, 58.7), (-6.2, 58.5), (-5.6, 55.3), (-3.2, 54), (-4.5, 52.8), (-5.3, 51.7), (-5.8, 50)];
    private static readonly (double, double)[] ContiguousUs =
        [(-124.5, 48.5), (-95, 49), (-83, 46), (-67, 47), (-70, 41.5), (-75.5, 35.2), (-80.5, 25.2), (-82.5, 28), (-85, 29.5), (-89.5, 29.5), (-97.3, 26), (-106.5, 31.8), (-117, 32.5), (-124, 40.5), (-124.5, 48.5)];
    private static readonly (double, double)[] SovietArea =
        [(22, 55), (27, 69.5), (60, 70), (100, 77), (179.9, 69), (170, 60), (143, 51), (135, 43), (120, 49), (87, 49), (80, 42), (67, 37), (53, 37), (48, 38.5), (40, 43), (32, 46), (22, 48), (22, 55)];
    private static readonly (double, double)[] ChinaDeJure =
        [(98, 22), (108, 18), (122, 22), (122.5, 31), (122, 40), (125, 40), (131, 43), (134, 48), (127, 53), (120, 53), (116, 46), (105, 42), (96, 42), (80, 40), (74, 37), (78, 32), (92, 28), (98, 28), (98, 22)];
    private static readonly (double, double)[] JapanArea =
        [(130, 31), (131.5, 31.3), (135, 33.5), (140, 35), (141, 38), (142, 41.5), (140, 41), (139, 38), (136.5, 37), (133, 35.5), (130.8, 34), (129.5, 33.2), (130, 31)];
    private static readonly (double, double)[] ManchukuoArea =
        [(119, 40), (122, 40), (125, 40), (131, 43), (134, 48), (127, 53), (120, 53), (116, 46), (117, 42), (119, 40)];
    private static readonly (double, double)[] FranceArea =
        [(-4.8, 48.4), (-1.5, 43.4), (3, 42.4), (7.5, 43.8), (6.5, 46.5), (8.2, 49), (2.5, 51.1), (-1.5, 49.7), (-4.8, 48.4)];
    private static readonly (double, double)[] VichyFreeZone =
        [(-0.2, 43.0), (3, 42.4), (7.5, 43.8), (6.0, 46.4), (4.5, 46.6), (1.5, 47.0), (0.0, 46.2), (-0.2, 43.0)];
    private static readonly (double, double)[] FranceOccupiedZone =
        [(-4.8, 48.4), (-1.5, 43.4), (-0.2, 43.0), (0.0, 46.2), (1.5, 47.0), (4.5, 46.6), (6.0, 46.4), (6.5, 46.5), (8.2, 49), (2.5, 51.1), (-1.5, 49.7), (-4.8, 48.4)];
    private static readonly (double, double)[] JapaneseOccupiedChina =
        [(110, 22), (114, 22), (121, 28), (122, 31), (122, 40), (118, 40), (112, 38), (110, 32), (110, 22)];

    public static async Task RunAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        await SeedRegimesAsync(db, report, ct);
        await SeedTerritoriesAsync(db, report, ct);
        await SeedControlRelationsAsync(db, report, ct);
        await SeedAlliancesAsync(db, report, ct);
        await SeedReignErasAsync(db, report, ct);
        await SeedEventsAsync(db, report, ct);
    }

    private static Regime R(Guid id, string self, string from, string? to, string status = RegimeStatus.Existing,
        Guid? destroyedBy = null, Guid? annexedBy = null)
    {
        var (range, fp, tp) = Periods.Parse(from, to);
        return new Regime
        {
            Id = id, SelfName = self, ExistencePeriod = range, ExistenceFromPrecision = fp, ExistenceToPrecision = tp,
            Status = status, DestroyedByRegimeId = destroyedBy, AnnexedByRegimeId = annexedBy,
        };
    }

    private static async Task SeedRegimesAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        // 無終點 = 本階段（至 1945-09-02）未記錄終止；法蘭西國的終止方式尚未建檔，暫為 existing（有終止日）
        var regimes = new List<Regime>
        {
            R(Germany, "德意志國", "1871-01-18", null),
            R(Japan, "大日本帝國", "1868", null),
            R(Italy, "義大利王國", "1861-03-17", null),
            R(UnitedKingdom, "大不列顛及北愛爾蘭聯合王國", "1927-04-12", null),
            R(UnitedStates, "美利堅合眾國", "1776-07-04", null),
            R(SovietUnion, "蘇維埃社會主義共和國聯盟", "1922-12-30", null),
            R(RepublicOfChina, "中華民國", "1912-01-01", null),
            R(FrenchRepublic, "法蘭西共和國", "1870-09-04", null),
            R(Manchukuo, "滿洲國", "1932-03-01", "1945-08-18", RegimeStatus.Destroyed, destroyedBy: SovietUnion),
            R(VichyFrance, "法蘭西國", "1940-07-10", "1944-08-20"),
            R(Austria, "奧地利聯邦國", "1934-05-01", "1938-03-13", RegimeStatus.Annexed, annexedBy: Germany),
        };
        var existing = await db.Regimes.Select(r => r.Id).ToListAsync(ct);
        foreach (var r in regimes.Where(r => !existing.Contains(r.Id)))
        {
            db.Regimes.Add(r);
            report.Regimes++;
        }
        await db.SaveChangesAsync(ct);

        (Guid Regime, Guid? Observer, string Name, string Type)[] aliases =
        [
            (Germany, null, "德國", AliasPerspective.Contemporary),
            (Germany, null, "納粹德國", AliasPerspective.Historiographic),
            (Germany, null, "第三帝國", AliasPerspective.Historiographic),
            (Japan, null, "日本", AliasPerspective.Contemporary),
            (Italy, null, "義大利", AliasPerspective.Contemporary),
            (UnitedKingdom, null, "英國", AliasPerspective.Contemporary),
            (UnitedStates, null, "美國", AliasPerspective.Contemporary),
            (SovietUnion, null, "蘇聯", AliasPerspective.Contemporary),
            (RepublicOfChina, null, "中國", AliasPerspective.Contemporary),
            (FrenchRepublic, null, "法國", AliasPerspective.Contemporary),
            (Austria, null, "奧地利", AliasPerspective.Contemporary),
            // 定性用語屬觀察視角他稱（憲法 §6 2026-10-28）：系統不定性，只記錄誰這樣稱呼
            (Manchukuo, RepublicOfChina, "偽滿洲國", AliasPerspective.Contemporary),
            (Manchukuo, null, "滿洲帝國", AliasPerspective.Contemporary),
            (VichyFrance, null, "維希法國", AliasPerspective.Historiographic),
        ];
        var have = await db.RegimeAliases.Select(a => new { a.RegimeId, a.ObserverRegimeId, a.AliasName }).ToListAsync(ct);
        foreach (var a in aliases.Where(a => !have.Any(h => h.RegimeId == a.Regime && h.ObserverRegimeId == a.Observer && h.AliasName == a.Name)))
        {
            db.RegimeAliases.Add(new RegimeAlias { RegimeId = a.Regime, ObserverRegimeId = a.Observer, AliasName = a.Name, AliasType = a.Type });
            report.Aliases++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedTerritoriesAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid Regime, string From, string To, (double, double)[] Shape)[] rows =
        [
            (Germany, "1937-07-07", "1938-03-12", GermanyPre1938),
            (Germany, "1938-03-13", "1945-05-08", GreaterGermany),
            (Austria, "1937-07-07", "1938-03-12", AustriaArea),
            (Italy, "1937-07-07", "1945-09-02", ItalyArea),
            (UnitedKingdom, "1937-07-07", "1945-09-02", GreatBritain),
            (UnitedStates, "1937-07-07", "1945-09-02", ContiguousUs),
            (SovietUnion, "1937-07-07", "1945-09-02", SovietArea),
            (RepublicOfChina, "1937-07-07", "1945-09-02", ChinaDeJure),
            (Japan, "1937-07-07", "1945-09-02", JapanArea),
            (Manchukuo, "1932-03-01", "1945-08-18", ManchukuoArea),
            (FrenchRepublic, "1937-07-07", "1945-09-02", FranceArea),
            (VichyFrance, "1940-07-10", "1944-08-20", VichyFreeZone),
        ];
        var have = await db.RegimeTerritories.Where(t => t.SupersededBy == null)
            .Select(t => new { t.RegimeId, t.ValidPeriod }).ToListAsync(ct);
        foreach (var r in rows)
        {
            var (range, fp, tp) = Periods.Parse(r.From, r.To);
            if (have.Any(h => h.RegimeId == r.Regime && Periods.SameSpan(h.ValidPeriod, range))) continue;
            db.RegimeTerritories.Add(new RegimeTerritory
            {
                RegimeId = r.Regime, ValidPeriod = range, ValidFromPrecision = fp, ValidToPrecision = tp!,
                Geom = Poly(r.Shape), IsIllustrative = true, Source = IllustrativeSource,
            });
            report.Territories++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedControlRelationsAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid Controller, Guid Controlled, string Type, string From, string To, (double, double)[]? Area, bool Disputed, string Desc)[] rows =
        [
            (Japan, Manchukuo, ControlType.Puppet, "1932-03-01", "1945-08-18", null, false,
                "日本關東軍扶植溥儀建立滿洲國，實際由日本控制（九一八事變後的前情，憲法 §1）"),
            (Japan, RepublicOfChina, ControlType.Occupation, "1937-07-29", "1945-09-09", JapaneseOccupiedChina, false,
                "日軍佔領華北、華東、華南沿海等地（1937-07-29 北平淪陷起；1945-09-09 南京受降）。佔領範圍隨戰事變動，此為示意"),
            (Germany, FrenchRepublic, ControlType.Occupation, "1940-06-22", "1944-08-25", FranceOccupiedZone, false,
                "《貢比涅停戰協定》後德軍佔領法國北部與大西洋沿岸（佔領區），至巴黎解放。1942-11-11 起德軍亦進佔南部（見對法蘭西國的佔領）"),
            (Germany, VichyFrance, ControlType.Occupation, "1942-11-11", "1944-08-20", null, false,
                "安東行動：德軍進佔維希政府管轄的南部自由區"),
            (Germany, VichyFrance, ControlType.Puppet, "1940-07-10", "1944-08-20", null, true,
                "維希政府與德國的關係性質史學上有爭議（合作政權 vs. 傀儡政權），故標為爭議"),
        ];
        var have = await db.RegimeControlRelations
            .Select(c => new { c.ControllerRegimeId, c.ControlledRegimeId, c.ControlType, c.ValidPeriod }).ToListAsync(ct);
        foreach (var r in rows)
        {
            var (range, fp, tp) = Periods.Parse(r.From, r.To);
            if (have.Any(h => h.ControllerRegimeId == r.Controller && h.ControlledRegimeId == r.Controlled && h.ControlType == r.Type
                              && Periods.SameSpan(h.ValidPeriod, range))) continue;
            db.RegimeControlRelations.Add(new RegimeControlRelation
            {
                ControllerRegimeId = r.Controller, ControlledRegimeId = r.Controlled, ControlType = r.Type,
                ValidPeriod = range, ValidFromPrecision = fp, ValidToPrecision = tp!,
                Area = r.Area is null ? null : Poly(r.Area), IsIllustrative = r.Area is not null,
                IsDisputed = r.Disputed, Description = r.Desc,
                Source = r.Area is null ? null : IllustrativeSource,
            });
            report.ControlRelations++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedAlliancesAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid Id, string Name, string From, string? To, string Desc)[] alliances =
        [
            (Axis, "軸心國", "1936-10-25", "1945-09-02", "1936-10-25 羅馬－柏林軸心成立；1940-09-27《三國同盟條約》納入日本；至 1945-09-02 日本簽署降書"),
            (Allies, "同盟國", "1942-01-01", null, "以 1942-01-01《聯合國家宣言》為成立日（此前已有英、法等對德作戰的同盟關係）"),
        ];
        var have = await db.Alliances.Select(a => a.Id).ToListAsync(ct);
        foreach (var a in alliances.Where(a => !have.Contains(a.Id)))
        {
            var (range, fp, tp) = Periods.Parse(a.From, a.To);
            db.Alliances.Add(new Alliance
            {
                Id = a.Id, SelfName = a.Name, Description = a.Desc,
                ExistencePeriod = range, ExistenceFromPrecision = fp, ExistenceToPrecision = tp,
            });
            report.Alliances++;
        }
        await db.SaveChangesAsync(ct);

        (Guid Alliance, Guid? Observer, string Name, string Type)[] aliases =
        [
            (Axis, Japan, "樞軸國", AliasPerspective.Contemporary),
            (Allies, null, "聯合國家", AliasPerspective.Contemporary),
        ];
        var haveAliases = await db.AllianceAliases.Select(a => new { a.AllianceId, a.ObserverRegimeId, a.AliasName }).ToListAsync(ct);
        foreach (var a in aliases.Where(a => !haveAliases.Any(h => h.AllianceId == a.Alliance && h.ObserverRegimeId == a.Observer && h.AliasName == a.Name)))
            db.AllianceAliases.Add(new AllianceAlias { AllianceId = a.Alliance, ObserverRegimeId = a.Observer, AliasName = a.Name, AliasType = a.Type });
        await db.SaveChangesAsync(ct);

        (Guid Alliance, Guid Regime, string Role, string From, string? To, string? Note)[] members =
        [
            (Axis, Germany, MembershipRole.Member, "1936-10-25", "1945-05-08", "1945-05-08 德國無條件投降"),
            (Axis, Italy, MembershipRole.Member, "1936-10-25", "1943-09-08", "1943-09-03 秘密簽署《卡西比萊停戰協定》，09-08 公布，退出軸心"),
            (Axis, Japan, MembershipRole.Member, "1940-09-27", "1945-09-02", "1940-09-27《三國同盟條約》"),
            (Allies, UnitedStates, MembershipRole.Member, "1942-01-01", null, "《聯合國家宣言》簽署國"),
            (Allies, UnitedKingdom, MembershipRole.Member, "1942-01-01", null, "《聯合國家宣言》簽署國"),
            (Allies, SovietUnion, MembershipRole.Member, "1942-01-01", null, "《聯合國家宣言》簽署國"),
            (Allies, RepublicOfChina, MembershipRole.Member, "1942-01-01", null, "《聯合國家宣言》簽署國"),
            (Allies, Italy, MembershipRole.CoBelligerent, "1943-10-13", null, "1943-10-13 義大利（巴多格里奧政府）對德宣戰，成為共同交戰國"),
        ];
        var haveMembers = await db.AllianceMemberships.Select(m => new { m.AllianceId, m.RegimeId, m.ValidPeriod }).ToListAsync(ct);
        foreach (var m in members)
        {
            var (range, fp, tp) = Periods.Parse(m.From, m.To);
            if (haveMembers.Any(h => h.AllianceId == m.Alliance && h.RegimeId == m.Regime && Periods.SameSpan(h.ValidPeriod, range))) continue;
            db.AllianceMemberships.Add(new AllianceMembership
            {
                AllianceId = m.Alliance, RegimeId = m.Regime, Role = m.Role, Note = m.Note,
                ValidPeriod = range, ValidFromPrecision = fp, ValidToPrecision = tp,
            });
            report.Memberships++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedReignErasAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid Regime, string Era, string? Monarch, string From, string? To)[] eras =
        [
            (Japan, "昭和", "昭和天皇", "1926-12-25", "1989-01-07"),
            (RepublicOfChina, "民國", null, "1912-01-01", null),
            (Manchukuo, "大同", "溥儀", "1932-03-01", "1934-02-28"),
            (Manchukuo, "康德", "溥儀", "1934-03-01", "1945-08-18"),
        ];
        var have = await db.ReignEras.Select(e => new { e.RegimeId, e.EraName, e.StartDate }).ToListAsync(ct);
        foreach (var e in eras)
        {
            PartialDate.TryParse(e.From, out var from, out _);
            PartialDate? to = null;
            if (e.To is not null) PartialDate.TryParse(e.To, out to, out _);
            if (have.Any(h => h.RegimeId == e.Regime && h.EraName == e.Era && h.StartDate == from!.Earliest)) continue;
            db.ReignEras.Add(new ReignEra
            {
                RegimeId = e.Regime, EraName = e.Era, MonarchName = e.Monarch,
                StartDate = from!.Earliest, StartPrecision = from.Precision,
                EndDate = to?.Latest, EndPrecision = to?.Precision,
            });
            report.ReignEras++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedEventsAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        var tags = await db.EventTags.ToDictionaryAsync(t => t.TagName, t => t.Id, ct);
        const string Ww2 = "second-world-war";
        (string Id, string Name, string? Parent, string Start, string End, string? Tz, string? Note, double X, double Y, string[] Tags)[] events =
        [
            (Ww2, "第二次世界大戰", null, "1939-09-01", "1945-09-02", null,
                "歐洲戰場通常以 1939-09-01 德國入侵波蘭起算；本專案二戰階段範圍自 1937-07-07 盧溝橋事變起（憲法 §1）",
                10.0, 50.0, ["war"]),
            ("marco-polo-bridge-incident-1937", "盧溝橋事變", null, "1937-07-07", "1937-07-07", "Asia/Shanghai",
                "當地時間 1937-07-07 夜間至 07-08 凌晨", 116.21, 39.85, ["war"]),
            ("anschluss-1938", "德奧合併", Ww2, "1938-03-12", "1938-03-13", "Europe/Vienna",
                "03-12 德軍進入奧地利，03-13 公布《德奧合併法》", 16.37, 48.21, ["annexation"]),
            ("invasion-of-poland-1939", "德國入侵波蘭", Ww2, "1939-09-01", "1939-10-06", "Europe/Warsaw",
                "1939-09-01 當地時間清晨 04:45 起", 18.67, 54.41, ["war"]),
            ("attack-on-pearl-harbor-1941", "珍珠港事件", Ww2, "1941-12-07", "1941-12-07", "Pacific/Honolulu",
                "攻擊始於當地時間 1941-12-07 07:48（當時夏威夷時間 UTC−10:30）；同一時刻為 UTC 1941-12-07 18:18、日本時間 1941-12-08 03:18（UTC+9），日本史料多記為 12 月 8 日",
                -157.95, 21.36, ["war"]),
            ("italian-armistice-1943", "義大利停戰", Ww2, "1943-09-03", "1943-09-08", "Europe/Rome",
                "1943-09-03 於西西里卡西比萊秘密簽署，09-08 公布", 15.20, 36.97, ["treaty", "surrender"]),
            ("japanese-surrender-1945", "日本簽署降書", Ww2, "1945-09-02", "1945-09-02", "Asia/Tokyo",
                "於東京灣美艦密蘇里號簽署（當地時間上午）；同一時刻美國本土仍為 1945-09-01", 139.75, 35.35, ["surrender"]),
        ];
        foreach (var e in events)
        {
            if (await db.HistoricalEvents.AnyAsync(x => x.Id == e.Id, ct)) continue;
            var ev = new HistoricalEvent
            {
                Id = e.Id, Name = e.Name, ParentEventId = e.Parent, StartEdtf = e.Start, EndEdtf = e.End,
                StartDecimal = EdtfDate.Parse(e.Start).EarliestDecimal,
                EndDecimal = EdtfDate.Parse(e.End).LatestDecimal,
                TimeZone = e.Tz, TimeNote = e.Note,
                OriginPoint = F.CreatePoint(new Coordinate(e.X, e.Y)),
            };
            foreach (var t in e.Tags) ev.Tags.Add(new HistoricalEventTagMap { TagId = tags[t] });

            if (e.Id == "attack-on-pearl-harbor-1941")
            {
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = UnitedStates, LocalName = "Attack on Pearl Harbor（珍珠港事件）",
                    NarrativeSummary = "日本海軍航艦部隊未經宣戰突襲夏威夷珍珠港美國太平洋艦隊，美國翌日對日宣戰。",
                    OfficialJustification = "羅斯福稱 12 月 7 日為「國恥日（a date which will live in infamy）」",
                });
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = Japan, LocalName = "真珠灣攻擊（真珠湾攻撃）",
                    NarrativeSummary = "日本海軍機動部隊空襲夏威夷珍珠港，作為對美、英開戰的首波作戰之一；日方記為昭和 16 年 12 月 8 日。",
                });
            }
            if (e.Id == "marco-polo-bridge-incident-1937")
            {
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = RepublicOfChina, LocalName = "七七事變（盧溝橋事變）",
                    NarrativeSummary = "日軍藉口士兵失蹤，要求進入宛平縣城搜查遭拒，隨即攻擊盧溝橋與宛平，中國軍隊抵抗，全面抗戰開始。",
                });
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = Japan, LocalName = "盧溝橋事件",
                    NarrativeSummary = "日方稱中國軍隊先開槍引發衝突，事件擴大為日本所稱的「支那事變」（日華事變）。",
                });
            }
            db.HistoricalEvents.Add(ev);
            report.Events++;
            await db.SaveChangesAsync(ct); // 逐筆存，確保父事件先存在
        }
    }
}
