-- B3 full 人選快照（唯讀；Tai 2026-11-11 21:24）。輸出 bioId、姓名、任期數、1908–1945 窗內任期日數（去重疊前加總）、首任起日。
begin transaction read only;
\pset tuples_only on
\pset format unaligned
\pset fieldsep '\t'
select b.id, b.name, coalesce(b.name_zh,''),
  count(r.id),
  coalesce(sum(greatest(0, least(coalesce(upper(r.valid_period),'1946-01-01'),'1946-01-01'::date) - greatest(lower(r.valid_period),'1908-01-01'::date))),0),
  coalesce(min(lower(r.valid_period))::text,'')
from leader_bios b left join leader_records r on r.person_id=b.id and r.retracted_at is null
where b.retracted_at is null and b.superseded_by is null and not b.is_test
group by b.id, b.name, b.name_zh order by b.id;
rollback;
