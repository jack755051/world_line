#!/bin/zsh
# 檢查一批 research.json 引用網址的 HTTP 狀態（只印非 200 的）：./urlcheck.sh bNN
python3 -c "
import json,sys
r=json.load(open(sys.argv[1]+'/research.json'))
u=set()
for p in r['people']:
  for f,v in p.items():
    if isinstance(v,dict):
      for s in v.get('sources') or []: u.add(s['url'])
print('\n'.join(sorted(u)))" $1 | while read u; do
  c=$(curl -s -o /dev/null -L -m 20 -A 'Mozilla/5.0 worldline-research' -w '%{http_code}' "$u"); [[ $c == 200 ]] || echo "$c $u"; done; echo checked
