# Mirrors prompt builders in .dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js verbatim.
import json, re, os, sys
REPO='/Users/jack755051/Project/private/world_line-battle-demo'
RULES=f'工作目錄：{REPO}。只寫任務指定的 OUTDIR 與 RAWDIR。不要 git add／commit／push，不要寫任何資料庫，不要呼叫 5052 API，不要繞過 Cloudflare／Anubis／403，不要用 Wayback 代替被擋的頁。不要 Read、cat、head 整份 raw 原文，不要把整頁貼進上下文。'
CHECK='check_min-report.json'
plan=json.load(open('/tmp/b3v3-plan.json'))
B={b['nn']:b for b in plan['batches']}
def pp(b,p): return os.path.join(b['outDir'],'people',f"{p['bioId']}.json")
def kw(p):
    years=re.findall(r'\d{4}',p['line'])[:4]
    return '|'.join(x for x in [p.get('name'),p.get('nameZh'),*years] if x)
def research(b,p): return '\n'.join([
 '你只研究一個人，開一個全新的研究。不要研究提示詞裡的其他人。',
 f"人物：{p['line']}", f"bioId：{p['bioId']}", f"只寫這個檔：{pp(b,p)}",
 f"內容是一個 JSON 物件：person（一個人的完整條目）、sources、rawMap、researchedOn、policyVersion（bio-2026-11-v0）、alignedTo（b0b0e0f）、alignNote、schemaNote。不要寫 {b['outDir']}/research.json。",
 f"規則檔（格式、來源分級、Q1–Q10、T14、最低 8 次查詢／4 種來源類型／原文語言檢索都要做）：{b['researchPrompt']}",
 '抓取與引文不要照規則檔裡舊的 curl／整檔 Read。一律：',
 f"python3 -I tools/b3v3/fetch_source.py status --rawdir {b['rawDir']} --rawmap {b['outDir']}/rawmap.json",
 '已有的 sourceKey 不要重抓。新頁：',
 f"python3 -I tools/b3v3/fetch_source.py fetch --rawdir {b['rawDir']} --rawmap {b['outDir']}/rawmap.json --source-key <sourceKey> --url <url> --keywords '{kw(p)}'",
 '抄 quote 只用 lookup，關鍵字改成你要的原文片段。WebFetch 只用於發現網址。',
 '不要跑 verify.py 或 check_min.py。回覆不要貼引文或頁面。', RULES])
def retry(b,p): return '\n'.join([
 '只加強重跑一個人，不要改本批其他人。', f"人物：{p['line']}", f"bioId：{p['bioId']}",
 f"規則檔：{b['retryPrompt']}",
 f"先只讀這一份：{pp(b,p)}。不要讀整份 research.json，不要讀 raw 原文。", '改完覆寫同一個單人檔。',
 f"抓取：python3 -I tools/b3v3/fetch_source.py status --rawdir {b['rawDir']} --rawmap {b['outDir']}/rawmap.json",
 f"已有的 sourceKey 不要重抓。新頁與 lookup 都用 fetch_source.py。建議關鍵字起點：{kw(p)}",
 '本輪新增：至少 5 種來源類型、15 次查詢（原文語言至少 4 次）、6 個新頁。searchLog 標 "round": "retry"。',
 '仍不足就加 target=paragraph:length、note 以「篇幅不足：」開頭的 gap。', '不要跑 check_min.py。回覆不要貼頁面。', RULES])
def review(b): return '\n'.join([
 f"你是審查者。規則檔 {b['reviewPrompt']} 的來源分級、T14、最低標準、Q1–Q10 全部仍適用。",
 f"batch{b['nn']} 上次審查被中斷，請整批重查。" if b['recheck'] else f"審查 batch{b['nn']}。",
 f"逐字引文是否在原文，以 verify.py 為準。請讀 {b['outDir']}/evidence-pack.json（每筆 claim 的段落文字、quote、sourceKey、verify）與 {b['outDir']}/research.json。",
 f"不要 Read 或 cat {b['rawDir']} 的整檔，不要整批重抓網頁。全批最多 1 次抽查重抓，而且只能：",
 f"python3 -I tools/b3v3/fetch_source.py fetch --rawdir {b['rawDir']} --rawmap {b['outDir']}/rawmap.json --source-key <sourceKey> --url <url> --keywords '<詞>'",
 f"最低標準看 {b['outDir']}/{CHECK}，不要自己跑 check_min.py。",
 f"改完 research.json 後跑 verify.py，只讀它印出的摘要，然後寫 {b['outDir']}/review.json。", RULES])
# usage: prompts.py <out.json> kind:nn[:bioId,...] ...
tasks=[]
for spec in sys.argv[2:]:
    kind,nn,*rest=spec.split(':'); b=B[nn]
    if kind=='review': tasks.append({'kind':'review','label':f'review:{nn}','phase':'Review','prompt':review(b)}); continue
    ids=rest[0].split(',') if rest else None
    allp=b['people'] if kind=='research' else (b['retry'].get('people') or b['people'])
    for p in allp:
        if ids and p['bioId'] not in ids: continue
        f=research if kind=='research' else retry
        tasks.append({'kind':kind,'label':f"{kind}:{nn}:{p['bioId']}",'phase':kind.capitalize(),'prompt':f(b,p)})
json.dump(tasks,open(sys.argv[1],'w'),ensure_ascii=False,indent=1)
print([t['label'] for t in tasks])
