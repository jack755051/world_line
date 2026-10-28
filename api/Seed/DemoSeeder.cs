using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using WorldLine.Api.Api;
using WorldLine.Api.Data;
using WorldLine.Api.Domain;
using WorldLine.Api.Edtf;

namespace WorldLine.Api.Seed;

/// <summary>
/// 示範資料（可重複執行）：只新增不存在的資料、從不更新或刪除（符合 I5）。以固定 Guid／slug／名稱判斷是否已存在。
/// 年份為公認史實（天文紀年）；疆域一律是粗略「示意多邊形」（is_illustrative = true），非史料考據。
/// 執行：`dotnet WorldLine.Api.dll seed`（容器內）或 `dotnet run --project api -- seed`。
/// </summary>
public static class DemoSeeder
{
    public const string IllustrativeSource = "示意多邊形（非史料考據，僅供開發展示）";

    // ---- 固定 Id ----
    public static readonly Guid Han = new("0b1e0000-0000-4000-8000-000000000001");
    public static readonly Guid Wei = new("0b1e0000-0000-4000-8000-000000000002");
    public static readonly Guid ShuHan = new("0b1e0000-0000-4000-8000-000000000003");
    public static readonly Guid Wu = new("0b1e0000-0000-4000-8000-000000000004");
    public static readonly Guid Jin = new("0b1e0000-0000-4000-8000-000000000005");
    public static readonly Guid Tang = new("0b1e0000-0000-4000-8000-000000000006");
    public static readonly Guid Umayyad = new("0b1e0000-0000-4000-8000-000000000007");
    public static readonly Guid Abbasid = new("0b1e0000-0000-4000-8000-000000000008");

    private static readonly GeometryFactory F = new(new PrecisionModel(), 4326);

    private static MultiPolygon Poly(params (double X, double Y)[] pts) =>
        F.CreateMultiPolygon([F.CreatePolygon(pts.Select(p => new Coordinate(p.X, p.Y)).ToArray())]);

    // 粗略示意輪廓（經度, 緯度）
    private static readonly (double, double)[] China =
        [(98, 22), (108, 18), (122, 22), (123, 31), (122, 40), (118, 42), (105, 40), (98, 34), (98, 22)];
    private static readonly (double, double)[] North =
        [(101, 33), (110, 32.5), (120, 32.5), (122, 35), (122, 40), (118, 42), (105, 40), (101, 36), (101, 33)];
    private static readonly (double, double)[] SouthWest =
        [(98, 24), (106, 23), (110, 29), (110, 32.5), (101, 33), (98, 30), (98, 24)];
    private static readonly (double, double)[] SouthEast =
        [(106, 23), (108, 18), (122, 22), (123, 31), (120, 32.5), (110, 32.5), (110, 29), (106, 23)];
    private static readonly (double, double)[] NorthAndSouthWest =
        [(98, 24), (106, 23), (110, 29), (110, 32.5), (120, 32.5), (122, 35), (122, 40), (118, 42), (105, 40), (101, 36), (98, 30), (98, 24)];
    private static readonly (double, double)[] TangArea =
        [(75, 38), (80, 30), (98, 22), (108, 18), (122, 22), (123, 31), (125, 40), (120, 43), (105, 42), (90, 43), (75, 42), (75, 38)];
    private static readonly (double, double)[] UmayyadArea =
        [(-9, 36), (-9, 43), (3, 43), (35, 38), (70, 42), (72, 36), (68, 25), (45, 12), (33, 28), (-9, 36)];
    private static readonly (double, double)[] AbbasidArea =
        [(8, 30), (35, 38), (70, 42), (72, 36), (68, 25), (45, 12), (33, 28), (8, 30)];

    public static async Task<SeedReport> RunAsync(WorldLineDbContext db, CancellationToken ct = default)
    {
        var report = new SeedReport();
        await using var tx = await db.Database.BeginTransactionAsync(ct);

        await SeedRegimesAsync(db, report, ct);
        await SeedTerritoriesAsync(db, report, ct);
        await SeedRelationsAsync(db, report, ct);
        await SeedPresetsAsync(db, report, ct);
        await SeedReignErasAndPlacesAsync(db, report, ct);
        await SeedEventsAsync(db, report, ct);

        await tx.CommitAsync(ct);
        return report;
    }

    private static Regime R(Guid id, string self, int from, int to, string status,
        Guid? predecessor = null, string? origin = null, Guid? destroyedBy = null) => new()
    {
        Id = id, SelfName = self, ExistencePeriod = Ranges.Closed(from, to), Status = status,
        PredecessorRegimeId = predecessor, OriginTransitionType = origin, DestroyedByRegimeId = destroyedBy,
    };

    private static async Task SeedRegimesAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        // 憲法 §4 三國案例：漢 ─分裂→ 魏／蜀漢／吳；魏 ─禪讓→ 晉；蜀漢 亡於魏；吳 亡於晉。
        // 晉（316 亡於漢趙）、唐（907 禪讓後梁）、阿拔斯（1258 亡於蒙古）的終止方式尚未建檔，暫為 existing（有終止年）。
        var regimes = new List<Regime>
        {
            R(Han, "漢", 25, 220, RegimeStatus.Split),
            R(Wei, "魏", 220, 266, RegimeStatus.Abdicated, Han, OriginTransitionType.Split),
            R(ShuHan, "漢", 221, 263, RegimeStatus.Destroyed, Han, OriginTransitionType.Split, destroyedBy: Wei),
            R(Jin, "晉", 266, 316, RegimeStatus.Existing, Wei, OriginTransitionType.Abdication),
            R(Wu, "吳", 222, 280, RegimeStatus.Destroyed, Han, OriginTransitionType.Split, destroyedBy: Jin),
            R(Tang, "唐", 618, 907, RegimeStatus.Existing),
            R(Abbasid, "阿拔斯哈里發國", 750, 1258, RegimeStatus.Existing),
            R(Umayyad, "伍麥亞哈里發國", 661, 750, RegimeStatus.Destroyed, destroyedBy: Abbasid),
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
            (Han, null, "東漢", AliasPerspective.Historiographic),
            (Wei, null, "曹魏", AliasPerspective.Historiographic),
            (ShuHan, null, "蜀漢", AliasPerspective.Historiographic),
            (ShuHan, Wei, "蜀", AliasPerspective.Contemporary),
            (Wu, null, "東吳", AliasPerspective.Historiographic),
            (Wu, null, "孫吳", AliasPerspective.Historiographic),
            (Jin, null, "西晉", AliasPerspective.Historiographic),
            (Umayyad, Tang, "大食", AliasPerspective.Contemporary),
            (Umayyad, Tang, "白衣大食", AliasPerspective.Contemporary),
            (Umayyad, null, "阿拉伯帝國", AliasPerspective.Historiographic),
            (Umayyad, null, "伍麥亞王朝", AliasPerspective.Historiographic),
            (Abbasid, Tang, "大食", AliasPerspective.Contemporary),
            (Abbasid, Tang, "黑衣大食", AliasPerspective.Contemporary),
            (Abbasid, null, "阿拉伯帝國", AliasPerspective.Historiographic),
            (Abbasid, null, "阿拔斯王朝", AliasPerspective.Historiographic),
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
        (Guid Regime, int From, int To, (double, double)[] Shape)[] rows =
        [
            (Han, 25, 220, China),
            (Wei, 220, 266, North),
            (ShuHan, 221, 263, SouthWest),
            (Wu, 222, 280, SouthEast),
            (Jin, 266, 279, NorthAndSouthWest),
            (Jin, 280, 316, China),
            (Tang, 618, 907, TangArea),
            (Umayyad, 661, 750, UmayyadArea),
            (Abbasid, 750, 1258, AbbasidArea),
        ];
        var have = await db.RegimeTerritories.Where(t => t.SupersededBy == null)
            .Select(t => new { t.RegimeId, t.ValidPeriod }).ToListAsync(ct);
        foreach (var r in rows)
        {
            if (have.Any(h => h.RegimeId == r.Regime && Ranges.Lower(h.ValidPeriod) == r.From && Ranges.UpperInclusive(h.ValidPeriod) == r.To))
                continue;
            db.RegimeTerritories.Add(new RegimeTerritory
            {
                RegimeId = r.Regime, ValidPeriod = Ranges.Closed(r.From, r.To), Geom = Poly(r.Shape),
                IsIllustrative = true, Source = IllustrativeSource,
            });
            report.Territories++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedRelationsAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid A, Guid B, string Type, int From, int To, string Desc)[] rows =
        [
            (ShuHan, Wu, RelationType.Alliance, 223, 263, "吳蜀同盟：夷陵之戰後於 223 年重修舊好，至蜀漢滅亡"),
            (Wei, ShuHan, RelationType.Hostility, 221, 263, "魏蜀長期敵對（諸葛亮北伐、姜維北伐等）"),
            (Tang, Umayyad, RelationType.Trade, 661, 750, "唐與大食經陸上絲路及海路往來（示意區間：依政權存續）"),
            (Tang, Abbasid, RelationType.Trade, 750, 907, "唐與大食經陸上絲路及海路往來（示意區間：依政權存續）"),
        ];
        var have = await db.RegimeRelations.Select(r => new { r.RegimeAId, r.RegimeBId, r.RelationType }).ToListAsync(ct);
        foreach (var r in rows.Where(r => !have.Any(h => h.RegimeAId == r.A && h.RegimeBId == r.B && h.RelationType == r.Type)))
        {
            db.RegimeRelations.Add(new RegimeRelation
            {
                RegimeAId = r.A, RegimeBId = r.B, RelationType = r.Type, ValidPeriod = Ranges.Closed(r.From, r.To), Description = r.Desc,
            });
            report.Relations++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedPresetsAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (string Name, string Desc, bool IsDefault, Guid[] Members)[] presets =
        [
            ("傳統教科書史觀", "以禪讓相承為正統主線：東漢 → 曹魏 → 西晉（陳壽《三國志》以魏為本紀）", true, [Han, Wei, Jin]),
            ("蜀漢正統論史觀", "以漢室血脈為正統：東漢 → 蜀漢 → 西晉（如習鑿齒、朱熹《資治通鑑綱目》）", false, [Han, ShuHan, Jin]),
        ];
        foreach (var p in presets)
        {
            if (await db.LineagePresets.AnyAsync(x => x.PresetName == p.Name, ct)) continue;
            if (p.IsDefault && await db.LineagePresets.AnyAsync(x => x.IsDefault, ct)) continue;
            var preset = new LineagePreset { PresetName = p.Name, Description = p.Desc, IsDefault = p.IsDefault };
            for (var i = 0; i < p.Members.Length; i++)
                preset.Members.Add(new LineagePresetMember { RegimeId = p.Members[i], SortOrder = i });
            db.LineagePresets.Add(preset);
            report.Presets++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedReignErasAndPlacesAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        (Guid Regime, string Era, string Monarch, int From, int To)[] eras =
        [
            (Han, "建安", "漢獻帝", 196, 220),
            (Wei, "黃初", "魏文帝", 220, 226),
            (ShuHan, "章武", "漢昭烈帝", 221, 223),
            (Wu, "黃武", "吳大帝", 222, 229),
            (Jin, "泰始", "晉武帝", 265, 274),
            (Tang, "開元", "唐玄宗", 713, 741),
            (Tang, "天寶", "唐玄宗", 742, 756),
        ];
        var have = await db.ReignEras.Select(e => new { e.RegimeId, e.EraName, e.StartYear }).ToListAsync(ct);
        foreach (var e in eras.Where(e => !have.Any(h => h.RegimeId == e.Regime && h.EraName == e.Era && h.StartYear == e.From)))
        {
            db.ReignEras.Add(new ReignEra { RegimeId = e.Regime, EraName = e.Era, MonarchName = e.Monarch, StartYear = e.From, EndYear = e.To });
            report.ReignEras++;
        }

        (string Name, string? Modern, int From, int To, double X, double Y)[] places =
        [
            ("長安", "西安", -201, 904, 108.94, 34.26),
            ("建業", "南京", 212, 280, 118.78, 32.06),
        ];
        var havePlaces = await db.PlaceNames.Select(p => p.HistoricalName).ToListAsync(ct);
        foreach (var p in places.Where(p => !havePlaces.Contains(p.Name)))
        {
            db.PlaceNames.Add(new PlaceName
            {
                HistoricalName = p.Name, ModernName = p.Modern, ValidPeriod = Ranges.Closed(p.From, p.To),
                Geom = F.CreatePoint(new Coordinate(p.X, p.Y)),
            });
            report.Places++;
        }
        await db.SaveChangesAsync(ct);
    }

    private static async Task SeedEventsAsync(WorldLineDbContext db, SeedReport report, CancellationToken ct)
    {
        foreach (var name in new[] { "國際第三者（當代旁觀）", "後世史學界（事後回顧）" })
        {
            if (!await db.ObserverCategories.AnyAsync(c => c.CategoryName == name, ct))
                db.ObserverCategories.Add(new ObserverCategory { CategoryName = name });
        }
        foreach (var tag in new[] { "war", "conquest", "abdication", "trade", "treaty" })
        {
            if (!await db.EventTags.AnyAsync(t => t.TagName == tag, ct))
                db.EventTags.Add(new EventTag { TagName = tag });
        }
        await db.SaveChangesAsync(ct);
        var tags = await db.EventTags.ToDictionaryAsync(t => t.TagName, t => t.Id, ct);
        var historians = await db.ObserverCategories.Where(c => c.CategoryName == "後世史學界（事後回顧）").Select(c => c.Id).SingleAsync(ct);

        (string Id, string Name, string Start, string End, double X, double Y, string[] Tags)[] events =
        [
            ("battle-of-red-cliffs-208", "赤壁之戰", "0208~", "0208~", 113.62, 29.87, ["war"]),
            ("han-abdication-to-wei-220", "漢獻帝禪讓曹丕", "0220", "0220", 113.85, 34.03, ["abdication"]),
            ("wei-conquers-shu-263", "魏滅蜀漢", "0263", "0263", 104.06, 30.67, ["war", "conquest"]),
            ("jin-conquers-wu-280", "晉滅吳", "0279", "0280", 118.78, 32.06, ["war", "conquest"]),
            ("battle-of-talas-751", "怛羅斯之戰", "0751-07~", "0751-07~", 71.40, 42.90, ["war"]),
        ];
        foreach (var e in events)
        {
            if (await db.HistoricalEvents.AnyAsync(x => x.Id == e.Id, ct)) continue;
            var ev = new HistoricalEvent
            {
                Id = e.Id, Name = e.Name, StartEdtf = e.Start, EndEdtf = e.End,
                StartDecimal = EdtfDate.Parse(e.Start).EarliestDecimal,
                EndDecimal = EdtfDate.Parse(e.End).LatestDecimal,
                OriginPoint = F.CreatePoint(new Coordinate(e.X, e.Y)),
            };
            foreach (var t in e.Tags) ev.Tags.Add(new HistoricalEventTagMap { TagId = tags[t] });
            db.HistoricalEvents.Add(ev);
            report.Events++;

            if (e.Id == "battle-of-talas-751")
            {
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = Tang, LocalName = "怛羅斯之戰",
                    NarrativeSummary = "唐安西節度使高仙芝率軍西進，與大食（阿拔斯）及葛邏祿聯軍交戰於怛羅斯，唐軍敗退。",
                    PrimarySources = """["《資治通鑑》卷二一六","杜環《經行記》（《通典》引錄）"]""",
                });
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    RegimeId = Abbasid, LocalName = "塔拉斯河之戰（معركة نهر طلاس）",
                    NarrativeSummary = "阿拔斯軍於塔拉斯河畔擊敗唐軍，鞏固在河中地區的勢力。",
                });
                ev.Perspectives.Add(new HistoricalEventPerspective
                {
                    ObserverCategoryId = historians, LocalName = "怛羅斯之戰",
                    NarrativeSummary = "常被視為唐在中亞擴張受挫的標誌之一；其長期影響（相較於 755 年安史之亂）在學界仍有討論。",
                });
                ev.Controversies.Add(new HistoricalEventControversy
                {
                    Topic = "造紙術是否因此役西傳",
                    NeutralDescription = "傳統說法認為此役被俘的唐朝工匠將造紙術帶到撒馬爾罕；部分近代研究認為造紙術西傳的時間與途徑另有可能。",
                    Viewpoints = """
                        [{"holder":"傳統說法","summary":"被俘工匠在撒馬爾罕開始造紙","sources":["杜環《經行記》（《通典》引錄）"]},
                         {"holder":"部分近代研究","summary":"造紙術可能更早或經其他管道西傳，751 年之說證據有限","sources":["Jonathan M. Bloom, Paper Before Print (2001)"]}]
                        """,
                });
            }
        }
        await db.SaveChangesAsync(ct);
    }
}

public sealed class SeedReport
{
    public int Regimes { get; set; }
    public int Aliases { get; set; }
    public int Territories { get; set; }
    public int Relations { get; set; }
    public int Presets { get; set; }
    public int ReignEras { get; set; }
    public int Places { get; set; }
    public int Events { get; set; }

    public override string ToString() =>
        $"regimes+{Regimes} aliases+{Aliases} territories+{Territories} relations+{Relations} presets+{Presets} reign_eras+{ReignEras} places+{Places} events+{Events}";
}
