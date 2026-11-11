-- 邱吉爾補建：寫入後計數核對（全為 SELECT；請以唯讀連線執行）
-- 用法（變數 bio、rec 可選；不給就以名稱與期間查）：
--   docker exec -i -e "PGOPTIONS=-c default_transaction_read_only=on" worldline-borders-dev-db \
--     psql -U worldline -d <worldline_borders_dev|worldline_person_dryrun> -At [-v bio=<uuid>] [-v rec=<uuid>] < counts.sql
-- 預期值寫在每條註解；寫入前（目前）應為 0、0、0|0、0、0、3|1。
\if :{?bio}
\else
\set bio ''
\endif
\if :{?rec}
\else
\set rec ''
\endif

-- ① 三個來源網址在 sources 的筆數（預期 3）
select 'sources' as k, count(*) from sources
 where url in ('https://www.gov.uk/government/history/past-prime-ministers/winston-churchill',
               'https://api.parliament.uk/historic-hansard/people/mr-winston-churchill/index.html',
               'https://www.nobelprize.org/prizes/literature/1953/churchill/biographical/');

-- ② 有效的 Winston Churchill bio（預期 1）
select 'bio_live' as k, count(*) from leader_bios where name = 'Winston Churchill' and retracted_at is null;

-- ③ 該 bio 的 leader_bio_field_citations 總數｜quote 非空數（預期 11|11）
select 'bio_citations_total|quoted' as k, count(*) || '|' || count(*) filter (where quote is not null)
  from leader_bio_field_citations
 where bio_id = coalesce(nullif(:'bio', '')::uuid,
                         (select id from leader_bios where name = 'Winston Churchill' and retracted_at is null));

-- ④ united-kingdom、head_of_government、有效、與 [1940-05-10,1945-07-26) 重疊的任期（預期 1）
select 'uk_hog_1940_45' as k, count(*) from leader_records r join regimes g on g.id = r.regime_id
 where g.slug = 'united-kingdom' and r.role = 'head_of_government' and r.retracted_at is null
   and r.valid_period && daterange('1940-05-10', '1945-07-26');

-- ⑤ 該任期的 leader_record_citations（有效）筆數（預期 2）
select 'record_citations' as k, count(*) from leader_record_citations
 where retracted_at is null
   and record_id = coalesce(nullif(:'rec', '')::uuid,
                            (select r.id from leader_records r join regimes g on g.id = r.regime_id
                              where g.slug = 'united-kingdom' and r.role = 'head_of_government'
                                and r.retracted_at is null and r.name = 'Winston Churchill'
                                and r.valid_period = daterange('1940-05-10', '1945-07-26')));

-- 附：3 筆撤回測試 bio｜撤回任期 01a19efa-769a-7615-9705-89c66d803905 仍為撤回（預期 3|1，不變）
select 'retracted_unchanged' as k,
       (select count(*) from leader_bios where retracted_at is not null and id in
          ('01a19efa-758c-718a-b1ec-27916469f239', '01a19ef6-b466-7e2e-94e1-8ec3c0e5ac10',
           '01a19ef9-1c0b-781a-911b-adc230abbeaf'))
       || '|' ||
       (select count(*) from leader_records where retracted_at is not null
           and id = '01a19efa-769a-7615-9705-89c66d803905');
