#!/bin/zsh
# 建開發庫（5442）的控制層 fixture 請求目錄：只用 symlink 指向已寫入正式庫的既有 seed 請求檔，不複製、不改內容。
# 用法：data/seed/dev-fixtures/control-1940/build.sh  → 產生 tmp/fixture-control-1940/requests/F1/ 與預填政權 id 的 ids 檔
set -e
cd ${0:A:h}/../../../..
W=data/seed/ww2
OUT=tmp/fixture-control-1940/requests/F1
rm -rf tmp/fixture-control-1940; mkdir -p $OUT
ln_() { ln -s ${PWD}/$W/$1/requests/$2 $OUT/$3-$2; }
for f in $(cd $W/france-1940-07-15/requests && ls 01-source-*.json) 03-theater-west-europe.json 04-snapshot-1-1940-07-15.json 04-snapshot-2-1940-08-15.json \
         05-control-1-main.json 05-control-2-nord-pas-de-calais.json 05-control-3a-alsace-moselle-military.json 05-control-3b-alsace-moselle-cdz.json; do
  ln_ france-1940-07-15 $f a
done
for f in 01-source-1-src_jo_19400711.json 01-source-2-src_dgfp_d9.json 01-source-4-src_frus_1942_i.json \
         05-control-1-vichy-free-zone.json 06-alignment-1-french-state-co-belligerent.json 06-alignment-2-united-kingdom-allies-1942.json 08-coverage-1-alpine.json; do
  ln_ fr-uk-1940 $f b
done
for f in 01-source-1-src_nca_v.json 01-source-2-src_frus_japan_v2.json 03-source-4-src_dgfp_d6_gpo.json 02-alignment-1-deutsches-reich-axis.json 05-alignment-3-deutsches-reich-axis-pact-of-steel-gpo.json; do
  ln_ alignments $f c
done
# 政權已在開發庫（borders 資料），以 slug 查 id 預填，send_seed2 會跳過建立政權的請求
Q="select json_object_agg(k, id) from (values ('REGIME_DE','deutsches-reich'),('REGIME_FR3','french-third-republic'),('REGIME_FR_STATE','french-state-vichy'),('REGIME_FR_LIBRE','free-france'),('REGIME_UK','united-kingdom')) v(k,s) join regimes r on r.slug=v.s"
IDS=.dev/sent-ids.fixture-control-1940-dev.json
if [[ ! -f $IDS ]]; then
  docker exec -i worldline-borders-dev-db psql -U worldline -d worldline_borders_dev -At -c "$Q" > $IDS
fi
ls $OUT | wc -l
