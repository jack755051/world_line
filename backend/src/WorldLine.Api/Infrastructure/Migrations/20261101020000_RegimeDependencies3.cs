using System;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 屬地對照第三批：法國在黎凡特的委任統治地（大馬士革、阿勒坡、大黎巴嫩、德魯茲山、阿拉維、敘利亞聯邦／國／共和國、黎巴嫩共和國）
    /// 與亞歷山大勒塔（哈塔伊國，法土共同監管）。宗主依法國政權分段：第三共和 → 維琪（至 1941-07-14 阿卡停戰）→ 自由法國
    /// → 法蘭西民族解放委員會 → 臨時政府；以 daterange 交集寫入。依 slug 寫入、找不到政權就略過、已存在的同一筆不重複寫，
    /// 只供衝突相鄰判定與虛線弧端點使用。摩洛哥、突尼西亞、印度支那等其他法屬地仍未列入。
    /// </summary>
    [DbContext(typeof(WorldLineDbContext))]
    [Migration("20261101020000_RegimeDependencies3")]
    public partial class RegimeDependencies3 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                INSERT INTO regime_dependencies (dependency_regime_id, administering_regime_id, valid_period, note)
                SELECT d.id, a.id, dp.p::daterange * ap.p::daterange, jsonb_build_object('zh-Hant', dp.zh, 'en', dp.en)
                FROM (VALUES
                  ('french-mandate-levant-1920', '[1920-08-10,1920-09-01)', '法國委任統治', 'French mandate'),
                  ('state-of-damascus',          '[1920-09-01,1922-06-28)', '法國委任統治', 'French mandate'),
                  ('state-of-aleppo',            '[1920-09-01,1922-06-28)', '法國委任統治', 'French mandate'),
                  ('state-of-greater-lebanon',   '[1920-09-01,1926-05-23)', '法國委任統治', 'French mandate'),
                  ('jabal-druze-state',          '[1921-05-01,1936-09-09)', '法國委任統治', 'French mandate'),
                  ('syrian-federation-1922',     '[1922-06-28,1925-01-01)', '法國委任統治', 'French mandate'),
                  ('state-of-syria-mandate',     '[1925-01-01,1930-05-14)', '法國委任統治', 'French mandate'),
                  ('alawite-state',              '[1925-01-01,1936-09-09)', '法國委任統治', 'French mandate'),
                  ('lebanese-republic-mandate',  '[1926-05-23,1946-12-31)', '法國委任統治（1943 年宣布獨立後法軍仍駐留至 1946 年底）', 'French mandate (French troops remained until end of 1946)'),
                  ('syrian-republic-mandate',    '[1930-05-14,1946-04-17)', '法國委任統治（法軍 1946-04-17 撤離）', 'French mandate (French troops left 1946-04-17)'),
                  ('hatay-state',                '[1938-09-02,1939-06-29)', '亞歷山大勒塔：法土共同監管下的哈塔伊國', 'Alexandretta: Hatay State under joint French–Turkish supervision')
                ) AS dp(dep, p, zh, en)
                CROSS JOIN (VALUES
                  ('french-third-republic',                  '[1920-08-10,1940-06-22)'),
                  ('french-state-vichy',                     '[1940-06-22,1941-07-14)'),
                  ('free-france',                            '[1941-07-14,1943-06-03)'),
                  ('french-committee-of-national-liberation','[1943-06-03,1944-08-09)'),
                  ('provisional-government-french-republic', '[1944-08-09,1947-01-01)')
                ) AS ap(adm, p)
                JOIN regimes d ON d.slug = dp.dep AND d.retracted_at IS NULL
                JOIN regimes a ON a.slug = ap.adm AND a.retracted_at IS NULL
                WHERE NOT isempty(dp.p::daterange * ap.p::daterange)
                  AND NOT EXISTS (SELECT 1 FROM regime_dependencies x
                                  WHERE x.dependency_regime_id = d.id AND x.administering_regime_id = a.id
                                    AND x.valid_period = dp.p::daterange * ap.p::daterange);
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("RegimeDependencies3 不支援 Down；請改開新資料庫。");
        }
    }
}
