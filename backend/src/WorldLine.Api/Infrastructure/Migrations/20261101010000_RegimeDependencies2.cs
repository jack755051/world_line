using System;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 屬地對照第二批：亞洲第三批資料新增的英國殖民地與保護國（英屬印度、錫蘭、亞丁、波斯灣各保護國、婆羅洲三邦、索羅門群島等），
    /// 以及澳洲管理的巴布亞與新幾內亞。與第一批相同，依 slug 寫入、找不到政權就略過，只供衝突相鄰判定與虛線弧端點使用。
    /// 尼泊爾、不丹、阿富汗、馬斯喀特與阿曼、沙烏地阿拉伯、葉門為獨立國家，不列入；法、葡屬地仍未列入。
    /// </summary>
    [DbContext(typeof(WorldLineDbContext))]
    [Migration("20261101010000_RegimeDependencies2")]
    public partial class RegimeDependencies2 : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                INSERT INTO regime_dependencies (dependency_regime_id, administering_regime_id, valid_period, note)
                SELECT d.id, a.id, v.p::daterange, jsonb_build_object('zh-Hant', v.zh, 'en', v.en)
                FROM (VALUES
                  ('british-raj',              'united-kingdom',           '[1922-12-05,1947-08-15)', '英屬印度（含土邦）', 'British India (incl. the princely states)'),
                  ('british-ceylon',           'united-kingdom',           '[1922-12-05,1948-02-04)', '英國直轄殖民地', 'British crown colony'),
                  ('maldives-protectorate',    'united-kingdom',           '[1922-12-05,1965-07-26)', '英國保護國', 'British protectorate'),
                  ('aden-colony',              'united-kingdom',           '[1937-04-01,1963-01-18)', '英國直轄殖民地', 'British crown colony'),
                  ('aden-protectorate',        'united-kingdom',           '[1922-12-05,1967-11-30)', '英國保護地', 'British protectorate'),
                  ('trucial-states',           'united-kingdom',           '[1922-12-05,1971-12-02)', '英國保護', 'British protection'),
                  ('qatar-protectorate',       'united-kingdom',           '[1922-12-05,1971-09-03)', '英國保護國', 'British protectorate'),
                  ('bahrain-protectorate',     'united-kingdom',           '[1922-12-05,1971-08-15)', '英國保護國', 'British protectorate'),
                  ('kuwait-protectorate',      'united-kingdom',           '[1922-12-05,1961-06-19)', '英國保護國', 'British protectorate'),
                  ('raj-of-sarawak',           'united-kingdom',           '[1922-12-05,1946-07-01)', '英國保護國', 'British protected state'),
                  ('brunei-protectorate',      'united-kingdom',           '[1922-12-05,1984-01-01)', '英國保護國', 'British protectorate'),
                  ('british-north-borneo',     'united-kingdom',           '[1922-12-05,1946-07-15)', '英國保護國（渣打公司管理）', 'British protectorate (chartered company)'),
                  ('british-solomon-islands',  'united-kingdom',           '[1922-12-05,1978-07-07)', '英國保護國', 'British protectorate'),
                  ('territory-of-papua',       'commonwealth-of-australia','[1906-09-01,1949-07-01)', '澳洲領地', 'Australian territory'),
                  ('territory-of-new-guinea',  'commonwealth-of-australia','[1920-12-17,1949-07-01)', '澳洲管理的委任統治地', 'Australian-administered mandate')
                ) AS v(dep, adm, p, zh, en)
                JOIN regimes d ON d.slug = v.dep AND d.retracted_at IS NULL
                JOIN regimes a ON a.slug = v.adm AND a.retracted_at IS NULL;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("RegimeDependencies2 不支援 Down；請改開新資料庫。");
        }
    }
}
