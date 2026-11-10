#!/bin/zsh
# 試驗段 b33：前景同步跑一位 Sonnet 研究員。用法：run_person.sh <stem> <groupKey> <name> <regime> <termStart> <recordIds,逗號> <來源提示>
# 子程序完整 json 存 b33/sub/<stem>.json；本腳本只印用量與結果前 400 字。
set -u
ts=$(date +%H%M%S)
stem=$1 key=$2 name=$3 regime=$4 start=$5 ids=$6 hint=$7
root=/Users/jack755051/01_Projects/world_line
g=data/seed/leaders/gap-830
mkdir -p $root/$g/b33/people $root/$g/b33/sub
idsj=$(python3 -c 'import json,sys;print(json.dumps(sys.argv[1].split(",")))' "$ids")
prompt="Research ONE person for a historical-map project, then write one JSON file.
Person: \"$name\" — regime $regime, term starting $start. groupKey \"$key\"; recordIds $idsj; recordNameVariants [\"$name\"].
Rules: read $g/BRIEF.md (sources, fields, portrait rules), $g/SCHEMA.md and data/seed/leaders/batch-p1-20261107/SCHEMA.md (P and S format). Ignore BRIEF steps 1, 3 and the final reply section. accessedOn = \"2026-11-10\".
Method: one or two strong pages covering several fields. Fetch with curl, strip tags, grep keywords; do not dump whole pages. Wikipedia/Wikidata/Baidu are never sources (Wikidata for the Q-id only: one wbsearchentities API call, check dates match). Source hints: $hint. Blocked: infopedia.pt, adesp.org, historia-hispanica.rah.es.
Output: write exactly $g/b33/people/$stem.json as either {\"person\": P} (P with key, groupKeys, recordIds, recordNameVariants, wikidataQid, name, nameZh, birthDate, deathDate, birthPlace, party, summary, unverified, conflicts if any, portrait) or {\"staging\": {\"groupKeys\":[...],\"names\":[...],\"why\":\"...\",\"clues\":\"...\"}} if identity is uncertain or no acceptable source opens. Evidence verbatim ≤25 words. Write no other file; no DB, docker, psql or HTTP POST.
Final reply: at most 3 short lines (filled fields, missing fields, reason)."
cd $root
claude -p --model sonnet --output-format json "$prompt" --allowedTools "Bash Read Edit Write Glob Grep WebFetch WebSearch" > $g/b33/sub/$stem.$ts.json 2> $g/b33/sub/$stem.$ts.err
python3 - "$g/b33/sub/$stem.$ts.json" <<'EOF'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception as e: print("PARSE FAIL",e); sys.exit()
u=d.get("usage",{})
print("sid",d.get("session_id"),"err",d.get("is_error"),"usd",d.get("total_cost_usd"),"turns",d.get("num_turns"),
 "in",u.get("input_tokens"),"out",u.get("output_tokens"),"cc",u.get("cache_creation_input_tokens"),"cr",u.get("cache_read_input_tokens"))
print(str(d.get("result",""))[:400])
EOF
ls -la $root/$g/b33/people/$stem.json 2>&1 | cut -c30-
