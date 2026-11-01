using System;
using Microsoft.EntityFrameworkCore.Infrastructure;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace WorldLine.Api.Infrastructure.Migrations
{
    /// <summary>
    /// 屬地對照（殖民地、委任統治地 → 宗主國／管理國），只供衝突相鄰判定與虛線弧端點使用（ConflictsEndpoints.ArcsOnAsync）。
    /// 政權表沒有宗主國欄位，現有佔領歸屬與政權關係也沒有涵蓋殖民地，因此另開最小對照表；不改任何主權、事件或佔領紀錄。
    /// 對照列依 slug 寫入：資料庫裡沒有該政權（例如測試庫、正式庫尚未匯入）就略過。期間只是上限，實際仍以當日主權紀錄為準。
    /// 法、荷等其他宗主國的屬地尚未列入。
    /// </summary>
    [DbContext(typeof(WorldLineDbContext))]
    [Migration("20261101000000_RegimeDependencies")]
    public partial class RegimeDependencies : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.Sql("""
                CREATE TABLE regime_dependencies (
                    id uuid NOT NULL DEFAULT gen_random_uuid(),
                    dependency_regime_id uuid NOT NULL,
                    administering_regime_id uuid NOT NULL,
                    valid_period daterange NOT NULL,
                    note jsonb NULL,
                    created_at timestamp with time zone NOT NULL DEFAULT now(),
                    CONSTRAINT pk_regime_dependencies PRIMARY KEY (id),
                    CONSTRAINT fk_regime_dependencies_dependency FOREIGN KEY (dependency_regime_id) REFERENCES regimes (id),
                    CONSTRAINT fk_regime_dependencies_administering FOREIGN KEY (administering_regime_id) REFERENCES regimes (id),
                    CONSTRAINT ck_regime_dependencies_distinct CHECK (dependency_regime_id <> administering_regime_id),
                    CONSTRAINT ck_regime_dependencies_period CHECK (NOT isempty(valid_period)),
                    CONSTRAINT ex_regime_dependencies_no_overlap EXCLUDE USING gist (dependency_regime_id WITH =, valid_period WITH &&)
                );
                CREATE INDEX ix_regime_dependencies_administering ON regime_dependencies (administering_regime_id);

                INSERT INTO regime_dependencies (dependency_regime_id, administering_regime_id, valid_period, note)
                SELECT d.id, a.id, v.p::daterange, jsonb_build_object('zh-Hant', v.zh, 'en', v.en)
                FROM (VALUES
                  ('cyprus-british-administration',  'united-kingdom-of-great-britain-and-ireland', '[1908-10-06,1914-11-05)', '英國管理（鄂圖曼名義主權）', 'British administration (nominal Ottoman sovereignty)'),
                  ('cyprus-british-annexation-1914', 'united-kingdom-of-great-britain-and-ireland', '[1914-11-05,1922-12-05)', '英國併吞', 'British annexation'),
                  ('cyprus-british-annexation-1914', 'united-kingdom',                              '[1922-12-05,1925-05-01)', '英國併吞', 'British annexation'),
                  ('cyprus-crown-colony',            'united-kingdom',                              '[1925-05-01,1960-08-16)', '英國直轄殖民地', 'British crown colony'),
                  ('malta-crown-colony',             'united-kingdom-of-great-britain-and-ireland', '[1908-10-06,1922-12-05)', '英國直轄殖民地', 'British crown colony'),
                  ('malta-crown-colony',             'united-kingdom',                              '[1922-12-05,1964-09-21)', '英國直轄殖民地', 'British crown colony'),
                  ('gibraltar-crown-colony',         'united-kingdom-of-great-britain-and-ireland', '[1908-10-06,1922-12-05)', '英國直轄殖民地', 'British crown colony'),
                  ('gibraltar-crown-colony',         'united-kingdom',                              '[1922-12-05,)',           '英國海外領土', 'British overseas territory'),
                  ('sultanate-of-egypt',             'united-kingdom-of-great-britain-and-ireland', '[1914-12-19,1922-02-28)', '英國保護國', 'British protectorate'),
                  ('mandatory-palestine',            'united-kingdom-of-great-britain-and-ireland', '[1920-08-10,1922-12-05)', '英國委任統治', 'British mandate'),
                  ('mandatory-palestine',            'united-kingdom',                              '[1922-12-05,1948-05-15)', '英國委任統治', 'British mandate'),
                  ('emirate-of-transjordan',         'united-kingdom-of-great-britain-and-ireland', '[1920-08-10,1922-12-05)', '英國委任統治', 'British mandate'),
                  ('emirate-of-transjordan',         'united-kingdom',                              '[1922-12-05,1946-05-25)', '英國委任統治', 'British mandate'),
                  ('mandatory-iraq',                 'united-kingdom-of-great-britain-and-ireland', '[1920-08-10,1922-12-05)', '英國委任統治', 'British mandate'),
                  ('mandatory-iraq',                 'united-kingdom',                              '[1922-12-05,1932-10-03)', '英國委任統治', 'British mandate'),
                  ('british-hong-kong',              'united-kingdom',                              '[1922-12-05,1997-07-01)', '英國直轄殖民地', 'British crown colony'),
                  ('straits-settlements',            'united-kingdom',                              '[1922-12-05,1946-04-01)', '英國直轄殖民地', 'British crown colony'),
                  ('british-malaya',                 'united-kingdom',                              '[1922-12-05,1946-04-01)', '英國保護邦', 'British protected states'),
                  ('british-burma',                  'united-kingdom',                              '[1937-04-01,1948-01-04)', '英國殖民地（1937 年自印度分治）', 'British colony (separated from India 1937)'),
                  ('commonwealth-of-the-philippines','united-states-of-america',                    '[1935-11-15,1946-07-04)', '美國自治邦', 'US commonwealth')
                ) AS v(dep, adm, p, zh, en)
                JOIN regimes d ON d.slug = v.dep AND d.retracted_at IS NULL
                JOIN regimes a ON a.slug = v.adm AND a.retracted_at IS NULL;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            throw new NotSupportedException("RegimeDependencies 不支援 Down；請改開新資料庫。");
        }
    }
}
