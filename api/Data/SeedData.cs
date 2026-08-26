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

        db.RegimeTerritories.AddRange(
            // 漢：2 筆（穩定期政權，快照較疏）
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = han.Id, ValidPeriod = Years(25, 189), Geom = Rect(100, 20, 122, 40), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = han.Id, ValidPeriod = Years(189, 220), Geom = Rect(102, 22, 120, 38), CreatedAt = DateTimeOffset.UtcNow },

            // 魏：3 筆
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(220, 226), Geom = Rect(105, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(226, 249), Geom = Rect(104, 32, 122, 42), CreatedAt = DateTimeOffset.UtcNow },
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = wei.Id, ValidPeriod = Years(249, 265), Geom = Rect(104, 32, 123, 42), CreatedAt = DateTimeOffset.UtcNow },

            // 蜀漢：4 筆，208/215/219 荊州易手區間刻意加密
            new RegimeTerritory { Id = Guid.NewGuid(), RegimeId = shuHan.Id, ValidPeriod = Years(208, 215), Geom = Rect(100, 26, 114, 32), IsDisputed = true, CorrectionReason = null, CreatedAt = DateTimeOffset.UtcNow }, // 借荊州
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

        await db.SaveChangesAsync();
    }
}
