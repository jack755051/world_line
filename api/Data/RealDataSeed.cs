using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using NetTopologySuite.Geometries;
using NetTopologySuite.IO.Converters;
using WorldLine.Api.Data.Entities;

namespace WorldLine.Api.Data;

/// <summary>
/// **這裡放真正查證過、附引用來源的正式史料，跟 `SeedData.cs` 的示意矩形是兩個不同
/// 性質的東西，刻意分開一個檔案**——`SeedData.cs` 開頭明講「Geometries are rough
/// illustrative rectangles, not historically accurate boundaries」，混進真實資料會讓
/// 那句警語變成謊話。這裡的每一步都照 `docs/data-governance.md` 的規則走：I5 版本鏈
/// 修正（不覆蓋刪除原記錄）＋ PRD §12 source/citation model（`Source`/
/// `RegimeTerritoryCitation`，2026-08-31 落地）記錄考證過程。
///
/// **2026-08-31 第一筆真實資料：吳（西元 225 年）疆域**——使用者問「東吳的矩形什麼時候
/// 能換成真的」，經過一輪 pilot（先試魏失敗，CHGIS 對魏核心地盤幾乎沒有三國時期的
/// 資料，改用吳成功）之後正式匯入。幾何資料放 `Data/RealData/wu-225-territory.geojson`
/// （不寫成 C# 字面值——82KB、1951 個頂點，寫進程式碼可讀性太差），是用 CHGIS v6 Time
/// Series Prefecture Polygons（Harvard Dataverse DOI 10.7910/DVN/I0Q7SM）的 12 筆
/// 郡級記錄（武陵/長沙/零陵/桂陽/丹陽/會稽/吳郡/豫章/廬陵/合浦/蒼梧/南海，皆與西元
/// 225 年重疊）用 shapely `unary_union` dissolve、再用 Douglas-Peucker 演算法簡化
/// （容許誤差 0.02 度）算出來的，完整考證過程記在下方 `evidenceNote`。
///
/// **冪等判斷**：檢查有沒有已存在的 `Source.Title` 等於這筆匯入用的資料集名稱——不是
/// 檢查「regimes 存不存在」（那是 `SeedData.SeedAsync` 自己的冪等判斷，兩者範圍不同：
/// 這個方法在 `SeedData.SeedAsync` 之後才跑，每次啟動都要能正確判斷「這筆真實資料
/// 匯入過了沒」，不能因為 regimes 表已經有資料就整批跳過）。
/// </summary>
public static class RealDataSeed
{
    private const string ChgisV6SourceTitle = "CHGIS Version 6: Time Series Prefecture Polygons";

    public static async Task SeedAsync(WorldLineDbContext db)
    {
        if (await db.Sources.AnyAsync(s => s.Title == ChgisV6SourceTitle))
        {
            return; // 已經匯入過，不重複執行（避免每次啟動都疊加新的 correction 版本鏈）
        }

        var wu = await db.Regimes.FirstOrDefaultAsync(r => r.SelfName == "吳");
        if (wu is null)
        {
            return; // SeedData.cs 的示範資料還沒建立（例如全新測試資料庫尚未跑過 SeedData），沒有政權可以掛
        }

        // 找目前有效（未被 I5 取代）、涵蓋西元 225 年的那一筆——就是 SeedData.cs 裡
        // Years(222, 280) 的示意矩形，見該檔案。
        var target = await db.RegimeTerritories
            .Where(t => t.RegimeId == wu.Id && t.SupersededBy == null && t.ValidPeriod.Contains(225))
            .SingleOrDefaultAsync();
        if (target is null)
        {
            return; // 找不到對應的示意矩形可以修正，防禦性跳過，不拋例外擋住整個應用程式啟動
        }

        var geojsonPath = Path.Combine(AppContext.BaseDirectory, "Data", "RealData", "wu-225-territory.geojson");
        var geoJsonOptions = new JsonSerializerOptions();
        geoJsonOptions.Converters.Add(new GeoJsonConverterFactory());
        var geom = JsonSerializer.Deserialize<MultiPolygon>(await File.ReadAllTextAsync(geojsonPath), geoJsonOptions)!;

        const string evidenceNote =
            "此疆域為 12 筆 CHGIS 郡級記錄 dissolve 而成（皆與西元 225 年重疊）：武陵郡" +
            "（record idx 2917, 209-262）、長沙郡（2957, 222-256）、零陵郡（2933, 168-256）、" +
            "桂陽郡（3362, 23-256）、丹陽郡（2251, 208-265）、會稽郡（2177, 129-256）、" +
            "吳郡（2163, 198-265）、豫章郡（2385, 221-256）、廬陵郡（2376, 191-266）、" +
            "合浦郡（3315, 220-227）、蒼梧郡（3247, 23-225）、南海郡（3221, -110-264）。" +
            "政權歸屬考證：交叉比對維基百科「孫吳行政區劃」條目（225 年時廣州尚未從交州" +
            "分出、建安郡尚未從會稽分出，故不含在內）。GIS 方法：shapely unary_union 合併，" +
            "其中桂陽郡、廬陵郡來源幾何本身不合法（is_valid=False），先用 buffer(0) 修復；" +
            "合併後用 Douglas-Peucker 演算法簡化（容許誤差 0.02 度，頂點數 23329 → 1951，" +
            "簡化前後目視比對輪廓無明顯差異）。已知缺口：南郡（三國時期魏蜀吳反覆爭奪，" +
            "該圖層完全沒有 189-280 年的記錄）、交趾/九真/日南/鬱林（CHGIS 資料庫範圍不" +
            "涵蓋現在的越南地區，是吳交州轄境的一部分但未反映在這個疆域多邊形裡）。";

        var source = new Source
        {
            Id = Guid.NewGuid(),
            Title = ChgisV6SourceTitle,
            AuthorOrPublisher = "Fairbank Center for Chinese Studies (Harvard University) and " +
                "Center for Historical Geographical Studies (Fudan University)",
            VersionOrPublishedAt = "Version 6, published December 2016",
            Locator = "https://doi.org/10.7910/DVN/I0Q7SM （檔案 v6_time_pref_pgn_utf_wgs84.shp）",
            License = "free for academic research, no commercial use, resale, or redistribution permitted",
            AccessedAt = new DateOnly(2026, 8, 31),
            CreatedAt = DateTimeOffset.UtcNow,
        };

        var replacement = new RegimeTerritory
        {
            Id = Guid.NewGuid(),
            RegimeId = wu.Id,
            ValidPeriod = target.ValidPeriod, // 沿用原本 [222,280) 存續區間，見 evidenceNote 說明
            Geom = geom,
            IsDisputed = false,
            CreatedAt = DateTimeOffset.UtcNow,
        };

        db.RegimeTerritories.Add(replacement);
        target.SupersededBy = replacement.Id;
        target.CorrectionReason = "以 CHGIS v6 Time Series Prefecture Polygons 取代示意矩形，詳見對應的 regime_territory_citations.evidence_note";
        target.CorrectedAt = DateTimeOffset.UtcNow;

        db.Sources.Add(source);
        db.RegimeTerritoryCitations.Add(new RegimeTerritoryCitation
        {
            Id = Guid.NewGuid(),
            RegimeTerritoryId = replacement.Id,
            SourceId = source.Id,
            EvidenceNote = evidenceNote,
            CreatedAt = DateTimeOffset.UtcNow,
        });

        await db.SaveChangesAsync();
    }
}
