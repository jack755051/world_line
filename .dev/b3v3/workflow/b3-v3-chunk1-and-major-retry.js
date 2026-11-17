export const meta = {
  name: 'b3-v3-chunk1-and-major-retry',
  description: 'B3 v3 people bios, token-thrifty: one fresh Sonnet agent per person, fetch_source.py excerpts only, verify.py checks quotes, Opus reviews an evidence pack. Resume, concurrency cap, and limit/dry-run.',
  phases: [
    { title: 'Major retry', detail: 'optional strengthened retry for returned major leaders' },
    { title: 'Research', detail: 'one fresh Sonnet agent per person, then merge into research.json' },
    { title: 'Retry', detail: 'one strengthened retry for people below the v3 minimum' },
    { title: 'Review', detail: 'Opus reviews the evidence pack; verify.py checks quotes' },
  ],
}

const fs = await import('node:fs')
const path = await import('node:path')
const { execFileSync } = await import('node:child_process')

const REPO = args.repo || '/Users/jack755051/Project/private/world_line-battle-demo'
const RAW_ROOT = args.rawRoot || '/Users/jack755051/wl-source-cache/b3full-v3'
const RULES = `工作目錄：${REPO}。只寫任務指定的 OUTDIR 與 RAWDIR。不要 git add／commit／push，不要寫任何資料庫，不要呼叫 5052 API，不要繞過 Cloudflare／Anubis／403，不要用 Wayback 代替被擋的頁。不要 Read、cat、head 整份 raw 原文，不要把整頁貼進上下文。`
const CHECK_MIN_NAME = 'check_min-report.json'
const PERSON_DONE = {
  type: 'object',
  properties: {
    bioId: { type: 'string' },
    name: { type: 'string' },
    searchLogSteps: { type: 'number' },
    fetched: { type: 'number' },
    note: { type: 'string', description: '60 words at most; do not paste quotes or page text' },
  },
  required: ['bioId', 'name', 'searchLogSteps', 'fetched', 'note'],
}
const SUMMARY = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    verifyOk: { type: 'boolean' },
    people: { type: 'array', items: { type: 'object', properties: {
      name: { type: 'string' }, paragraphs: { type: 'number' }, zhChars: { type: 'number' },
      meetsMinimum: { type: 'boolean' }, verdict: { type: 'string' } }, required: ['name', 'paragraphs', 'zhChars', 'meetsMinimum', 'verdict'] } },
    notes: { type: 'string' },
  },
  required: ['batch', 'verifyOk', 'people', 'notes'],
}

function asList(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.map(String)
  return String(value).split(',').map((part) => part.trim()).filter(Boolean)
}

function py(scriptArgs) {
  try {
    const out = execFileSync('python3', ['-I', ...scriptArgs], {
      cwd: REPO, encoding: 'utf8', maxBuffer: 32 * 1024 * 1024,
    })
    return { code: 0, out, err: '' }
  } catch (error) {
    return {
      code: error.status ?? 1,
      out: error.stdout ? String(error.stdout) : '',
      err: error.stderr ? String(error.stderr) : String(error),
    }
  }
}

function pyMust(scriptArgs) {
  const result = py(scriptArgs)
  if (result.code !== 0) {
    log(result.err || result.out)
    throw new Error(`${scriptArgs[0]} exit ${result.code}`)
  }
  return result.out
}

function rel(file) {
  return path.isAbsolute(file) ? file : path.join(REPO, file)
}

const concurrency = Math.max(1, Number(args.concurrency) || 3)
const dryRun = args.dryRun === true || args.dryRun === 'true'
const planArgs = [
  'tools/b3v3/plan_work.py',
  '--repo', REPO,
  '--prompt-dir', args.promptDir || path.join(REPO, '.dev/b3v3/prompts'),
  '--out-root', args.outRoot || 'data/seed/leaders/b3-trial/full/v3',
  '--raw-root', RAW_ROOT,
  '--concurrency', String(concurrency),
]
const chunk = asList(args.chunk)
if (chunk.length) planArgs.push('--chunk', chunk.join(','))
if (args.resume) planArgs.push('--resume', rel(args.resume))
if (args.limit !== undefined && args.limit !== null && args.limit !== '') planArgs.push('--limit', String(args.limit))
if (args.forceResearch === true || args.forceResearch === 'true') planArgs.push('--force-research')
if (!args.resume && !chunk.length) {
  log('需要 args.chunk 或 args.resume')
  return { error: 'need chunk or resume' }
}

const plan = JSON.parse(pyMust(planArgs))
log(`計畫 ${plan.batchCount} 批，每波最多 ${concurrency} 批，dryRun=${dryRun}`)
for (const batch of plan.batches) {
  const retry = batch.retry.mode === 'list' ? batch.retry.people.map((person) => person.name).join('、') : batch.retry.mode
  log(`batch${batch.nn} research=${batch.research} retry=${retry || 'none'} review=${batch.review} recheck=${batch.recheck} ${batch.skipResearchReason || ''}`)
}
if (dryRun) return plan

function personPath(batch, person) {
  return path.join(batch.outDir, 'people', `${person.bioId}.json`)
}

function personReady(file) {
  try {
    const data = JSON.parse(fs.readFileSync(file, 'utf8'))
    return Boolean(data && data.person && data.person.bioId && data.sources)
  } catch (_error) {
    return false
  }
}

function keywordHint(person) {
  const years = (person.line.match(/\d{4}/g) || []).slice(0, 4)
  return [person.name, person.nameZh, ...years].filter(Boolean).join('|')
}

function researchPrompt(batch, person) {
  return [
    `你只研究一個人，開一個全新的研究。不要研究提示詞裡的其他人。`,
    `人物：${person.line}`,
    `bioId：${person.bioId}`,
    `只寫這個檔：${personPath(batch, person)}`,
    `內容是一個 JSON 物件：person（一個人的完整條目）、sources、rawMap、researchedOn、policyVersion（bio-2026-11-v0）、alignedTo（b0b0e0f）、alignNote、schemaNote。不要寫 ${batch.outDir}/research.json。`,
    `規則檔（格式、來源分級、Q1–Q10、T14、最低 8 次查詢／4 種來源類型／原文語言檢索都要做）：${batch.researchPrompt}`,
    `抓取與引文不要照規則檔裡舊的 curl／整檔 Read。一律：`,
    `python3 -I tools/b3v3/fetch_source.py status --rawdir ${batch.rawDir} --rawmap ${batch.outDir}/rawmap.json`,
    `已有的 sourceKey 不要重抓。新頁：`,
    `python3 -I tools/b3v3/fetch_source.py fetch --rawdir ${batch.rawDir} --rawmap ${batch.outDir}/rawmap.json --source-key <sourceKey> --url <url> --keywords '${keywordHint(person)}'`,
    `抄 quote 只用 lookup，關鍵字改成你要的原文片段。WebFetch 只用於發現網址。`,
    `不要跑 verify.py 或 check_min.py。回覆不要貼引文或頁面。`,
    RULES,
  ].join('\n')
}

function retryPrompt(batch, person) {
  return [
    `只加強重跑一個人，不要改本批其他人。`,
    `人物：${person.line}`,
    `bioId：${person.bioId}`,
    `規則檔：${batch.retryPrompt}`,
    `先只讀這一份：${personPath(batch, person)}。不要讀整份 research.json，不要讀 raw 原文。`,
    `改完覆寫同一個單人檔。`,
    `抓取：python3 -I tools/b3v3/fetch_source.py status --rawdir ${batch.rawDir} --rawmap ${batch.outDir}/rawmap.json`,
    `已有的 sourceKey 不要重抓。新頁與 lookup 都用 fetch_source.py。建議關鍵字起點：${keywordHint(person)}`,
    `本輪新增：至少 5 種來源類型、15 次查詢（原文語言至少 4 次）、6 個新頁。searchLog 標 "round": "retry"。`,
    `仍不足就加 target=paragraph:length、note 以「篇幅不足：」開頭的 gap。`,
    `不要跑 check_min.py。回覆不要貼頁面。`,
    RULES,
  ].join('\n')
}

function reviewPromptFor(batch) {
  return [
    `你是審查者。規則檔 ${batch.reviewPrompt} 的來源分級、T14、最低標準、Q1–Q10 全部仍適用。`,
    batch.recheck ? `batch${batch.nn} 上次審查被中斷，請整批重查。` : `審查 batch${batch.nn}。`,
    `逐字引文是否在原文，以 verify.py 為準。請讀 ${batch.outDir}/evidence-pack.json（每筆 claim 的段落文字、quote、sourceKey、verify）與 ${batch.outDir}/research.json。`,
    `不要 Read 或 cat ${batch.rawDir} 的整檔，不要整批重抓網頁。全批最多 1 次抽查重抓，而且只能：`,
    `python3 -I tools/b3v3/fetch_source.py fetch --rawdir ${batch.rawDir} --rawmap ${batch.outDir}/rawmap.json --source-key <sourceKey> --url <url> --keywords '<詞>'`,
    `最低標準看 ${batch.outDir}/${CHECK_MIN_NAME}，不要自己跑 check_min.py。`,
    `改完 research.json 後跑 verify.py，只讀它印出的摘要，然後寫 ${batch.outDir}/review.json。`,
    RULES,
  ].join('\n')
}

async function runAgent(prompt, options) {
  try {
    return await agent(prompt, options)
  } catch (error) {
    log(`agent failed ${options.label}: ${error && error.message ? error.message : error}`)
    return null
  }
}

function runVerify(batch) {
  const report = path.join(batch.outDir, 'verify-report.json')
  const result = py([
    'data/seed/leaders/b3-trial/verify.py',
    path.join(batch.outDir, 'research.json'),
    '--report', report,
  ])
  log(`verify batch${batch.nn} exit ${result.code} ${(result.out || result.err).split('\n')[0]}`)
  return result.code === 0
}

function runCheckMin(batch) {
  const result = py(['data/seed/leaders/b3-trial/full/v3/check_min.py', path.join(batch.outDir, 'research.json')])
  log(`check_min batch${batch.nn} ${(result.out || result.err).trim()}`)
  return result.code === 0
}

function runEvidence(batch) {
  const result = py([
    'tools/b3v3/evidence_pack.py',
    path.join(batch.outDir, 'research.json'),
    '--out', path.join(batch.outDir, 'evidence-pack.json'),
  ])
  log(`evidence batch${batch.nn} exit ${result.code} ${(result.out || result.err).trim()}`)
  return result.code === 0
}

function mergePeople(batch, bioIds, mode) {
  const scriptArgs = [
    'tools/b3v3/merge_people.py', 'merge',
    '--outdir', batch.outDir,
    '--rawdir', batch.rawDir,
    '--batch', batch.batchId,
    '--order', bioIds.join(','),
  ]
  if (mode) scriptArgs.push(mode)
  const result = py(scriptArgs)
  log(`merge batch${batch.nn} ${mode || 'fresh'} exit ${result.code} ${(result.err || result.out).trim()}`)
  return result.code === 0
}

function extractPerson(batch, person) {
  fs.mkdirSync(path.join(batch.outDir, 'people'), { recursive: true })
  const result = py([
    'tools/b3v3/merge_people.py', 'extract',
    '--research', path.join(batch.outDir, 'research.json'),
    '--bio-id', person.bioId,
    '--out', personPath(batch, person),
  ])
  if (result.code !== 0) log(`extract ${person.bioId} ${result.err || result.out}`)
  return result.code === 0
}

function readFailing(batch) {
  try {
    const report = JSON.parse(fs.readFileSync(path.join(batch.outDir, CHECK_MIN_NAME), 'utf8'))
    const research = JSON.parse(fs.readFileSync(path.join(batch.outDir, 'research.json'), 'utf8'))
    const byKey = new Map((research.people || []).map((person) => [person.key, person]))
    return report.people.filter((row) => !row.meetsMinimum).map((row) => {
      const person = byKey.get(row.key) || {}
      return batch.people.find((item) => item.bioId === person.bioId) || {
        bioId: person.bioId, name: row.name, nameZh: person.nameZh || row.name, line: person.name || row.name,
      }
    }).filter((person) => person.bioId)
  } catch (error) {
    log(`batch${batch.nn} 讀不到 ${CHECK_MIN_NAME}：${error && error.message ? error.message : error}`)
    return []
  }
}

async function researchStage(batch) {
  if (!batch.research) {
    log(`batch${batch.nn} 略過研究（${batch.skipResearchReason || 'resume'}）`)
    return { ok: true, skippedResearch: true }
  }
  fs.mkdirSync(batch.rawDir, { recursive: true })
  fs.mkdirSync(path.join(batch.outDir, 'people'), { recursive: true })
  const pending = batch.people.filter((person) => !personReady(personPath(batch, person)))
  await Promise.all(pending.map((person) => runAgent(researchPrompt(batch, person), {
    label: `research:${batch.nn}:${person.bioId}`, phase: 'Research', model: 'sonnet', schema: PERSON_DONE,
  })))
  const missing = batch.people.filter((person) => !personReady(personPath(batch, person)))
  if (missing.length) {
    log(`batch${batch.nn} 缺單人檔：${missing.map((person) => person.name).join('、')}`)
    return { ok: false, missing: missing.map((person) => person.bioId) }
  }
  const mode = fs.existsSync(path.join(batch.outDir, 'research.json')) ? '--overwrite' : null
  if (!mergePeople(batch, batch.people.map((person) => person.bioId), mode)) return { ok: false }
  runVerify(batch)
  runCheckMin(batch)
  return { ok: true }
}

async function retryStage(prev, batch) {
  if (!prev || prev.ok === false) return prev || { ok: false }
  const people = batch.retry.mode === 'list' ? batch.retry.people : (batch.retry.mode === 'auto' ? readFailing(batch) : [])
  if (!people.length) {
    log(`batch${batch.nn} 沒有要重跑的人`)
    return prev
  }
  for (const person of people) {
    if (!extractPerson(batch, person)) return { ok: false }
  }
  await Promise.all(people.map((person) => runAgent(retryPrompt(batch, person), {
    label: `retry:${batch.nn}:${person.bioId}`, phase: 'Retry', model: 'sonnet', schema: PERSON_DONE,
  })))
  if (!mergePeople(batch, people.map((person) => person.bioId), '--replace')) return { ok: false }
  runVerify(batch)
  runCheckMin(batch)
  return { ok: true }
}

async function reviewStage(prev, batch) {
  if (!batch.review) return prev
  if (!prev || prev.ok === false) {
    log(`batch${batch.nn} 略過審查`)
    return prev || { ok: false }
  }
  runEvidence(batch)
  const reviewed = await runAgent(reviewPromptFor(batch), {
    label: `review:${batch.nn}`, phase: 'Review', schema: SUMMARY,
  })
  runVerify(batch)
  runCheckMin(batch)
  return reviewed || { ok: true, batch: batch.nn }
}

async function runMajor(items) {
  if (!items || !items.length) return []
  const results = []
  for (let index = 0; index < items.length; index += concurrency) {
    const slice = items.slice(index, index + concurrency)
    const part = await pipeline(slice, async (item) => {
      const outDir = item.outdir || item.outDir
      const rawDir = item.rawDir || path.join(RAW_ROOT, `batch${item.nn}`, 'raw')
      const names = (item.people || []).join('、')
      await runAgent([
        `只重跑這些人：${names}。目錄 ${outDir}。`,
        `抓取與引文只用 python3 -I tools/b3v3/fetch_source.py（先 status，已有的 sourceKey 不要重抓）。`,
        `禁止 Read 整份 raw。規則檔：${item.retry}`,
        RULES,
      ].join('\n'), { label: `major-retry:${item.nn}`, phase: 'Major retry', model: 'sonnet' })
      const batch = { nn: item.nn, outDir, rawDir }
      runVerify(batch)
      runCheckMin(batch)
      runEvidence(batch)
      return runAgent([
        `審查 ${outDir}。逐字引文看 ${outDir}/evidence-pack.json，不要重讀 raw，全批最多 1 次 fetch_source.py 抽查。`,
        `規則檔：${item.review}`,
        RULES,
      ].join('\n'), { label: `major-review:${item.nn}`, phase: 'Major retry', schema: SUMMARY })
    })
    results.push(...(part || []))
  }
  return results
}

const major = await runMajor(args.major || [])
const chunkResults = []
for (let index = 0; index < plan.batches.length; index += concurrency) {
  const slice = plan.batches.slice(index, index + concurrency)
  log(`開始第 ${index / concurrency + 1} 波：${slice.map((batch) => batch.nn).join('、')}`)
  const part = await pipeline(slice, researchStage, retryStage, reviewStage)
  chunkResults.push(...(part || []))
}
const done = chunkResults.filter((item) => item && item.ok !== false)
log(`完成 ${done.length}/${plan.batchCount} 批（major ${major.filter(Boolean).length}/${(args.major || []).length}）`)
return { major, chunk: chunkResults, planned: plan.batches.map((batch) => batch.nn) }
