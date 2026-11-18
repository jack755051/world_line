#!/bin/zsh
# 依開發庫重產 existing_bios.tsv（id、name、zh、生年、卒年；只含有效生平）
cd ${0:A:h}
docker exec worldline-borders-dev-db psql -U worldline -d worldline_borders_dev -tA -F $'\t' -c "select id, name, coalesce(name_zh,''), coalesce(extract(year from birth_date)::int::text,''), coalesce(extract(year from death_date)::int::text,'') from leader_bios where retracted_at is null order by name" > existing_bios.tsv
wc -l < existing_bios.tsv
