using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NpgsqlTypes;
using WorldLine.Api.Data.Entities;
using WorldLine.Api.Domain;

namespace WorldLine.Api.Data;

/// <summary>
/// Plan task 1.7 seed data — Han/Wei/Shu-Han/Wu/Jin, chosen because the constitution's own §4
/// worked example uses exactly this case (分裂/被取代禪讓/被滅亡 all appear). Idempotent: skips
/// entirely if regimes already exist, so it's safe to call on every startup.
///
/// ⚠️ Geometries are rough illustrative rectangles, not historically accurate boundaries — this
/// is schema/relationship test data, not a real dataset. Years are simplified round numbers for
/// the same reason (e.g. treating all three post-Han regimes as splitting off in exactly 220).
///
/// **2026-08-31 追加：唐朝／伍麥亞王朝／阿拔斯王朝**（task 3.8 後補，見檔案內該區塊的
/// 說明）——PRD Story 3 AC#2 舉例的「唐朝視角看阿拉伯帝國稱大食」在三國種子資料裡沒有
/// 對應案例，這批資料補上真正的例子（含怛羅斯之戰這個唐朝與阿拉伯帝國唯一真實接觸
/// 點），跟三國那批資料之間（189-618 年）刻意留白，不是遺漏。
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

        // Status/OriginTransitionType 用中立英文代碼存（'active'|'split'|'succeeded'|'conquered'），
        // 不用中文字面值——憲法 §4 的「存續／分裂／被取代(禪讓)／被滅亡」是業務概念的權威定義，
        // 這裡只是它在資料庫的編碼方式。2026-08-28 從中文字面值改過來：中文字面值當 enum 用，
        // 套到非中國政權（例如歐洲史的合併、羅馬共和轉帝制）會很勉強，且已經在只有 5 筆資料時
        // 就出現同一概念兩種寫法飄掉的情況（status 用過「被取代(禪讓)」、origin_transition_type
        // 用過「被取代禪讓」，一個有括號一個沒有）。改成代碼後 UI/文件層再依語系對照回中文顯示。
        var han = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "漢",
            Status = "split",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var wei = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "魏",
            Status = "succeeded",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "split",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var shuHan = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "蜀漢",
            Status = "conquered",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "split",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var wu = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "吳",
            Status = "conquered",
            PredecessorRegimeId = han.Id,
            OriginTransitionType = "split",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var jin = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "晉",
            Status = "active",
            PredecessorRegimeId = wei.Id,
            OriginTransitionType = "succeeded",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        // Fill in destroyed_by now that the destroyer regimes exist.
        shuHan.DestroyedByRegimeId = wei.Id; // 263
        wu.DestroyedByRegimeId = jin.Id;     // 280

        db.Regimes.AddRange(han, wei, shuHan, wu, jin);

        // --- Regime aliases (I4: 他稱代稱，FK 必須指回明確存在的自稱政權本體) ---
        // AliasType 2026-08-30 起有值（task 2.9a 拍板受控值，見 RegimeAliasType 類別
        // 說明）——這兩筆本來就是決定分類依據時參考的真實案例：「賊」是政治敵意稱呼，
        // 「孫吳」是無關特定視角的史學消歧義稱呼，兩者理由本質不同。

        // 改成有名稱的變數（而非匿名 inline new），才能在下方 content_translations 區塊引用它們的 Id。
        var weiAlias = new RegimeAlias { Id = Guid.NewGuid(), RegimeId = wei.Id, ObserverRegimeId = shuHan.Id, AliasName = "賊", AliasType = RegimeAliasType.Political, CreatedAt = DateTimeOffset.UtcNow }; // 蜀漢文書視角（如《出師表》「漢賊不兩立」）稱魏為賊，帶政治立場的他稱
        var wuAlias = new RegimeAlias { Id = Guid.NewGuid(), RegimeId = wu.Id, ObserverRegimeId = null, AliasName = "孫吳", AliasType = RegimeAliasType.Scholarly, CreatedAt = DateTimeOffset.UtcNow }; // 後世史家為與其他「吳」政權（如十國吳）區隔而使用，無特定觀察政權視角
        db.RegimeAliases.AddRange(weiAlias, wuAlias);

        // --- Lineage preset (方案 D: 史觀主線，跟核心政權圖解耦) ---

        var textbookPreset = new LineagePreset
        {
            Id = Guid.NewGuid(),
            PresetName = "傳統教科書史觀",
            Description = "漢→魏→晉正線傳承，蜀漢/東吳為分裂期政權，不列入本 preset（但仍完整存在於 regimes 表）",
            IsDefault = true, // task 2.8：PRD Story 4 AC#3 的預設主線視圖，兩個 preset 只有這筆標 true
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
            // 漢：4 筆——前 2 筆是上方 I5 版本鏈示範（同一時間區間的原始版 + 修正版，涵蓋 25-189 年）。
            // 189-220 年這段原本只有 1 筆涵蓋全境的示意矩形，跟同期蜀漢/吳的疆域整塊重疊，
            // 沒有反映赤壁之戰後三方實際割據的局面——189-208 年劉備/孫權尚未成勢，維持原本
            // 涵蓋全境的示意範圍；208 年（赤壁之戰、劉備借荊州）之後拆一筆出來，縮小到約略等於
            // 曹操實際控制的地盤（漢獻帝這時只是曹操的傀儡，朝廷名義上的疆域跟曹操實際地盤是
            // 兩回事，208 年後兩者已經高度重合）——直接沿用魏建國第一筆疆域的座標，因為魏 220
            // 年建國（漢禪魏）是「曹操實際控制的地盤，透過禪讓儀式換了個名字跟名義上的皇帝」，
            // 不是「打下新的領土」，兩者地理範圍理論上該是同一塊，不是巧合。
            hanTerritory1Original,
            hanTerritory1Corrected,
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = han.Id, ValidPeriod = Years(189, 208), Geom = Rect(102, 22, 120, 38), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = han.Id, ValidPeriod = Years(208, 220), Geom = Rect(105, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow }, // 縮小至約等於曹操實際控制地盤（=魏建國時的疆域，見上方說明）

            // 魏：4 筆——249-265 這筆（北方核心）維持不變，另外新增 263-265 這筆（南方，
            // 263 年滅蜀後接管蜀漢原本的地盤）。**2026-08-30 修正**：原本只有北方核心
            // 這 3 筆，263 年蜀漢滅亡後，蜀漢原本的疆域（益州）直接從地圖上消失、變成
            // 無主之地，沒有反映「魏滅蜀」這個事件實際發生的地盤轉移（使用者實機發現
            // 這個問題）。座標沿用蜀漢滅亡前最後一筆疆域 `Rect(100,26,108,32)`——跟漢
            // 禪魏那筆的處理原則一樣：政權更迭（不管是和平禪讓還是被滅國攻佔）不會讓
            // 已經被佔領的土地憑空消失或變成新開墾的無主地，疆域理論上該直接銜接原本
            // 的控制範圍。魏在 263-265 年因此同時有兩筆疆域記錄（北方核心+南方新併入的
            // 蜀地），不是同一個政權自己內部的爭議（不會畫紅色斜線，見圖著色跟重疊區
            // 判斷都是用 regimeId 分組，同政權多筆疆域一律用同一個顏色表示）。
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(220, 226), Geom = Rect(105, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(226, 249), Geom = Rect(104, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(249, 265), Geom = Rect(104, 32, 123, 42), CreatedAt = DateTimeOffset.UtcNow }, // 北方核心，263 滅蜀後維持不變
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(263, 265), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 263 滅蜀新增——座標沿用蜀漢滅亡前最後一筆疆域

            // 蜀漢：5 筆，208/215/219 荊州易手區間刻意加密。208-215 拆成兩筆——「核心」
            // （南郡以西，孫氏從沒質疑過）跟「荊州爭議地帶」，跟下面東吳的爭議地帶用**完全
            // 相同的座標**（2026-08-29 使用者拍板：爭議區的定義是「雙方宣稱的範圍本身就是
            // 同一塊」，類比現實的喀什米爾爭議——印巴雙方對「爭議區」認定的範圍是同一塊，
            // 不是「我宣稱這一大塊、你宣稱那一大塊，剛好有一小段重疊」。原本蜀漢版本 A
            // 宣稱到經度 114、東吳爭議地帶宣稱從 112 開始，兩者只有 112-114 這一小段真的
            // 重疊，各自宣稱的範圍都比實際重疊區大很多，不合理）。**取代原本 I3 示範用的
            // 兩個並存版本**（蜀漢自己對借荊州範圍的史觀分歧）——那個示範跟「跟東吳的邊界
            // 爭議」其實是同一個歷史問題的兩種建模方式，同時維持兩者太複雜，選擇保留跟
            // 東吳的邊界爭議（跨政權，更貼近「政權重疊區才算爭議」這條已拍板規則的實際
            // 用例），I3 並存版本機制本身的 schema 支援不受影響，只是這筆種子資料不再拿
            // 它示範，之後有更適合的案例再補。
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(208, 215), Geom = Rect(100, 26, 111, 32), CreatedAt = DateTimeOffset.UtcNow }, // 核心（南郡以西），不受爭議
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(208, 215), Geom = Rect(111, 26, 116, 32), IsDisputed = true, CreatedAt = DateTimeOffset.UtcNow }, // 荊州爭議地帶——座標跟東吳那筆完全一致
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(215, 219), Geom = Rect(100, 26, 111, 32), CreatedAt = DateTimeOffset.UtcNow }, // 215 孫劉分荊州後縮小
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(219, 221), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 219 失荊州
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(221, 263), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 正式建國後穩定期（益州核心）

            // 東吳：5 筆，同樣在荊州易手區間加密。208-215 拆成兩筆——「江東核心」（孫氏
            // 從頭到尾穩定控制，沒有任何一方質疑過）跟「荊州爭議地帶」。爭議地帶座標跟
            // 上面蜀漢那筆**完全一致**（見蜀漢區塊的說明——爭議區定義是雙方宣稱範圍本身
            // 就是同一塊，不是兩個不同形狀矩形的碰撞產物）。
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(208, 215), Geom = Rect(116, 22, 122, 32), CreatedAt = DateTimeOffset.UtcNow }, // 江東核心，不受爭議
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(208, 215), Geom = Rect(111, 26, 116, 32), IsDisputed = true, CreatedAt = DateTimeOffset.UtcNow }, // 荊州爭議地帶——座標跟蜀漢那筆完全一致
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(215, 219), Geom = Rect(111, 22, 122, 32), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(219, 222), Geom = Rect(108, 22, 122, 32), CreatedAt = DateTimeOffset.UtcNow }, // 219 呂蒙奪荊州後擴大
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wu.Id, ValidPeriod = Years(222, 280), Geom = Rect(108, 20, 122, 32), CreatedAt = DateTimeOffset.UtcNow },

            // 西晉：3 筆——265-280 這段拆成北方核心+南方（原蜀地）兩筆，跟魏 263-265
            // 那兩筆同樣的處理原則：晉是魏禪讓而來（265 年），禪讓當下魏的實際控制範圍
            // 已經包含 263 年滅蜀併入的南方地盤，晉繼承的疆域理論上該直接銜接魏禪讓前的
            // 完整範圍，不能只繼承北方核心、讓南方（原蜀地）在禪讓那一刻又憑空消失一次
            // （2026-08-30 修正，跟上面魏新增 263-265 那筆是同一次修正的另一半）。
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = jin.Id, ValidPeriod = Years(265, 280), Geom = Rect(104, 32, 123, 42), CreatedAt = DateTimeOffset.UtcNow }, // 北方核心，繼承自魏
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = jin.Id, ValidPeriod = Years(265, 280), Geom = Rect(100, 26, 108, 32), CreatedAt = DateTimeOffset.UtcNow }, // 南方（原蜀地），繼承自魏 263 年滅蜀後的地盤
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
        // 神話援引：政權引用神話/傳說先例（如堯舜禪讓）鞏固自身合法性，是可跨文明比較的標籤
        // ——不代表被援引的神話本身被系統當成客觀史實，見 notes §九「神話算不算歷史」。
        var mythInvocationTag = new EventTag { Id = 3, TagName = "神話援引" };
        db.EventTags.AddRange(warTag, successionTag, mythInvocationTag);

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
            new HistoricalEventTagMap { EventId = hanAbdicatesWei.Id, TagId = mythInvocationTag.Id },
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
            // 2026-08-30 補上：東吳視角刻意跟上面蜀漢視角在敘事重心上真的不一樣（不是換個
            // 標籤複製一份）——蜀漢視角強調「孫劉兩家結盟、聯軍以寡擊眾」的平等聯盟敘事，
            // 這裡改成強調周瑜/東吳水軍才是決勝主力、劉備方兵力有限，這是史學界真實存在
            // 的敘事分歧（受《三國演義》影響的通俗史觀常放大劉備/諸葛亮的角色，東吳本位或
            // 較嚴謹的史學考據通常認為周瑜跟江東水軍才是實際主導戰局的一方）。順帶讓
            // task 3.7 AC#3「互動清單」的赤壁之戰有兩個政權（蜀漢、東吳）都留下視角，才
            // 配對得出「蜀漢↔東吳」這組互動——原本只有蜀漢單方視角時配不出來，見
            // implementation plan 任務 3.7 的補充說明。
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = chibi.Id,
                RegimeId = wu.Id,
                LocalName = "東吳視角",
                NarrativeSummary = "周瑜統領江東水軍主力，以火攻大破曹軍，是此役決勝關鍵；劉備軍協同但兵力有限",
                OfficialJustification = "保全江東基業，抵禦曹操南下併吞",
            },
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = chibi.Id,
                ObserverCategoryId = laterHistorians.Id,
                LocalName = "後世史學界考據",
                NarrativeSummary = "對曹操南征兵力規模、黃蓋詐降細節與火攻具體戰術的史料考證整理，各家說法不一",
                PrimarySources = """[{"title":"三國志","author":"陳壽","year":280},{"title":"資治通鑑","author":"司馬光","year":1084}]""",
            },
            // 神話援引示範（notes 世界史筆記 §九）：曹丕受禪詔書與《受禪表》碑刻明確援引堯舜禪讓
            // 先例包裝正當性——援引這件事本身是可考證史實，被援引的堯舜傳說本身不當作客觀史實看待。
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = hanAbdicatesWei.Id,
                RegimeId = wei.Id,
                LocalName = "魏方受禪敘事",
                NarrativeSummary = "曹丕接受漢獻帝禪讓，即位為魏文帝，改元黃初",
                OfficialJustification = "受禪詔書與《受禪表》援引唐堯禪舜、虞舜禪禹的上古先例，主張漢帝禪魏是效法聖王「以德相讓」的正統模式而非武力奪取；許昌一帶並立「受禪台」與《受禪表》碑刻紀念，碑文明確以堯舜作為比擬對象",
                PrimarySources = """[{"title":"三國志·魏書·文帝紀","author":"陳壽","year":280},{"title":"受禪表（碑刻）","author":"魏黃初元年立","year":220}]""",
            }
        );

        // 爭議點：真實存在的史學爭議（曹操自稱兵力與後世估算落差極大），非虛構案例
        var troopSizeControversy = new HistoricalEventControversy
        {
            Id = Guid.NewGuid(),
            EventId = chibi.Id,
            Topic = "曹操南征兵力數字爭議",
            NeutralDescription = "曹操檄文自稱「今治水軍八十萬眾」，但《三國志》裴松之注引周瑜語稱其實際「眾數雖多，甚未足畏」；後世史學家依糧秣運輸與戰場記載推估實際兵力遠不足八十萬，確切數字至今無定論。",
            Viewpoints = """[{"stance":"曹操自稱八十萬眾","source":"曹操檄文（《三國志·吳書·周瑜傳》引）"},{"stance":"實際兵力約二十餘萬","source":"後世學者依糧秣/運輸能力推算"}]""",
        };
        db.HistoricalEventControversies.Add(troopSizeControversy);

        // 正統性爭議：三國史學史上最著名的史觀分歧，直接對應方案 D（lineage_presets 解耦設計）
        // 存在的理由——不同時代的史書基於自身政權的政治處境，對「誰是正統」給出不同答案，掛在
        // 漢禪魏這個事件上，因為這正是分歧的起點。
        var legitimacyControversy = new HistoricalEventControversy
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
        };
        db.HistoricalEventControversies.Add(legitimacyControversy);

        // --- Translations (task 2.17: 憲法 R4 中英雙語，僅中立事實內容，見 PRD §6) ---
        // 範圍：regimes.self_name、regime_aliases.alias_name、historical_events.name、
        // lineage_presets.preset_name/description、historical_event_controversies.topic/
        // neutral_description。historical_event_perspectives 跟 viewpoints 不翻譯（立場性敘事，
        // 靠多重視角機制各自語言呈現，見 PRD §6 核心設計原則），故這裡沒有它們的翻譯列。
        // 2026-08-29：改用型別化表（各自真外鍵 + ON DELETE CASCADE），取代原本的通用表方案
        // ——理由是這個專案的目標是給多使用者用、資料量會持續成長，通用表放棄外鍵完整性的
        // 取捨在那個前提下不划算，見 PRD §6 修訂記錄。

        db.RegimeTranslations.AddRange(
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = han.Id, Locale = "en", SelfName = "Han", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = wei.Id, Locale = "en", SelfName = "Wei", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = shuHan.Id, Locale = "en", SelfName = "Shu Han", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = wu.Id, Locale = "en", SelfName = "Wu", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = jin.Id, Locale = "en", SelfName = "Jin", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.RegimeAliasTranslations.AddRange(
            new RegimeAliasTranslation { Id = Guid.NewGuid(), RegimeAliasId = weiAlias.Id, Locale = "en", AliasName = "the Usurper", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeAliasTranslation { Id = Guid.NewGuid(), RegimeAliasId = wuAlias.Id, Locale = "en", AliasName = "Sun Wu", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.HistoricalEventTranslations.AddRange(
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = chibi.Id, Locale = "en", Name = "Battle of Red Cliffs", CreatedAt = DateTimeOffset.UtcNow },
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = hanAbdicatesWei.Id, Locale = "en", Name = "Emperor Xian of Han Abdicates to Wei (Cao Pi Receives the Throne)", CreatedAt = DateTimeOffset.UtcNow },
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = shuConquest.Id, Locale = "en", Name = "Wei's Conquest of Shu Han", CreatedAt = DateTimeOffset.UtcNow },
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = weiAbdicatesJin.Id, Locale = "en", Name = "Emperor Yuan of Wei Abdicates to Jin (Sima Yan Receives the Throne)", CreatedAt = DateTimeOffset.UtcNow },
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = wuConquest.Id, Locale = "en", Name = "Western Jin's Conquest of Wu", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.LineagePresetTranslations.AddRange(
            new LineagePresetTranslation
            {
                Id = Guid.NewGuid(),
                LineagePresetId = textbookPreset.Id,
                Locale = "en",
                PresetName = "Traditional Textbook Historiography",
                Description = "The Han→Wei→Jin succession as the main line; Shu Han and Eastern Wu are treated as regimes "
                    + "of the fragmentation period and excluded from this preset (though they remain fully present in the "
                    + "regimes table).",
                CreatedAt = DateTimeOffset.UtcNow,
            },
            new LineagePresetTranslation
            {
                Id = Guid.NewGuid(),
                LineagePresetId = shuHanOrthodoxPreset.Id,
                Locale = "en",
                PresetName = "Shu Han Legitimist Historiography",
                Description = "Regards Shu Han as the legitimate continuation of the Han imperial line, treating Wei as a "
                    + "usurpation and excluding it from the main line. Legitimacy is considered interrupted after Shu Han's "
                    + "fall in 263; Jin is retroactively recognized as the legitimate continuation only once it reunifies "
                    + "China in 280 — on the grounds of reunification rather than of having received Wei's abdication, a "
                    + "different rationale from why the Traditional Textbook view includes Jin. This divergence is "
                    + "connected to the political needs of the Eastern Jin and Southern Song dynasties, both regimes "
                    + "confined to southern China that needed a historical precedent showing legitimacy could persist in "
                    + "the south — see the controversy entry on the Han-abdicates-to-Wei event below.",
                CreatedAt = DateTimeOffset.UtcNow,
            }
        );

        db.HistoricalEventControversyTranslations.AddRange(
            new HistoricalEventControversyTranslation
            {
                Id = Guid.NewGuid(),
                ControversyId = troopSizeControversy.Id,
                Locale = "en",
                Topic = "Dispute over the Size of Cao Cao's Southern Expedition Force",
                NeutralDescription = "Cao Cao's proclamation claimed to command \"800,000 naval troops,\" but Pei Songzhi's "
                    + "commentary on the Records of the Three Kingdoms quotes Zhou Yu describing the real number as "
                    + "\"large, but nothing to fear.\" Later historians, estimating from logistics and battlefield "
                    + "records, believe the actual force fell far short of 800,000, though the precise figure remains "
                    + "unresolved.",
                CreatedAt = DateTimeOffset.UtcNow,
            },
            new HistoricalEventControversyTranslation
            {
                Id = Guid.NewGuid(),
                ControversyId = legitimacyControversy.Id,
                Locale = "en",
                Topic = "The Three Kingdoms Legitimacy Dispute (Wei vs. Shu Han)",
                NeutralDescription = "Chen Shou's Records of the Three Kingdoms, compiled under the Western Jin (which "
                    + "itself received its throne by abdication from Wei), takes the \"Book of Wei\" as the imperial "
                    + "annals and treats Wei as legitimate. Xi Zuochi's Chronicles of Han and Jin, written under the "
                    + "Eastern Jin, reversed this, treating Shu Han as the legitimate continuation of Han. Zhu Xi's Zizhi "
                    + "Tongjian Gangmu, written under the Southern Song, followed Xi Zuochi's position. The three "
                    + "schools' disagreement doesn't stem purely from differing evidence — it tracks the political "
                    + "situation of the dynasty each history was written under: Western Jin's own legitimacy rested on "
                    + "having received Wei's abdication, while Eastern Jin and Southern Song were both regimes confined "
                    + "to southern China that needed a historical precedent showing legitimacy could persist in the "
                    + "south, and Shu Han's situation supplied exactly that precedent.",
                CreatedAt = DateTimeOffset.UtcNow,
            }
        );

        // --- 唐朝／阿拉伯帝國（伍麥亞→阿拔斯）：2026-08-31 追加，Story 3 AC#2 的真實
        // 驗證案例 ---
        // PRD Story 3 AC#2 原文舉例「唐朝視角下阿拉伯帝國稱大食」，但三國種子資料完全
        // 沒有涵蓋這個時代/地區，task 3.8 動工時只能拿種子資料裡真實存在的「蜀漢稱魏為
        // 賊」示範，不是 PRD 原文案例本身。這裡補上真正的唐朝/阿拉伯帝國資料，讓 AC#2
        // 的原文案例也有真實資料可以驗證，同時示範「政權被滅亡」在非中國史脈絡下的案例
        // ——阿拔斯革命推翻伍麥亞王朝是一場革命起事，不是中國史常見的禪讓或攻滅戰爭，
        // 但末代哈里發馬爾萬二世兵敗被殺、政權遭暴力終結，仍符合 conquered 狀態的定義。
        //
        // ⚠️ 跟本檔案其餘資料同一個限制：疆域是粗略示意矩形，不是精確史料邊界；年份簡化
        // 為整數年。唐朝疆域資料終點訂在 907 年（唐朝滅亡年，但本批資料不建模唐滅亡本身
        // ——跟晉的疆域資料延伸到 316 年、卻不建模西晉滅亡是同一個簡化原則）；阿拔斯王朝
        // 疆域資料終點訂在 900 年（示意終點，實際王朝存續到 1258 年蒙古滅巴格達，超出這批
        // 種子資料的示範範圍，不是史實錯誤）。
        //
        // ⚠️ 189-618 年之間（本檔案原有三國資料結束跟這批新資料開始之間）刻意留白，沒有
        // 任何政權的疆域資料——不是 bug，是這個資料庫目前唯二涵蓋的兩個歷史區段之間本來
        // 就沒有串連資料，拖拉桿經過這段年份地圖會正確顯示「查無疆域」，等之後真的匯入
        // 銜接時代的史料才會補上（TimelineState 拉桿上限也因此一併從 300 延伸到 950）。

        var tang = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "唐",
            Status = "active",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var umayyad = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "伍麥亞王朝",
            Status = "conquered",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var abbasid = new Regime
        {
            Id = Guid.NewGuid(),
            SelfName = "阿拔斯王朝",
            Status = "active",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        // 阿拔斯王朝不是伍麥亞王朝「分裂」或「禪讓」出來的——阿拔斯家族主張的正統性
        // 來自先知叔父阿拔斯的血統，是一場推翻既有政權的革命，不是既有政權內部的傳承
        // 轉移，predecessor_regime_id/origin_transition_type 刻意留 null（這兩個欄位
        // 的語意只回答「split/succeeded」這兩種傳承關係，不是「誰打贏了誰」——那個關係
        // 記錄在被滅政權自己的 destroyed_by_regime_id，見下面 umayyad.DestroyedByRegimeId，
        // 跟蜀漢/吳被滅時魏/晉自己也不會有對應 origin 欄位是同一個處理原則）。
        umayyad.DestroyedByRegimeId = abbasid.Id; // 750

        db.Regimes.AddRange(tang, umayyad, abbasid);

        // 唐朝對阿拉伯帝國的稱呼確實依王朝分兩種（白衣/黑衣），不是同一個「大食」通用
        // 套在兩個政權上——伍麥亞旗幟尚白、阿拔斯旗幟尚黑，唐代史料（《舊唐書》《新唐書》
        // 〈大食傳〉）以此區分兩個先後政權，這裡刻意各建一筆而非一個泛用代稱。
        var umayyadAlias = new RegimeAlias { Id = Guid.NewGuid(), RegimeId = umayyad.Id, ObserverRegimeId = tang.Id, AliasName = "白衣大食", AliasType = RegimeAliasType.Transliteration, CreatedAt = DateTimeOffset.UtcNow };
        var abbasidAlias = new RegimeAlias { Id = Guid.NewGuid(), RegimeId = abbasid.Id, ObserverRegimeId = tang.Id, AliasName = "黑衣大食", AliasType = RegimeAliasType.Transliteration, CreatedAt = DateTimeOffset.UtcNow };
        db.RegimeAliases.AddRange(umayyadAlias, abbasidAlias);

        // 伊斯蘭哈里發傳統沒有中國式年號紀年，這裡只給唐朝加 reign_eras，不是遺漏。
        db.ReignEras.AddRange(
            new ReignEra { Id = Guid.NewGuid(), RegimeId = tang.Id, EraName = "貞觀", StartYear = 627, EndYear = 649, CreatedAt = DateTimeOffset.UtcNow },
            new ReignEra { Id = Guid.NewGuid(), RegimeId = tang.Id, EraName = "天寶", StartYear = 742, EndYear = 756, CreatedAt = DateTimeOffset.UtcNow } // 怛羅斯之戰（751）發生於此年號期間
        );

        // 唐朝西境跟阿拉伯帝國東境在中亞（河中地區）真的有地理重疊——這正是怛羅斯之戰的
        // 地緣背景，不是矩形示意資料湊巧重疊；751 年戰敗後唐朝勢力退出中亞，第二筆疆域
        // 刻意收縮，兩個政權此後不再重疊（跟本檔案其餘疆域資料同一個「事件驅動密度」
        // 原則，不是固定週期切分）。
        db.RegimeTerritories.AddRange(
            // 唐：618-751 涵蓋安西四鎮鼎盛期西抵中亞的影響範圍；751 怛羅斯戰敗後收縮
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = tang.Id, ValidPeriod = Years(618, 751), Geom = Rect(73, 20, 123, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = tang.Id, ValidPeriod = Years(751, 907), Geom = Rect(95, 20, 123, 42), CreatedAt = DateTimeOffset.UtcNow }, // 退出中亞後收縮

            // 伍麥亞王朝：661-750，一筆涵蓋伊比利半島到中亞（史上疆域最大的政權之一），
            // 矩形簡化跟本檔案其餘資料同一個限制
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = umayyad.Id, ValidPeriod = Years(661, 750), Geom = Rect(-9, 15, 75, 45), CreatedAt = DateTimeOffset.UtcNow },

            // 阿拔斯王朝：750 年起，怛羅斯戰後鞏固河中地區（東境略往東擴到 78 度），
            // 疆域資料示意終點訂在 900 年（見本區塊開頭說明）
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = abbasid.Id, ValidPeriod = Years(750, 900), Geom = Rect(20, 12, 78, 45), CreatedAt = DateTimeOffset.UtcNow }
        );

        // 阿拔斯革命（伍麥亞王朝終結的觸發事件）＋怛羅斯之戰（唐朝與阿拉伯帝國唯一真實
        // 直接接觸點，task 3.8 Story 3 AC#2 的驗證錨點）。
        var abbasidRevolution = new HistoricalEvent
        {
            Id = "event-abbasid-revolution-750",
            Name = "阿拔斯革命（伍麥亞王朝覆滅）",
            StartEdtf = "0750",
            EndEdtf = "0750",
            StartDecimal = 750.000m,
            EndDecimal = 750.000m,
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        var battleOfTalas = new HistoricalEvent
        {
            Id = "event-battle-of-talas-751",
            Name = "怛羅斯之戰",
            StartEdtf = "0751",
            EndEdtf = "0751",
            StartDecimal = 751.000m,
            EndDecimal = 751.000m,
            Sections = """{"background":"唐朝安西節度使高仙芝介入拔汗那（費爾干納）與石國（塔什干）的紛爭，石國王子向阿拔斯王朝求援，雙方軍隊在中亞怛羅斯河畔遭遇","turning_points":["參戰的葛邏祿部臨陣倒戈"],"impact":"唐朝勢力退出中亞爭奪，阿拔斯王朝鞏固對河中地區的控制；後世流傳戰俘工匠將造紙術傳入伊斯蘭世界之說，惟具體傳播過程史學界仍有爭議（見下方爭議點）"}""",
            CreatedAt = DateTimeOffset.UtcNow,
            UpdatedAt = DateTimeOffset.UtcNow,
        };

        db.HistoricalEvents.AddRange(abbasidRevolution, battleOfTalas);

        db.RegimeTransitionEvents.Add(
            new RegimeTransitionEvent { RegimeId = umayyad.Id, EventId = abbasidRevolution.Id, TransitionKind = "destruction" }
        );

        db.HistoricalEventTagMaps.AddRange(
            new HistoricalEventTagMap { EventId = abbasidRevolution.Id, TagId = warTag.Id },
            new HistoricalEventTagMap { EventId = abbasidRevolution.Id, TagId = successionTag.Id },
            new HistoricalEventTagMap { EventId = battleOfTalas.Id, TagId = warTag.Id }
        );

        // 多重視角：唐/阿拔斯王朝各自的參戰理由，跟赤壁之戰蜀漢/東吳雙方視角同一個模式
        // ——task 3.7 AC#3「互動清單」用這組資料配對出「唐↔阿拔斯王朝」這組互動。
        db.HistoricalEventPerspectives.AddRange(
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = battleOfTalas.Id,
                RegimeId = tang.Id,
                LocalName = "唐軍（安西都護府）視角",
                NarrativeSummary = "安西節度使高仙芝率軍馳援西域屬國拔汗那，與阿拔斯軍隊在怛羅斯遭遇，激戰數日後因葛邏祿部倒戈而潰敗",
                OfficialJustification = "援助西域附庸拔汗那，鞏固安西四鎮對河中地區的宗主地位",
            },
            new HistoricalEventPerspective
            {
                Id = Guid.NewGuid(),
                EventId = battleOfTalas.Id,
                RegimeId = abbasid.Id,
                LocalName = "阿拔斯軍視角",
                NarrativeSummary = "呼羅珊總督轄下齊亞德·伊本·薩利赫應石國王子求援，領軍迎擊東進的唐軍，於怛羅斯擊敗唐軍",
                OfficialJustification = "聲援石國、抵禦唐朝勢力東擴，鞏固新政權對河中地區的控制",
            }
        );

        // 爭議點：真實存在的史學爭議（「戰俘傳播造紙術」是通俗流傳的敘事，但傳播路徑
        // 是否僅此一途，現代史學界看法不一），跟赤壁之戰的曹操兵力爭議同一個「非虛構
        // 案例」原則。
        var talasControversy = new HistoricalEventControversy
        {
            Id = Guid.NewGuid(),
            EventId = battleOfTalas.Id,
            Topic = "戰俘傳播造紙術入伊斯蘭世界之說的爭議",
            NeutralDescription = "後世史料（多見於較晚的阿拉伯/波斯文獻轉引）記載，怛羅斯之戰被俘的唐軍工匠中有造紙匠人，因此把造紙術傳入撒馬爾罕，進而經伊斯蘭世界傳入歐洲；但現代史學界指出，造紙技術在此戰之前可能已經透過絲路貿易與文化交流逐漸西傳，「戰俘傳播」是否為唯一或主要途徑證據並不充分，撒馬爾罕造紙業與此戰確切的因果關係至今仍無定論。",
            Viewpoints = """[{"stance":"怛羅斯戰俘工匠將造紙術傳入伊斯蘭世界","source":"後世阿拉伯/波斯史料轉引記載"},{"stance":"造紙術可能已透過絲路貿易漸進西傳，戰俘傳播說證據不足","source":"現代造紙史／絲路交流史研究"}]""",
        };
        db.HistoricalEventControversies.Add(talasControversy);

        db.RegimeTranslations.AddRange(
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = tang.Id, Locale = "en", SelfName = "Tang", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = umayyad.Id, Locale = "en", SelfName = "Umayyad Caliphate", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTranslation { Id = Guid.NewGuid(), RegimeId = abbasid.Id, Locale = "en", SelfName = "Abbasid Caliphate", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.RegimeAliasTranslations.AddRange(
            new RegimeAliasTranslation { Id = Guid.NewGuid(), RegimeAliasId = umayyadAlias.Id, Locale = "en", AliasName = "White-Clad Dashi", CreatedAt = DateTimeOffset.UtcNow },
            new RegimeAliasTranslation { Id = Guid.NewGuid(), RegimeAliasId = abbasidAlias.Id, Locale = "en", AliasName = "Black-Clad Dashi", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.HistoricalEventTranslations.AddRange(
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = abbasidRevolution.Id, Locale = "en", Name = "The Abbasid Revolution (Fall of the Umayyad Caliphate)", CreatedAt = DateTimeOffset.UtcNow },
            new HistoricalEventTranslation { Id = Guid.NewGuid(), EventId = battleOfTalas.Id, Locale = "en", Name = "Battle of Talas", CreatedAt = DateTimeOffset.UtcNow }
        );

        db.HistoricalEventControversyTranslations.Add(new HistoricalEventControversyTranslation
        {
            Id = Guid.NewGuid(),
            ControversyId = talasControversy.Id,
            Locale = "en",
            Topic = "The Dispute Over the Spread of Papermaking via Prisoners of War",
            NeutralDescription = "Later sources (mostly transmitted through relatively late Arabic/Persian accounts) record that "
                + "papermakers among the Tang soldiers captured at Talas brought papermaking to Samarkand, from where it "
                + "spread through the Islamic world and eventually to Europe. Modern historians, however, note that "
                + "papermaking technology may have already been gradually moving westward through Silk Road trade and "
                + "cultural contact before the battle, and that the evidence for prisoner transmission being the sole or "
                + "primary route is thin; the exact causal link between the battle and Samarkand's papermaking industry "
                + "remains unresolved.",
            CreatedAt = DateTimeOffset.UtcNow,
        });

        await db.SaveChangesAsync();
    }
}
