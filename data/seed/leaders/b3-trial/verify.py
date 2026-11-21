"""B3 試跑離線檢查（不連任何資料庫、不連網）。以 ../b3-sample/verify.py 為底，加上 Tai 2026-11-11 09:35 定案（ARCHITECTURE §16.3.2）。

用法：python3 -I verify.py batchNN/research.json [--raw RAW_DIR RAWMAP.json] [--report out.json]
- 有 --raw：引文須空白正規化後逐字出現在研究當天抓下的原文（RAW_DIR 內純文字檔；RAWMAP：sourceKey → 檔名）。
  原文不進版控（著作權），報告只記 sha256。沒有 --raw 時只做格式檢查，報告標 rawChecked=false。
- 逐字比對由 quote_hit 做（空白正規化後的子字串）。tools/b3v3/evidence_pack.py 用同一函式產出審查用的短證據包，審查者不重讀原文。
- 若 research.json 頂層有 "rawDir"、"rawMap" 且未給 --raw，會自動採用（rawMap 為相對 research.json 的路徑）。
檢查：
 1. 引文 NFC ≤ 80 字元（§16.4.1）；非空；（有原文時）逐字出現。
 2. 每段落、每職位至少 1 筆 citation（§16.1-3）；段落／職位 citation 的 grade 必須是 A 或 B，且與來源一致（Q9：未評等來源只可出現在 gaps 候選）。
    將領生平檔（gradePolicy=ABC-2026-11-12 或 rawDir 含 /generals-）另收具名 C 級（Tai 2026-11-12 06:34）；C 須具名作者／出版機構，論壇／部落格／維基類不收。
 3. 來源網域不在硬性排除清單（含任何 wikipedia／wikidata／百度）；citation 的 sourceKey 必須存在於頂層 sources（建議 5）。
 4. Q2：段落中文 ≤ 400 字、英文 ≤ 800 字元（NFC code point）。ord 唯一；period 起 < 迄。
 5. Q3：month／year 精度的端點必須是該單位的起日（YYYY-MM-01／YYYY-01-01）。
 6. 職位 roleKind 不得為元首／首腦（Q4：範圍外元首任期只寫正文；元首／首腦任期只在 leader_records）；值域照 §16.3 提案。
 7. Q5：regimeId 非空時，職位期間必須與 1908-01-01～1945-10-01 有交集；regimeId 為空時須有 organization。
 8. Q7：evidenceNote 提到「下一任」者，必須同時含「推論」。
 9. gaps：target 格式、gap_kind 三值（§16.4.2）。
10. 每人必須有 bioId 鍵（建議 6；值可為 null）。
對齊後檔案（頂層 alignedTo == "b0b0e0f"，research.aligned.json；ARCHITECTURE b0b0e0f／T11／T12／T14）另加：
11. positions 用 positionKind，出現 roleKind 即違規；positionKind 值域沿用原 7 種（僅供參考，實作時再定）；不得為元首／首腦／實際掌權者。
12. roleCandidates 每筆必須有 citations（逐筆照第 1、2 項檢查）、role_kind ∈ {head_of_state, head_of_government, de_facto_leader}、reason 非空；
    不得有 roleKind／candidateRoleKind（Tai 2026-11-11 12:12 第 4 項：統一為 role_kind）。
13. t14Overlap 若有，值須為 cabinet／general／occupation_colonial。
14. positions 不得含 positionKind=party（Tai 2026-11-11 12:12 第 2 項：黨職一律移至 roleCandidates 為 de_facto_leader），
    除非該項標 partyPostAmbiguous=true 且附 partyPostAmbiguousReason；positionKind 不得為三種角色值（同第 11 項）。
T14 R0–R6（T14_RECOMMENDATION.md；Tai 2026-11-11 12:47 第 5 項）、黨籍席位（同日第 2 項）另加：
15. roleCandidates.role_kind 值域擴為 ROLE_LAYER_KINDS（元首／首腦／實際掌權者＋cabinet_minister、military_commander、
    occupation_administrator、colonial_governor）；positions.positionKind 不得為任何角色層值；positionKind 值域加 police、military_education。
16. 每筆帶 t14Overlap 的 positions 項須有 t14Rule ∈ R0–R6（或 t14Ambiguous=true 附理由）；positions 內 t14Rule 只可為 R5／R6，
    R0–R4 只能出現在 roleCandidates（兩層互斥），除非 t14Ambiguous=true。
17. t14Rule=R6 須 roleEligible=true、roleEligibleKind ∈ 角色層值、roleGap 非空、t14Reason 非空；非 R6 不得有 roleEligible。
18. positions 若有 originalPositionKind（邊界個案改類別），須與 positionKind 不同且屬原值域；roleCandidates 的 t14Rule 若有，須 ∈ R0–R4。
C 級補充區（Tai 2026-11-18；docs/source-rules.md §2「C 級補充區」）：
19. person.supplementC 是選填的獨立區塊，主段落／職位／角色永遠不引它。grade 必須是 "C"；sources 只放在區塊內（鍵不得與頂層 sources 重複）；
    Wikipedia／Wikidata 只准出現在這個區塊。每條 clauses／dates 要有 cKey（區塊內來源）、url、quote（NFC ≤80、逐字出現在原文）、locator、accessedOn。
    dates 只能是 待查證（status 以「待查證」開頭、confirmed 不得為 true）：C 單獨不能確認日期。
    A／B 為準（Tai 2026-11-18）：C 日期或句子和 A／B 衝突（tools/c_rules.py 的 date_conflict／clause_conflict）不得留在 clauses／dates，
    只能放 conflictNotes（附 conflictsWithAB.ref／reason，不顯示、不計入）；C 句子的年份／數字／拉丁專名／括號詞要出現在引文裡（support_gaps）。
    區塊的錯誤另列在報告的 supplementCErrors，不算進 errors／ok（主內容的判定不受 C 影響）；有 C 錯誤時 exit 仍是 1。
"""
import hashlib, json, re, sys, unicodedata
from pathlib import Path
from urllib.parse import urlparse

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(next(p for p in _Path(__file__).resolve().parents if (p / "data" / "source-policy.json").exists()) / "tools"))
import source_policy as _sp  # 全專案唯一的來源政策：data/source-policy.json
import c_rules as _cr  # C 級補充區：A／B 為準、引文支撐（tools/c_rules.py，與 tools/b3v3/tiers.py 共用）
_DATED = _sp.POLICY["bannedSince"]
# 後來才禁用的網域由 DATED_BANNED_HOSTS 依生效時間處理，所以不放進一律擋的清單
EXCLUDED_HOSTS = tuple(h for h in _sp.BANNED_HOSTS if h not in _DATED) + _sp.FILE_HOSTS
# 具名 C 級（Tai 本人 2026-11-12 06:34「將領生平來源放寬到具名 C 級」）：只對將領生平檔開放
# （頂層 gradePolicy == "ABC-2026-11-12"，或 rawDir 含 "/generals-"）；B3 其他檔仍只收 A／B。
# C 級來源須有具名作者或具名出版機構，且網域不得是論壇／部落格／維基類／AI 內容農場。
GRADE_C_POLICY = "ABC-2026-11-12"
C_BANNED_HOSTS = EXCLUDED_HOSTS + tuple(_sp.POLICY["bannedHostsForC"])
# 網域字樣（forum／bbs／blog／wiki…）改讀政策檔的 bannedHostLabels（整段字樣比對，含誤判例外），不再自帶子字串清單（2026-11-14）
# 主管 2026-11-12 22:08（套用 Tai 既有「個人網站不收」）：generals.dk 禁用。只擋本規則生效後新增的來源——
# apply_refill.py 對新增來源蓋 addedAt＝該補跑批開跑時間；addedAt ≥ 生效時間且網域命中 → 錯誤。既有已 commit 的引用（無 addedAt 或較早）不擋，
# 由 bios/refill/final_refill_report.py 列為「待替換」。
DATED_BANNED_HOSTS = {h: v["since"] for h, v in _DATED.items()}
BAN_DECISION = {h: v["decision"] for h, v in _DATED.items()}
ROLE_KINDS = {"minister", "legislator", "military_command", "party", "diplomat", "judicial", "other"}
ALIGNED_POSITION_KINDS = ROLE_KINDS | {"police", "military_education"}   # T14 文件 §4 邊界個案
ROLE_LAYER_KINDS = {"head_of_state", "head_of_government", "de_facto_leader", "cabinet_minister", "military_commander",
                    "occupation_administrator", "colonial_governor"}   # T14 文件 §1 R0–R4
T14_RULES = {"R0", "R1", "R2", "R3", "R4", "R5", "R6"}
ROLE_RULES = {"R0", "R1", "R2", "R3", "R4"}
FORBIDDEN_ROLES = {"head_of_state", "head_of_government"}
FORBIDDEN_ALIGNED = FORBIDDEN_ROLES | {"de_facto_leader"}
CANDIDATE_KINDS = ROLE_LAYER_KINDS
T14_VALUES = {"cabinet", "general", "occupation_colonial"}
GAP_KINDS = {"conflict", "not_found", "identity_uncertain"}
PREC = {None, "day", "month", "year"}
SCOPE_START, SCOPE_END = "1908-01-01", "1945-10-01"


# 將領 nameZh 正體檢查用（../generals-roster/zh_trad.py；OpenCC 在使用者層 venv，zh_trad 自行加路徑，因主迴圈用 python3 -I）
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location("zh_trad", str(Path(__file__).resolve().parent.parent / "generals-roster" / "zh_trad.py"))
    _zt = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_zt)
    _zt.to_trad("测试")
    _TO_TRAD, _TRAD_ERR = _zt.to_trad, None

    def _legacy_ok(nz):  # 10:07 版規則（s2t＋PROTECT，不含 t2tw／PRE）下是否已是正體
        t = _zt._load().convert(nz)
        return (t if len(t) != len(nz) else "".join(a if a in _zt.PROTECT else b for a, b in zip(nz, t))) == nz
except Exception as _e:  # noqa
    _TO_TRAD, _TRAD_ERR = None, repr(_e)


def norm(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", s)).strip()


def quote_hit(text_norm, quote):
    """回傳 quote 在空白正規化原文中的起點；沒有則 None。"""
    nq = norm(quote or "")
    if not nq or text_norm is None:
        return None
    i = text_norm.find(nq)
    return i if i >= 0 else None


def load_raw_texts(raw_dir, rawmap):
    """rawmap：sourceKey → 檔名。回傳 (texts, hashes, missing)；missing 是 (key, path)。"""
    texts, hashes, missing = {}, {}, []
    raw_dir = Path(raw_dir)
    for k, f in rawmap.items():
        p = raw_dir / f
        if not p.exists():
            missing.append((k, p))
            continue
        b = p.read_bytes()
        texts[k] = norm(b.decode("utf-8", errors="replace"))
        hashes[k] = {"file": f, "sha256": hashlib.sha256(b).hexdigest()}
    return texts, hashes, missing


def nfc_len(s):
    return len(unicodedata.normalize("NFC", s or ""))


def arg(name, n=1):
    if name not in sys.argv:
        return None
    i = sys.argv.index(name)
    return sys.argv[i + 1:i + 1 + n]


C_TARGET_RE = re.compile(r"(paragraph:length|identity|(position|role):[\w-]+\.(start|end))")
C_ALLOWED_INDEX_HOSTS = tuple(_sp.POLICY.get("supplementCOnlyHosts") or ("wikipedia.org", "wikidata.org"))  # 只在 supplementC 內准用
C_STATUS_PREFIX = "A/B不足，已用C補"


def _c_text(raw_dir, texts, key):
    """C 來源原文：先看 rawmap 載入的，沒有就讀 RAW_DIR/<key>.txt（C 鍵不一定在批次 rawmap 裡）。"""
    if key in texts:
        return texts[key]
    if raw_dir:
        path = Path(raw_dir) / f"{key}.txt"
        if path.is_file():
            return norm(path.read_bytes().decode("utf-8", errors="replace"))
    return None


def check_supplement_c(p, main_sources, texts, raw, raw_dir, errs):
    """第 19 項：C 級補充區。錯誤寫進 errs（報告的 supplementCErrors），回傳統計。"""
    key = p.get("key", "?")
    block = p.get("supplementC")
    where = f"{key} supplementC"
    if not isinstance(block, dict):
        errs.append(f"{where}：必須是物件"); return {}
    if block.get("grade") != "C":
        errs.append(f"{where}：grade 必須是 \"C\"")
    if not str(block.get("status") or "").startswith(C_STATUS_PREFIX):
        errs.append(f"{where}：status 須以「{C_STATUS_PREFIX}」開頭")
    csrc = block.get("sources") or {}
    if not isinstance(csrc, dict):
        errs.append(f"{where}：sources 必須是物件"); csrc = {}
    for k, s in csrc.items():
        if k in main_sources:
            errs.append(f"{where} 來源 {k}：鍵與主來源重複（C 來源只放在補充區）")
        if (s or {}).get("grade") != "C":
            errs.append(f"{where} 來源 {k}：grade 必須是 C")
        u = (s or {}).get("url") or ""
        host = (urlparse(u).hostname or "").lower() if u else ""
        if not host:
            errs.append(f"{where} 來源 {k}：缺 url")
        elif not any(host == h or host.endswith("." + h) for h in C_ALLOWED_INDEX_HOSTS):
            if any(host == h or host.endswith("." + h) or (("/" in h) and h in u.lower()) for h in C_BANNED_HOSTS) \
                    or _sp.banned_label(u):
                errs.append(f"{where} 來源 {k}：C 級網域不收（論壇／部落格／內容農場）：{host}")
        if not str((s or {}).get("title") or "").strip():
            errs.append(f"{where} 來源 {k}：缺 title")
    stats = {"clauses": 0, "dates": 0, "zhChars": 0, "sources": sorted(csrc)}

    def one(w, item):
        ck = item.get("cKey")
        if ck not in csrc:
            errs.append(f"{w}：cKey {ck} 不在 supplementC.sources"); return
        if not item.get("url"):
            errs.append(f"{w}：缺 url")
        elif item.get("url") != (csrc[ck] or {}).get("url"):
            errs.append(f"{w}：url 與來源 {ck} 不符")
        q = item.get("quote")
        if not q or not str(q).strip():
            errs.append(f"{w}：引文空白"); return
        n = nfc_len(q)
        if n > 80:
            errs.append(f"{w}：引文 {n} 字 > 80：{q}")
        if raw:
            text = _c_text(raw_dir, texts, ck)
            if text is None:
                errs.append(f"{w}：C 來源 {ck} 沒有原文檔，無法核對引文")
            elif quote_hit(text, q) is None:
                errs.append(f"{w}：引文未逐字出現於 {ck}：{q}")
        for field in ("locator", "accessedOn"):
            if not item.get(field):
                errs.append(f"{w}：缺 {field}")
        if not C_TARGET_RE.fullmatch(str(item.get("target") or "")):
            errs.append(f"{w}：target 格式（paragraph:length／identity／position:<key>.start|end／role:<key>.start|end）：{item.get('target')}")

    for i, c in enumerate(block.get("clauses") or []):
        w = f"{where} clause{i}"
        one(w, c)
        zh = (c.get("text") or {}).get("zh-Hant") if isinstance(c.get("text"), dict) else None
        en = (c.get("text") or {}).get("en") if isinstance(c.get("text"), dict) else None
        if not zh:
            errs.append(f"{w}：缺 text.zh-Hant")
        gaps = _cr.support_gaps(zh or "", c.get("quote") or "") + _cr.support_gaps(en or "", c.get("quote") or "", names=False)
        if gaps:
            errs.append(f"{w}：C 句子有引文沒有的內容 {sorted(set(gaps))}（要刪掉或改成只照引文寫）")
        long = _cr.overreach(zh or "", c.get("quote") or "")
        if long:
            errs.append(f"{w}：C 句子 {long[0]} 字，超過引文能支撐的 {long[1]} 字（要刪減或改成只照引文寫）")
        clash = _cr.clause_conflict(p, c)
        if clash:
            errs.append(f"{w}：與 A／B 衝突，以 A／B 為準（{clash['ref']}：{clash['reason']}）；要刪或移到 conflictNotes")
        stats["clauses"] += 1
        stats["zhChars"] += sum(1 for ch in unicodedata.normalize("NFC", zh or "") if not ch.isspace())
    for i, d in enumerate(block.get("dates") or []):
        w = f"{where} date{i}"
        one(w, d)
        if d.get("confirmed") is True or not str(d.get("status") or "").startswith("待查證"):
            errs.append(f"{w}：C 單獨不能確認日期，status 須以「待查證」開頭、confirmed 不得為 true")
        if d.get("precision") not in PREC - {None}:
            errs.append(f"{w}：precision 須為 day／month／year")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(d.get("value") or "")):
            errs.append(f"{w}：value 須為 YYYY-MM-DD")
        else:
            m = re.fullmatch(r"(position|role):([\w-]+)\.(start|end)", str(d.get("target") or ""))
            units = (p.get("positions") or []) + (p.get("roleCandidates") or [])
            if m and not any(u.get("key") == m.group(2) for u in units):
                errs.append(f"{w}：主內容沒有 {m.group(2)}")
            clash = _cr.date_conflict(p, d)
            if clash:
                errs.append(f"{w}：與 A／B 衝突，以 A／B 為準（{clash['reason']}）；要刪或移到 conflictNotes")
            if str(d.get("target") or "").endswith(".end") and not _cr.end_quote_ok(d.get("quote") or ""):
                errs.append(f"{w}：C 迄日的引文只寫就任／當選（起點事件），不能當這個職位的迄日")
            if int(str(d["value"])[:4]) not in _cr.years(d.get("quote") or ""):
                errs.append(f"{w}：value {d['value']} 的年份不在引文裡")
        stats["dates"] += 1
    for i, n in enumerate(block.get("conflictNotes") or []):   # 和 A／B 衝突的 C：只當註記，不顯示成事實、不計入
        w = f"{where} conflictNote{i}"
        one(w, n)
        ref = (n.get("conflictsWithAB") or {}) if isinstance(n.get("conflictsWithAB"), dict) else {}
        if not ref.get("ref") or not ref.get("reason"):
            errs.append(f"{w}：conflictsWithAB 要有 ref 與 reason")
        if n.get("confirmed") is True:
            errs.append(f"{w}：衝突註記不得 confirmed")
    stats["conflictNotes"] = len(block.get("conflictNotes") or [])
    return stats


def main():
    rp = Path(sys.argv[1])
    data = json.load(open(rp))
    report_path = (arg("--report") or [None])[0]
    raw = arg("--raw", 2)
    if not raw and data.get("rawDir") and data.get("rawMap"):
        raw = [data["rawDir"], str(rp.parent / data["rawMap"])]
    texts, hashes, errs, warns, stats = {}, {}, [], [], {}
    if raw:
        raw_dir, rawmap = raw[0], json.load(open(raw[1]))
        texts, hashes, missing = load_raw_texts(raw_dir, rawmap)
        for k, p in missing:
            errs.append(f"原文檔不存在：{k} → {p}")
    srcs = data.get("sources") or {}
    allow_c = data.get("gradePolicy") == GRADE_C_POLICY or "/generals-" in str(data.get("rawDir") or "")
    OKG = ("A", "B", "C") if allow_c else ("A", "B")

    # 只出現在缺口候選的來源：照 2026-11-13 來源規則（I6／D4）也要評等，C 級可留（候選本來就不是出處，Q9）；
    # 段落／職位／角色的 citation 仍只收 OKG（下方逐筆檢查）。
    def _fact_keys(o, cand=False, out=None):
        out = set() if out is None else out
        if isinstance(o, dict):
            if "sourceKey" in o and not cand: out.add(o["sourceKey"])
            for kk, v in o.items(): _fact_keys(v, cand or kk == "candidateCitations", out)
        elif isinstance(o, list):
            for v in o: _fact_keys(v, cand, out)
        return out
    def _main_only(person):
        return {k: v for k, v in person.items() if k != "supplementC"} if isinstance(person, dict) else person
    fact_keys = _fact_keys([_main_only(x) for x in data.get("people") or []])
    for k, s in srcs.items():
        for u in (s.get("url"), s.get("archive_url")):
            host = (urlparse(u).hostname or "") if u else ""
            if any(host == h or host.endswith("." + h) for h in EXCLUDED_HOSTS):
                errs.append(f"來源 {k} 網域被排除：{host}")
        for u in (s.get("url"), s.get("archive_url")):
            host = ((urlparse(u).hostname or "") if u else "").lower()
            for h, since in DATED_BANNED_HOSTS.items():
                if (host == h or host.endswith("." + h)) and str(s.get("addedAt") or "") >= since:
                    errs.append(f"來源 {k} 網域已禁用（{h}，{BAN_DECISION[h]}，個人／無署名網站）：addedAt {s.get('addedAt')}")
        for u in (s.get("url"), s.get("archive_url")):  # 網域字樣（blogs／forum…）不分等級都禁用（2026-11-17：B 級 hoover.blogs 漏網）
            if u and _sp.banned_label(u):
                errs.append(f"來源 {k}：網域含禁用字樣「{_sp.banned_label(u)}」（source-policy bannedHostLabels）：{urlparse(u).hostname}")
        if s.get("grade") not in (None,) + OKG and not (s.get("grade") == "C" and k not in fact_keys):
            errs.append(f"來源 {k} grade 非法：{s.get('grade')}")
        if s.get("grade") == "C":
            if not ([a for a in (s.get("authors") or []) if str(a).strip()] or str(s.get("publisher") or "").strip()):
                errs.append(f"來源 {k}：C 級須有具名作者或具名出版機構")
            for u in (s.get("url"), s.get("archive_url")):
                if not u:
                    continue
                host = (urlparse(u).hostname or "").lower()
                full = u.lower()
                if any(host == h or host.endswith("." + h) or (("/" in h) and h in full) for h in C_BANNED_HOSTS) \
                        or _sp.banned_label(u):
                    errs.append(f"來源 {k}：C 級網域不收（論壇／部落格／維基類／內容農場）：{host}")
    blob = json.dumps(dict(data, people=[_main_only(x) for x in data.get("people") or []]), ensure_ascii=False).lower()
    if "wikipedia" in blob or "wikidata.org" in blob:
        for m in re.finditer(r"https?://[^\s\"']*(wikipedia|wikidata)[^\s\"']*", blob):
            errs.append(f"檔內出現 Wikipedia／Wikidata 網址：{m.group(0)}")

    qlens = []

    def chk_quote(where, sk, q):
        if sk not in srcs:
            errs.append(f"{where}：未知來源 {sk}"); return 0
        if not q or not q.strip():
            errs.append(f"{where}：引文空白"); return 0
        n = nfc_len(q)
        if n > 80:
            errs.append(f"{where}：引文 {n} 字 > 80：{q}")
        if raw:
            if sk not in texts:
                errs.append(f"{where}：來源 {sk} 沒有原文檔，無法核對引文")
            elif quote_hit(texts[sk], q) is None:
                errs.append(f"{where}：引文未逐字出現於 {sk}：{q}")
        return n

    def chk_bound(where, d, prec, end):
        if not d or prec in (None, "day"):
            return
        if prec == "year" and not d.endswith("-01-01"):
            errs.append(f"{where}：year 精度{'終點' if end else '起點'}須為 YYYY-01-01（Q3），實為 {d}")
        if prec == "month" and not d.endswith("-01"):
            errs.append(f"{where}：month 精度{'終點' if end else '起點'}須為 YYYY-MM-01（Q3），實為 {d}")

    aligned = data.get("alignedTo") == "b0b0e0f"
    if aligned and not data.get("alignNote"):
        errs.append("對齊檔缺 alignNote")
    people = data.get("people") or []
    if not people:
        errs.append("people 為空")
    for p in people:
        key = p.get("key", "?")
        if allow_c:  # 將領生平檔：nameZh 須等於 zh_trad.to_trad(nameZh)（s2t→t2tw 台灣字形＋PRE＋PROTECT；World Line 主管 2026-11-12 10:07／10:20）
            nz = p.get("nameZh")
            if _TO_TRAD is None:
                errs.append(f"{key}：無法載入 zh_trad／OpenCC，nameZh 正體檢查無法執行（{_TRAD_ERR}）")
            elif isinstance(nz, str) and nz and _TO_TRAD(nz) != nz:
                # 過渡：A/batch022 在 10:20 字形規則加入前已開跑；若只差台灣字形（10:07 版 s2t 規則已過）只記 note，commit 後由 patch_name_trad.py 補轉；A/batch023 起一律擋
                if "/A/batch022/" in str(data.get("rawDir") or "") and _legacy_ok(nz):
                    warns.append(f"{key}：nameZh 非台灣標準字形（過渡批，待 patch_name_trad.py）：{nz} → {_TO_TRAD(nz)}")
                else:
                    errs.append(f"{key}：nameZh 非正體／非台灣標準字形：{nz} → {_TO_TRAD(nz)}")
        if "bioId" not in p:
            errs.append(f"{key}：缺 bioId 鍵（建議 6）")
        paras, poss, gaps = p.get("paragraphs", []), p.get("positions", []), p.get("gaps", [])
        st = stats[key] = {"paragraphs": len(paras), "positions": len(poss), "gaps": len(gaps), "citations": 0, "sources": set()}
        if not paras:
            warns.append(f"{key}：沒有段落（薄資料可接受 1 段＋待查證，0 段需在 gaps 說明）")
        ords = [x.get("ord") for x in paras]
        if len(set(ords)) != len(ords):
            errs.append(f"{key}：ord 重複")
        items = [(f"{key} 段{x.get('ord')}", x, x.get("period") or {}, x.get("periodStartPrecision"), x.get("periodEndPrecision")) for x in paras]
        items += [(f"{key} 職位 {x.get('key')}", x, x.get("period") or {}, x.get("startPrecision"), x.get("endPrecision")) for x in poss]
        for where, x, per, sp, ep in items:
            cits = x.get("citations") or []
            if not cits:
                errs.append(f"{where}：沒有 citation")
            if sp not in PREC or ep not in PREC:
                errs.append(f"{where}：精度值非法")
            if (per.get("start") is None) != (sp is None) or (per.get("end") is None) != (ep is None):
                errs.append(f"{where}：期間端點與精度不一致")
            if per.get("start") and per.get("end") and per["start"] >= per["end"]:
                errs.append(f"{where}：起 >= 迄")
            chk_bound(where, per.get("start"), sp, False)
            chk_bound(where, per.get("end"), ep, True)
            for i, c in enumerate(cits):
                qlens.append(chk_quote(f"{where} c{i}", c.get("sourceKey"), c.get("quote")))
                st["citations"] += 1; st["sources"].add(c.get("sourceKey"))
                if c.get("grade") not in OKG:
                    errs.append(f"{where} c{i}：段落／職位出處須 {'／'.join(OKG)}，實為 {c.get('grade')}（Q9）")
                if c.get("sourceKey") in srcs and c.get("grade") != srcs[c["sourceKey"]].get("grade"):
                    errs.append(f"{where} c{i}：grade 與來源不符")
                if c.get("datePrecision") not in PREC:
                    errs.append(f"{where} c{i}：datePrecision 非法")
                if not c.get("locator"):
                    errs.append(f"{where} c{i}：缺 locator")
                if not c.get("accessedOn"):
                    errs.append(f"{where} c{i}：缺 accessedOn")
                note = c.get("evidenceNote") or ""
                if "下一任" in note and "推論" not in note:
                    errs.append(f"{where} c{i}：以下一任起日推得的迄日須在 evidenceNote 標「推論」（Q7）")
        for x in paras:
            body = x.get("body") or {}
            zh, en = nfc_len(body.get("zh-Hant")), nfc_len(body.get("en"))
            if not zh:
                errs.append(f"{key} 段{x.get('ord')}：缺 zh-Hant 正文")
            if zh > 400:
                errs.append(f"{key} 段{x.get('ord')} zh-Hant 正文 {zh} 字 > 400（Q2）")
            if en > 800:
                errs.append(f"{key} 段{x.get('ord')} en 正文 {en} 字元 > 800（Q2）")
        if aligned:
            for x in poss:
                w = f"{key} 職位 {x.get('key')}"
                if "roleKind" in x:
                    errs.append(f"{w}：對齊檔不得再用 roleKind，須為 positionKind")
                if x.get("positionKind") in ROLE_LAYER_KINDS:
                    errs.append(f"{w}：經歷層不得含角色層值 {x.get('positionKind')}（兩層互斥）")
                if "originalPositionKind" in x and (x["originalPositionKind"] == x.get("positionKind")
                                                    or x["originalPositionKind"] not in ROLE_KINDS):
                    errs.append(f"{w}：originalPositionKind 須屬原值域且與 positionKind 不同")
                amb = x.get("t14Ambiguous")
                if "t14Ambiguous" in x and (amb is not True or not (x.get("t14AmbiguousReason") or "").strip()):
                    errs.append(f"{w}：t14Ambiguous 須為 true 且附 t14AmbiguousReason")
                r = x.get("t14Rule")
                if "t14Overlap" in x and r not in T14_RULES and amb is not True:
                    errs.append(f"{w}：t14Overlap 項須有 t14Rule（R0–R6）或標 t14Ambiguous")
                if r is not None and r not in T14_RULES:
                    errs.append(f"{w}：t14Rule 非法 {r}")
                if r in ROLE_RULES and amb is not True:
                    errs.append(f"{w}：t14Rule={r} 屬角色層，須移至 roleCandidates（兩層互斥）")
                if r and not (x.get("t14Reason") or "").strip():
                    errs.append(f"{w}：有 t14Rule 須附 t14Reason")
                if r == "R6":
                    if x.get("roleEligible") is not True or x.get("roleEligibleKind") not in ROLE_LAYER_KINDS - FORBIDDEN_ALIGNED \
                            or not x.get("roleGap"):
                        errs.append(f"{w}：R6 須 roleEligible=true、roleEligibleKind（閣員／將領／佔領殖民長官）、roleGap 非空")
                elif any(k in x for k in ("roleEligible", "roleEligibleKind", "roleGap")):
                    errs.append(f"{w}：非 R6 不得有 roleEligible／roleEligibleKind／roleGap")
                if x.get("positionKind") == "party" and x.get("partyPostAmbiguous") is not True:
                    errs.append(f"{w}：黨職須移至 roleCandidates（de_facto_leader），或標 partyPostAmbiguous")
                if "partyPostAmbiguous" in x and (x["partyPostAmbiguous"] is not True
                                                  or not (x.get("partyPostAmbiguousReason") or "").strip()):
                    errs.append(f"{w}：partyPostAmbiguous 須為 true 且附 partyPostAmbiguousReason")
                if "t14Overlap" in x and x["t14Overlap"] not in T14_VALUES:
                    errs.append(f"{w}：t14Overlap 非法 {x['t14Overlap']}")
            for x in p.get("roleCandidates") or []:
                w = f"{key} 候選角色 {x.get('key')}"
                if x.get("role_kind") not in CANDIDATE_KINDS:
                    errs.append(f"{w}：role_kind 非法或缺 {x.get('role_kind')}")
                for bad in ("roleKind", "candidateRoleKind"):
                    if bad in x:
                        errs.append(f"{w}：不得有 {bad}（統一為 role_kind）")
                if not (x.get("reason") or "").strip():
                    errs.append(f"{w}：缺 reason")
                if "t14Rule" in x and x["t14Rule"] not in ROLE_RULES:
                    errs.append(f"{w}：roleCandidates 的 t14Rule 須為 R0–R4，實為 {x['t14Rule']}")
                if "positionKind" in x or "roleEligible" in x:
                    errs.append(f"{w}：roleCandidates 不得有 positionKind／roleEligible（原值存 originalPositionKind）")
                cc = x.get("citations") or []
                if not cc:
                    errs.append(f"{w}：沒有 citation（出處）")
                for i, c in enumerate(cc):
                    chk_quote(f"{w} c{i}", c.get("sourceKey"), c.get("quote"))
                    if c.get("grade") not in OKG:
                        errs.append(f"{w} c{i}：grade 須 {'／'.join(OKG)}")
                    if c.get("sourceKey") in srcs and c.get("grade") != srcs[c["sourceKey"]].get("grade"):
                        errs.append(f"{w} c{i}：grade 與來源不符")
            st["roleCandidates"] = len(p.get("roleCandidates") or [])
        for x in poss:
            rk = x.get("positionKind") if aligned else x.get("roleKind")
            if rk in (FORBIDDEN_ALIGNED if aligned else FORBIDDEN_ROLES):
                errs.append(f"{key} 職位 {x.get('key')}：不得建元首／首腦職位（§16.3、Q4）")
            elif rk not in (ALIGNED_POSITION_KINDS if aligned else ROLE_KINDS):
                errs.append(f"{key} 職位 {x.get('key')}：role_kind 非法 {rk}")
            per = x.get("period") or {}
            if x.get("regimeId"):
                s, e = per.get("start"), per.get("end")
                if (s and s >= SCOPE_END) or (e and e <= SCOPE_START) or (not s and not e):
                    errs.append(f"{key} 職位 {x.get('key')}：regimeId 只可填於清楚落在 1908–1945 的職位（Q5）")
            elif not x.get("organization"):
                errs.append(f"{key} 職位 {x.get('key')}：regimeId 空時須填 organization（Q5）")
        for g in gaps:
            if not re.fullmatch(r"(field:\w+|position:[\w-]+|role:[\w-]+|paragraph:[\w-]+|identity)", g.get("target", "")):  # role: 與 DB 約束、check_min.py 一致（2026-11-15）
                errs.append(f"{key} gap target 格式：{g.get('target')}")
            if g.get("gapKind") not in GAP_KINDS:
                errs.append(f"{key} gap_kind 非法：{g.get('gapKind')}")
            for i, c in enumerate(g.get("candidateCitations") or []):
                chk_quote(f"{key} gap {g.get('target')} cand{i}", c.get("sourceKey"), c.get("quote"))
        st["sources"] = sorted(s for s in st["sources"] if s)
    c_errs, c_stats = [], {}
    for p in people:
        if "supplementC" in p:
            c_stats[p.get("key", "?")] = check_supplement_c(p, srcs, texts, raw, raw[0] if raw else None, c_errs)
    qn = [n for n in qlens if n]
    rep = {"ok": not errs, "rawChecked": bool(raw), "errors": errs, "notes": warns, "people": stats,
           "quoteLen": {"n": len(qn), "max": max(qn) if qn else 0, "min": min(qn) if qn else 0}, "rawFiles": hashes,
           "supplementCOk": not c_errs, "supplementCErrors": c_errs, "supplementC": c_stats}
    if report_path:
        Path(report_path).write_text(json.dumps(rep, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps({k: rep[k] for k in ("ok", "rawChecked", "errors", "quoteLen", "supplementCOk", "supplementCErrors")},
                     ensure_ascii=False, indent=1))
    for k, v in stats.items():
        print(k, v["paragraphs"], "段", v["positions"], "職位", v["gaps"], "缺漏", v["citations"], "引用")
    sys.exit(0 if not errs and not c_errs else 1)


if __name__ == "__main__":
    main()
