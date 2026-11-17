export const meta = {
  name: 'b3-v3-chunk1-and-major-retry',
  description: '只依 args 啟動本波 agent。計畫、合併、verify、check_min、證據切片由 tools/b3v3/run_chunk.py 先做完。這個腳本不讀檔、不跑指令。',
  phases: [
    { title: 'Spawn', detail: 'one agent per spec entry; model comes from the spec' },
  ],
}

function parseSpec(value) {
  if (!value) return {}
  if (typeof value === 'string') {
    try {
      return JSON.parse(value)
    } catch (_error) {
      return {}
    }
  }
  return value
}

const spec = parseSpec(args.spec)
const agents = Array.isArray(args.agents) ? args.agents : (Array.isArray(spec.agents) ? spec.agents : [])
const repo = args.repo || spec.repo || '.'
const specPath = args.specPath || spec.specPath
const concurrency = Math.max(1, Number(args.concurrency || spec.concurrency) || 3)
const dryRun = args.dryRun === true || args.dryRun === 'true' || spec.dryRun === true

if (!agents.length) {
  log('沒有 args.agents。先在主 session（claude --model sonnet）跑 tools/b3v3/run_chunk.py next，把印出的 workflow-args 傳進來。')
  return { error: 'need agents' }
}

const counts = {}
for (const item of agents) {
  const model = item.model || 'sonnet'
  const key = `${item.phase || item.kind || 'agent'}:${model}`
  counts[key] = (counts[key] || 0) + 1
}
log(`本波 ${spec.wave || ''} ${agents.length} 個 agent，同時 ${concurrency}，dryRun=${dryRun}`)
for (const key of Object.keys(counts)) log(`${key} ${counts[key]}`)
if (dryRun) return { dryRun: true, counts, agents: agents.map((item) => item.label || item.id) }

function promptFor(item) {
  if (item.prompt) return item.prompt
  return [
    `工作目錄：${repo}。`,
    '先執行下面指令。它的 stdout 就是你的完整任務，照它做。不要把任務全文貼回對話。',
    `python3 -I tools/b3v3/run_chunk.py show-prompt --spec ${specPath} --id ${item.id}`,
    '不要 git add／commit／push，不要寫任何資料庫，不要呼叫 5052 API，不要繞過 Cloudflare／Anubis／403，不要用 Wayback 代替被擋的頁。',
    '不要 Read、cat、head 整份 raw 原文。已在 ~/wl-source-cache/b3full-v3 的原文不要重抓。',
  ].join('\n')
}

const results = []
for (let index = 0; index < agents.length; index += concurrency) {
  const slice = agents.slice(index, index + concurrency)
  log(`啟動 ${slice.map((item) => item.label || item.id).join('、')}`)
  const part = await Promise.all(slice.map(async (item) => {
    const options = {
      label: item.label || item.id,
      phase: item.phase || 'Spawn',
      model: item.model || 'sonnet',
    }
    if (item.schema) options.schema = item.schema
    try {
      const result = await agent(promptFor(item), options)
      return { id: item.id, ok: true, result }
    } catch (error) {
      log(`agent failed ${options.label}: ${error && error.message ? error.message : error}`)
      return { id: item.id, ok: false }
    }
  }))
  results.push(...part)
}
const ok = results.filter((item) => item && item.ok).length
log(`本波完成 ${ok}/${results.length}`)
return { wave: spec.wave || null, ok, total: results.length }
