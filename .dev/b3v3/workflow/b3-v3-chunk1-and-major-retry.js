export const meta = {
  name: 'b3-v3-chunk1-and-major-retry',
  description: 'B3 v3 people bios: major-leader retries (6 people) + rollout chunk 1 (batches 003-032, 90 people); research, retry if below minimum, Opus review; seed only',
  phases: [
    { title: 'Major retry', detail: 'retry then re-review the 6 returned major leaders' },
    { title: 'Research', detail: 'Sonnet research per batch' },
    { title: 'Retry', detail: 'one strengthened retry for people below the v3 minimum' },
    { title: 'Review', detail: 'Opus review, verify.py and check_min.py' },
  ],
}

const REPO = '/Users/jack755051/Project/private/world_line-battle-demo'
const RULES = `Working directory: ${REPO}. Write only to the OUTDIR and RAWDIR named in the instructions. Do not git add/commit/push, do not write to any database, do not call the 5052 API, do not bypass bot protection (Cloudflare/Anubis/403: give up and log it), do not use Wayback copies as substitutes.`
const CHECK = {
  type: 'object',
  properties: {
    batch: { type: 'string' },
    verifyOk: { type: 'boolean' },
    belowMinimum: { type: 'array', items: { type: 'string' }, description: 'names of people who do not meet the v3 minimum per check_min.py' },
    note: { type: 'string' },
  },
  required: ['batch', 'verifyOk', 'belowMinimum', 'note'],
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
const reviewPrompt = (file, outdir, nn, extra) =>
  `Follow the instructions in ${file} exactly to review the research output in ${outdir}. ${extra || ''} ${RULES} Edit only files inside ${outdir}. ` +
  `After reviewing, run data/seed/leaders/b3-trial/verify.py (must be ok with rawChecked=true) and data/seed/leaders/b3-trial/full/v3/check_min.py, ` +
  `then return the structured summary (batch="${nn}"; verdict per person: pass, pass_with_changes or returned; notes under 100 words: what you changed, removed or moved to gaps).`

const majorRun = pipeline(
  args.major,
  (b) => agent(`Follow the instructions in ${b.retry} exactly: one strengthened retry for ${b.people.join('、')} in ${b.outdir}. ${RULES} ` +
    `Then run verify.py and v3/check_min.py on the batch and report in under 120 words what changed per person.`,
    { label: `major-retry:${b.nn}`, phase: 'Major retry', model: 'sonnet' }),
  (rep, b) => agent(reviewPrompt(b.review, b.outdir, `major-${b.nn}`, `Only the retried people (${b.people.join('、')}) changed since the last review; focus on them, keep the others as previously reviewed. The retry agent reported: ${rep}`),
    { label: `major-review:${b.nn}`, phase: 'Major retry', schema: SUMMARY }),
)

const P = args.promptDir, OUT = args.outRoot
const chunkRun = pipeline(
  args.chunk,
  (nn) => agent(`Follow the instructions in ${P}/research-${nn}.md exactly to research B3 full v3 batch${nn}. ${RULES} ` +
    `When done, run data/seed/leaders/b3-trial/verify.py and data/seed/leaders/b3-trial/full/v3/check_min.py on ${OUT}/batch${nn}/research.json and return the structured check (batch="${nn}").`,
    { label: `research:${nn}`, phase: 'Research', model: 'sonnet', schema: CHECK }),
  async (chk, nn) => {
    if (chk && chk.belowMinimum && chk.belowMinimum.length) {
      await agent(`Follow the instructions in ${P}/retry-${nn}.md for a single strengthened retry of batch${nn}. The people below the v3 minimum are: ${chk.belowMinimum.join('、')} — retry only them (the PEOPLE list in the file is the whole batch; ignore anyone not named here). ` +
        `The minimum-check report is in ${OUT}/batch${nn} (check_min output). If someone still falls short after the retry, add the 篇幅不足 gap as the rules say. ${RULES} Report in under 80 words.`,
        { label: `retry:${nn}`, phase: 'Retry', model: 'sonnet' })
    }
    return chk
  },
  (chk, nn) => agent(reviewPrompt(`${P}/review-${nn}.md`, `${OUT}/batch${nn}`, nn, ''), { label: `review:${nn}`, phase: 'Review', schema: SUMMARY }),
)

const [major, chunk] = await Promise.all([majorRun, chunkRun])
const okMajor = major.filter(Boolean), okChunk = chunk.filter(Boolean)
log(`major retry: ${okMajor.length}/${args.major.length} batches; chunk 1: ${okChunk.length}/${args.chunk.length} batches reviewed`)
return { major: okMajor, chunk: okChunk, missingChunk: args.chunk.filter((nn, i) => !chunk[i]) }