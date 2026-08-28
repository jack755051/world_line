using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NpgsqlTypes;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data;

/// <summary>
/// Plan task 1.7 seed data — Han/Wei/Shu-Han/Wu/Jin, chosen because the constitution's own §4
/// worked example uses exactly this case (分裂/被取代禪讓/被滅亡 all appear). Idempotent: skips
/// entirely if regimes already exist, so it's safe to call on every startup.
///
/// ⚠️ Geometries are rough illustrative rectangles, not historically accurate boundaries — this
/// is schema/relationship test data, not a real dataset. Years are simplified round numbers for
/// the same reason (e.g. treating all three post-Han regimes as splitting off in exactly 220).
/// </summary>
public static class SeedData
{
    public static async Task SeedAsync(WorldLineDbContext db)
    {
        if (await db.Regimes.AnyAsync())
        {
            return;
        }

        var gf = NetTopologySuite.NtsGeometryServices.Instance.CreateGeometryFactory(srid: 4326);

        MultiPolygon Rect(double minLon, double minLat, double maxLon, double maxLat)
        {
            var shell = new[]
            {
                new Coordinate(minLon, minLat),
                new Coordinate(minLon, maxLat),
                new Coordinate(maxLon, maxLat),
                new Coordinate(maxLon, minLat),
                new Coordinate(minLon, minLat),
            };
            return gf.CreateMultiPolygon([gf.CreatePolygon(shell)]);
        }

        static NpgsqlRange<int> Years(int start, int end) => new(start, true, end, false);

        // --- Regimes + transition edges (方案 D: 客觀轉換邊，不判斷正統) ---

        var han = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "漢",
            Status = "分裂",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var wei = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "魏",
            Status = "被取代(禪讓)",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "分裂",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var shuHan = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "蜀漢",
            Status = "被滅亡",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "分裂",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var wu = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "吳",
            Status = "被滅亡",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "分裂",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var jin = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "晉",
            Status = "存續",
            PredecessorRegimeId = wei.Id,
            OriginTransitionType = "被取代禪讓",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        // Fill in destroyed_by now that the destroyer regimes exist.
        shuHan.DestroyedByRegimeId = wei.Id; // 263
        wu.DestroyedByRegimeId = jin.Id;     // 280

        db.Regimes.AddRange(han, wei, shuHan, wu, jin);

        // --- Regime aliases (I4: 他稱代稱，FK 必須指回明確存在的自稱政權本體) ---
        // AliasType 刻意留 null——PRD §12 TODO：alias_type 受控值須在 M2 alias API 前拍板，
        // 這裡先不腦補分類，避免種子資料把未拍板的欄位值變相定案。

        db.RegimeAliases.AddRange(
            new RegimeAlias { Id = Guid.NewGuid(), RegimeId = wei.Id, ObserverRegimeId = shuHan.Id, AliasName = "賊", CreatedAt = DateTimeOffset.UtcNow }, // 蜀漢文書視角（如《出師表》「漢賊不兩立」）稱魏為賊，帶政治立場的他稱
            new RegimeAlias { Id = Guid.NewGuid(), RegimeId = wu.Id, ObserverRegimeId = null, AliasName = "孫吳", CreatedAt = DateTimeOffset.UtcNow } // 後世史家為與其他「吳」政權（如十國吳）區隔而使用，無特定觀察政權視角
        );

        // --- Lineage preset (方案 D: 史觀主線，跟核心政權圖解耦) ---

        var textbookPreset = new LineagePreset
        {
            Id = Guid.NewGuid(),
            PresetName = "傳統教科書史觀",
            Description = "漢→魏→晉正線傳承，蜀漢/東吳為分裂期政權，不列入本 preset（但仍完整存在於 regimes 表）",
            CreatedAt = DateTimeOffset.UtcNow,
        };
        db.LineagePresets.Add(textbookPreset);
        db.LineagePresetMembers.AddRange(
            new LineagePresetMember { PresetId = textbookPreset.Id, RegimeId = han.Id, SortOrder = 1 },
            new LineagePresetMember { PresetId = textbookPreset.Id, RegimeId = wei.Id, SortOrder = 2 },
            new LineagePresetMember { PresetId = textbookPreset.Id, RegimeId = jin.Id, SortOrder = 3 }
        );

        // 第二個 preset：蜀漢正統論史觀（習鑿齒《漢晉春秋》東晉首倡、朱熹《資治通鑑綱目》南宋承襲）。
        // 刻意用同一組客觀轉換邊資料選出不同主線，驗證方案 D 真的把「正統判斷」解耦成可並存的
        // 呈現層：蜀漢的 regimes.status 是「被滅亡」而非「被取代(禪讓)」，本 preset 仍把它放進
        // 主線並直接跳過魏，證明 preset 成員資格不需要遵循 predecessor_regime_id 那條客觀邊。
        var shuHanOrthodoxPreset = new LineagePreset
        {
            Id = Guid.NewGuid(),
            PresetName = "蜀漢正統論史觀",
            Description = "以蜀漢承續漢室為正統，曹魏視為篡逆不列入主線。蜀漢 263 年滅亡後正統視為中斷，"
                + "晉直到 280 年統一天下才被追認為正統延續——理由是「統一天下」而非「受魏禪讓」，跟"
                + "傳統教科書史觀收錄晉的理由不同。此史觀分歧與東晉／南宋兩個偏安江南政權各自需要"
                + "「正統可在南方存續」的政治類比有關，詳見下方 event-han-abdicates-wei-220 的爭議點記錄。",
            CreatedAt = DateTimeOffset.UtcNow,
        };
        db.LineagePresets.Add(shuHanOrthodoxPreset);
        db.LineagePresetMembers.AddRange(
            new LineagePresetMember { PresetId = shuHanOrthodoxPreset.Id, RegimeId = han.Id, SortOrder = 1 },
            new LineagePresetMember { PresetId = shuHanOrthodoxPreset.Id, RegimeId = shuHan.Id, SortOrder = 2 },
            new LineagePresetMember { PresetId = shuHanOrthodoxPreset.Id, RegimeId = jin.Id, SortOrder = 3 }
        );

        // --- Place names (憲法 §6：地名雙軌顯示，古名為主、現代名括號對照) ---
        // 洛陽兩筆示範「同一地點、名稱隨政權更迭而變」：東漢五德屬火，忌水克火，故避諱寫作
        // 「雒陽」；曹魏受禪後改回「洛陽」（魏屬土德，土不畏水）。這個改字本身就是政權正統敘事
        // 的具體展演，跟下方「正統性」爭議點記錄互相呼應。

        db.PlaceNames.AddRange(
            new PlaceName { Id = Guid.NewGuid(), HistoricalName = "雒陽", ModernName = "洛陽", ValidPeriod = Years(25, 220), Geom = gf.CreatePoint(new Coordinate(112.45, 34.62)), CreatedAt = DateTimeOffset.UtcNow }, // 東漢首都，避水德諱寫作「雒」
            new PlaceName { Id = Guid.NewGuid(), HistoricalName = "洛陽", ModernName = null, ValidPeriod = Years(220, 316), Geom = gf.CreatePoint(new Coordinate(112.45, 34.62)), CreatedAt = DateTimeOffset.UtcNow }, // 魏/西晉首都，改回「洛」；古今同名，ModernName 依規範留空
            new PlaceName { Id = Guid.NewGuid(), HistoricalName = "成都", ModernName = null, ValidPeriod = Years(221, 263), Geom = gf.CreatePoint(new Coordinate(104.06, 30.57)), CreatedAt = DateTimeOffset.UtcNow }, // 蜀漢首都，古今同名
            new PlaceName { Id = Guid.NewGuid(), HistoricalName = "建業", ModernName = "南京", ValidPeriod = Years(222, 280), Geom = gf.CreatePoint(new Coordinate(118.78, 32.06)), CreatedAt = DateTimeOffset.UtcNow } // 東吳首都
        );

        // --- Reign eras (§5 拍板: 自建查詢表) ---

        db.ReignEras.AddRange(
            new ReignEra { Id = Guid.NewGuid(), RegimeId = han.Id, EraName = "建安", StartYear = 196, EndYear = 220, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = wei.Id, EraName = "黃初", StartYear = 220, EndYear = 226, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = shuHan.Id, EraName = "章武", StartYear = 221, EndYear = 223, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = shuHan.Id, EraName = "建興", StartYear = 223, EndYear = 237, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = wu.Id, EraName = "黃武", StartYear = 222, EndYear = 229, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = jin.Id, EraName = "泰始", StartYear = 265, EndYear = 274, CreatedAt = DateTimeOffset.UtcNow }
        );

        // --- Territory snapshots (事件驅動密度 — 荊州爭奪戰讓蜀漢/東吳的快照比穩定期政權密集) ---

        // I5 版本鏈的機械驗證（先前完全沒有種子資料測過 SupersededBy 這條 FK 路徑）：初版粗略依現代
        // 省界估計東漢疆域，之後依《後漢書·郡國志》十三州範圍修正，補上西南（益州）與西北（涼州）。
        // 原始列不刪除，只把 SupersededBy 指向修正列，並記錄修正原因與時間戳（憲法 I5、§8「類 git」）。
        // ⚠️ 這裡驗證的是「這條 FK 鏈能不能正確 insert/查詢」，不是 M2 應用層的修正端點行為本身
        // （新增新版本、擋直接 UPDATE/DELETE 那套流程邏輯留給 2.7，見 implementation plan）。
        var hanTerritory1Original = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = han.Id,
            ValidPeriod = Years(25, 189),
            Geom = Rect(102, 24, 118, 38), // 初版：粗略依現代省界估計，範圍偏保守
            CreatedAt = DateTimeOffset.UtcNow,
        };
        var hanTerritory1Corrected = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = han.Id,
            ValidPeriod = Years(25, 189),
            Geom = Rect(100, 20, 122, 40), // 修正版：納入益州、涼州後範圍擴大
            CreatedAt = DateTimeOffset.UtcNow,
        };
        hanTerritory1Original.SupersededBy = hanTerritory1Corrected.Id;
        hanTerritory1Original.CorrectionReason = "初版依現代省界粗略估計，範圍偏保守；依《後漢書·郡國志》十三州記載修正，補上西南益州與西北涼州轄境";
        hanTerritory1Original.CorrectedAt = DateTimeOffset.UtcNow;

        db.RegimeTerritories.AddRange(
            // 漢：3 筆（穩定期政權，快照較疏）——前 2 筆是上方 I5 版本鏈示範（同一時間區間的原始版 + 修正版）
            hanTerritory1Original,
            hanTerritory1Corrected,
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = han.Id, ValidPeriod = Years(189, 220), Geom = Rect(102, 22, 120, 38), CreatedAt = DateTimeOffset.UtcNow },

            // 魏：3 筆
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(220, 226), Geom = Rect(105, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(226, 249), Geom = Rect(104, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(249, 265), Geom = Rect(104, 32, 123, 42), CreatedAt = DateTimeOffset.UtcNow },

            // 蜀漢：5 筆，208/215/219 荊州易手區間刻意加密
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(208, 215), Geom = Rect(100, 26, 114, 32), IsDisputed = true, CorrectionReason = null, CreatedAt = DateTimeOffset.UtcNow }, // 借荊州（版本 A：含江陵以東）
            // I3 測試用：同一政權、同一時間區間的第二筆爭議版本——史料對「借荊州」實際控制範圍記載不一，
            // 兩筆皆標 IsDisputed=true 且互不 supersede（I5 修正鏈是「新版本取代舊版本」，這裡是「同期並存的兩種史觀」，語意不同）。
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(208, 215), Geom = Rect(100, 26, 111, 32), IsDisputed = true, CreatedAt = DateTimeOffset.UtcNow }, // 借荊州（版本 B：僅含南郡以西，較保守估計）
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(215, 219), Geom = Rect(100, 26, 111, 32), CreatedAt = DateTimeOffset.UtcNow }, // 215 孫劉分荊州後縮小
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(219, 221), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 219 失荊州
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(221, 263), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 正式建國後穩定期（益州核心）

            // 東吳：4 筆，同樣在荊州易手區間加密
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(208, 215), Geom = Rect(112, 22, 122, 32), IsDisputed = true, CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(215, 219), Geom = Rect(111, 22, 122, 32), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(219, 222), Geom = Rect(108, 22, 122, 32), CreatedAt = DateTimeOffset.UtcNow }, // 219 呂蒙奪荊州後擴大
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(222, 280), Geom = Rect(108, 20, 122, 32), CreatedAt = DateTimeOffset.UtcNow },

            // 西晉：2 筆
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = jin.Id, ValidPeriod = Years(265, 280), Geom = Rect(104, 32, 123, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = jin.Id, ValidPeriod = Years(280, 316), Geom = Rect(100, 20, 123, 42), CreatedAt = DateTimeOffset.UtcNow } // 統一後涵蓋原吳蜀疆域
        );

        // --- Regime relation (持續性關係，非離散事件) ---

        db.RegimeRelations.Add(new RegimeRelation
        {
            Id = Guid.NewGuid(),
            RegimeAId = shuHan.Id,
            RegimeBId = wu.Id,
            RelationType = "同盟",
            ValidPeriod = Years(208, 219),
            Description = "赤壁之戰前後孫劉聯盟，共同抵禦曹操；219 年因荊州歸屬爭議破裂",
            CreatedAt = DateTimeOffset.UtcNow,
        });

        // --- Historical events (事件骨幹 + 標籤 + 多重視角 + 爭議點 + 政權轉換邊連結) ---
        // 此前 9 張表（含此區塊涵蓋的 6 張）完全沒有種子資料，M2 事件相關端點（2.10-2.13）開發時無資料可測。
        // 赤壁之戰示範「事件→多重視角→爭議點」；兩筆滅國之戰示範 RegimeTransitionEvent 連結轉換邊與觸發事件。

        var chibi = new HistoricalEvent
        {
            Id = "event-chibi-208",
            Name = "赤壁之戰",
            StartEdtf = "0208",
            EndEdtf = "0208",
            StartDecimal = 208.000m,
            EndDecimal = 208.000m, // 簡化為整年，精確月份（約農曆十月）待正式資料匯入時用 EDTF 月精度取代
            Sections = """{"background":"曹操率軍南下欲統一天下，孫權、劉備結盟共同抵禦","turning_points":["黃蓋詐降","火攻連環船"],"impact":"曹操退回北方，奠定日後三國鼎立雛形"}""",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var shuConquest = new HistoricalEvent
        {
            Id = "event-shu-conquest-263",
            Name = "魏滅蜀之戰",
            StartEdtf = "0263",
            EndEdtf = "0263",
            StartDecimal = 263.000m,
            EndDecimal = 263.000m,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var wuConquest = new HistoricalEvent
        {
            Id = "event-wu-conquest-280",
            Name = "西晉滅吳之戰",
            StartEdtf = "0280",
            EndEdtf = "0280",
            StartDecimal = 280.000m,
            EndDecimal = 280.000m,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        db.HistoricalEvents.AddRange(chibi, shuConquest, wuConquest);

        // 兩筆禪讓事件：先前 RegimeTransitionEvent 只示範過 TransitionKind='destruction'（滅國之戰），
        // 'origin' 分支（分裂/禪讓觸發的建國）完全沒有種子資料驗證過。這兩筆同時也是三國正統之爭
        // 的具體歷史錨點（見下方爭議點記錄）。
        var hanAbdicatesWei = new HistoricalEvent
        {
            Id = "event-han-abdicates-wei-220",
            Name = "漢獻帝禪位於魏（曹丕受禪）",
            StartEdtf = "0220",
            EndEdtf = "0220",
            StartDecimal = 220.000m,
            EndDecimal = 220.000m,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var weiAbdicatesJin = new HistoricalEvent
        {
            Id = "event-wei-abdicates-jin-265",
            Name = "魏元帝禪位於晉（司馬炎受禪）",
            StartEdtf = "0265",
            EndEdtf = "0265",
            StartDecimal = 265.000m,
            EndDecimal = 265.000m,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        db.HistoricalEvents.AddRange(hanAbdicatesWei, weiAbdicatesJin);

        // Id 顯式指定（非留給 identity-by-default 產生）：historical_event_tag_map 的
        // TagId 是純 int 外鍵欄位、沒有導覽屬性，EF Core 無法在 SaveChanges 前自動補上
        // 資料庫產生的值，必須先有已知 Id 才能組 join row。
        var warTag = new EventTag { Id = 1, TagName = "戰爭" };
        var successionTag = new EventTag { Id = 2, TagName = "政權更替" };
        db.EventTags.AddRange(warTag, successionTag);

        // RegimeTransitionEvent：把既有的轉換邊（1.4/1.7 建立時只記錄「發生過」）連回「是哪個事件
        // 導致的」——這正是 7eb6a4b 新增這張表要解決的問題。'destruction' 分支先前已驗證過（滅蜀/滅
        // 吳），這裡補上 'origin' 分支：魏的起源轉換連回漢禪魏事件、晉的起源轉換連回魏禪晉事件。
        db.RegimeTransitionEvents.AddRange(
            new RegimeTransitionEvent { RegimeId = shuHan.Id, EventId = shuConquest.Id, TransitionKind = "destruction" },
            new RegimeTransitionEvent { RegimeId = wu.Id, EventId = wuConquest.Id, TransitionKind = "destruction" },
            new RegimeTransitionEvent { RegimeId = wei.Id, EventId = hanAbdicatesWei.Id, TransitionKind = "origin" },
            new RegimeTransitionEvent { RegimeId = jin.Id, EventId = weiAbdicatesJin.Id, TransitionKind = "origin" }
        );

        var laterHistorians = new ObserverCategory { Id = 1, CategoryName = "後世史學界（事後回顧）" };
        db.ObserverCategories.Add(laterHistorians);

        db.HistoricalEventTagMaps.AddRange(
            new HistoricalEventTagMap { EventId = chibi.Id, TagId = warTag.Id },
            new HistoricalEventTagMap { EventId = shuConquest.Id, TagId = warTag.Id },
            new HistoricalEventTagMap { EventId = shuConquest.Id, TagId = successionTag.Id },
            new HistoricalEventTagMap { EventId = wuConquest.Id, TagId = warTag.Id },
            new HistoricalEventTagMap { EventId = wuConquest.Id, TagId = successionTag.Id },
            // 禪讓事件刻意只掛「政權更替」、不掛「戰爭」——跟滅蜀/滅吳形成對照，示範同一個
            // event_tags 集合能區分「和平轉移」與「武力消滅」兩種性質的政權更替（多對多標籤設計原則）。
            new HistoricalEventTagMap { EventId = hanAbdicatesWei.Id, TagId = successionTag.Id },
            new HistoricalEventTagMap { EventId = weiAbdicatesJin.Id, TagId = successionTag.Id }
        );

        // 多重視角：示範「regime_id 路徑」與「observer_category_id 路徑」兩種（PRD §6：至少擇一非 NULL）
        db.HistoricalEventPerspectives.AddRange(
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = chibi.Id,
                RegimeId = shuHan.Id,
                LocalName = "孫劉聯軍視角",
                NarrativeSummary = "曹操大軍壓境，孫劉兩家結盟，以火攻大破曹軍水寨，聯軍以寡擊眾",
                OfficialJustification = "抵禦北方統一威脅，保全江東與荊州根基",
            },
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = chibi.Id,
                ObserverCategoryId = laterHistorians.Id,
                LocalName = "後世史學界考據",
                NarrativeSummary = "對曹操南征兵力規模、黃蓋詐降細節與火攻具體戰術的史料考證整理，各家說法不一",
                PrimarySources = """[{"title":"三國志","author":"陳壽","year":280},{"title":"資治通鑑","author":"司馬光","year":1084}]""",
            }
        );

        // 爭議點：真實存在的史學爭議（曹操自稱兵力與後世估算落差極大），非虛構案例
        db.HistoricalEventControversies.Add(new HistoricalEventControversy
        {
            Id = Guid.NewGuid(),
            EventId = chibi.Id,
            Topic = "曹操南征兵力數字爭議",
            NeutralDescription = "曹操檄文自稱「今治水軍八十萬眾」，但《三國志》裴松之注引周瑜語稱其實際「眾數雖多，甚未足畏」；後世史學家依糧秣運輸與戰場記載推估實際兵力遠不足八十萬，確切數字至今無定論。",
            Viewpoints = """[{"stance":"曹操自稱八十萬眾","source":"曹操檄文（《三國志·吳書·周瑜傳》引）"},{"stance":"實際兵力約二十餘萬","source":"後世學者依糧秣/運輸能力推算"}]""",
        });

        // 正統性爭議：三國史學史上最著名的史觀分歧，直接對應方案 D（lineage_presets 解耦設計）
        // 存在的理由——不同時代的史書基於自身政權的政治處境，對「誰是正統」給出不同答案，掛在
        // 漢禪魏這個事件上，因為這正是分歧的起點。
        db.HistoricalEventControversies.Add(new HistoricalEventControversy
        {
            Id = Guid.NewGuid(),
            EventId = hanAbdicatesWei.Id,
            Topic = "三國正統歸屬爭議（尊魏 vs 尊蜀漢）",
            NeutralDescription = "陳壽《三國志》成書於西晉（西晉受禪自魏），以〈魏書〉為本紀，尊魏為正統；"
                + "東晉習鑿齒《漢晉春秋》改帝蜀寇魏，尊蜀漢為漢室正統延續；南宋朱熹《資治通鑑綱目》"
                + "承襲此說。三派分歧不完全出於史料本身的差異，而與各自成書朝代的政治處境相關——"
                + "西晉的合法性建立在承接魏的禪讓之上，東晉／南宋則是偏安江南的政權，需要「正統可在"
                + "南方存續」的歷史類比，蜀漢的處境正好提供了這個先例。",
            Viewpoints = """[{"stance":"尊魏為正統","source":"陳壽《三國志》（西晉，280年成書）"},{"stance":"尊蜀漢為正統","source":"習鑿齒《漢晉春秋》（東晉）"},{"stance":"承襲蜀漢正統說","source":"朱熹《資治通鑑綱目》（南宋）"}]""",
        });

        await db.SaveChangesAsync();
    }
}
