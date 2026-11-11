"""把 B3 試跑 research.json 對齊 ARCHITECTURE.md b0b0e0f（人物／角色／經歷三層；§16.3.2/16.3.3/16.9 T11,T12,T14）。

用法：python3 -I align_b0b0e0f.py        （在 b3-trial 目錄下或任意處皆可）
輸入：batchNN/research.json（不修改）；輸出：batchNN/research.aligned.json、align-report.json。可重跑、冪等（輸入固定→輸出逐位元相同；不含時間戳）。
做的事（只搬移／改名／加標記，不新增或改寫任何引文、日期、出處）：
 1. positions[*].roleKind → positionKind（值照搬）。
 2. 元首／國家首腦／政府首腦／實際掌權者的經歷 → 移出 positions，放進該人的 roleCandidates
    （保留原欄位含 citations；加 role_kind、reason；原 positionKind 改存 originalPositionKind）。不建立角色資料。
 2b. 黨職（Tai 2026-11-11 12:12 第 2 項「黨職一律算 de_facto_leader」）：positionKind=party 者一律移入 roleCandidates，
    role_kind=de_facto_leader。positionKind 非 party、但標題／機構含政黨字樣者不猜，留在原處加 partyPostAmbiguous、
    partyPostAmbiguousReason。候選角色種類欄位一律為 role_kind（Tai 同日第 4 項），不再有 roleKind／candidateRoleKind。
 3. T14 重疊類別留在 positions，加 t14Overlap：cabinet｜general｜occupation_colonial。
 4. 頂層加 alignedTo、alignNote。
判斷規則見下方 PARTY_*／ HEAD_PATTERNS／PERSON_OVERRIDES／T14 規則，可直接審視。
"""
import json, re, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALIGN_NOTE = ("依 ARCHITECTURE.md b0b0e0f（Tai 2026-11-11 10:03，T11／T12）對齊：經歷層欄位 roleKind 改名 positionKind（值照搬）；"
              "元首／首腦／實際掌權者移至 roleCandidates（僅為候選，未建角色、未寫庫）；T14 重疊類別以 t14Overlap 標記，仍留在 positions。"
              "Tai 2026-11-11 12:12：黨職一律算 de_facto_leader（移至 roleCandidates）；roleCandidates 角色種類欄位統一為 role_kind，原經歷種類存 originalPositionKind。"
              "由 align_b0b0e0f.py 產生，原 research.json 未動。")

# 若標題含這些詞，代表是機構內職務／副職／幕僚，不是首腦本身
GUARD = re.compile(
    r"(party|council|senate|chamber|bank|university|academy|committee|court|commission|secretary|adviser|advisor|"
    r"deputy|vice|assistant|minister of|ministro de|ministre de|governor|house of|peers|partido|partito|parti |directório|directorio|"
    r"黨|議會|院|議長|主席|委員|秘書|顧問|副|部長|大臣|州長|省長|銀行|大學|學校)", re.I)

# (candidateRoleKind, 標題需「起首」符合的 pattern)；依 orig / zh-Hant / en 三個標題分別比對
HEAD_PATTERNS = [
    ("head_of_state", re.compile(r"^(the )?(president|king|queen|emperor|empress|tsar|czar|sultan|shah|emir|regent|head of state|"
                                  r"reichspräsident|presidente|re |rey |imperatore|imperador|emperador|regente|regent)\b", re.I)),
    ("head_of_state", re.compile(r"^(總統|國王|君主|皇帝|天皇|沙皇|蘇丹|沙阿|埃米爾|攝政|國家元首|大統領|執政|教宗)")),
    ("head_of_government", re.compile(r"^(the )?(prime minister|premier|chancellor|reichskanzler|kanzler|ministerpräsident|"
                                       r"president of the council|presidente del consiglio|primo ministro|primer ministro|head of government)\b", re.I)),
    ("head_of_government", re.compile(r"^(首相|總理|閣揆|行政院長|內閣總理|總理大臣)")),
    ("de_facto_leader", re.compile(r"^(the )?(dictator|duce|führer|fuehrer|caudillo|supreme leader|strongman|chief executive)\b", re.I)),
    ("de_facto_leader", re.compile(r"^(獨裁者|領袖|最高領導人|強人|元帥兼執政)")),
]

# 個案覆寫：(人物 key, 職位 key) → (role_kind, reason)。標題無法判斷、需依內容的才放這裡；全部列入 ALIGN.md 供 Tai 複核。
# （原有的蘇共總書記、國民黨總裁兩筆已由下方黨職規則涵蓋，故移除。）
PERSON_OVERRIDES = {}

# 黨職規則（Tai 2026-11-11 12:12 第 2 項）
PARTY_REASON = "Tai 2026-11-11 12:12：黨職一律算 de_facto_leader"
# 標題／機構含政黨字樣：positionKind 非 party 時只標 ambiguous，不移動
PARTY_HINT = re.compile(r"(黨|\bparty\b|\bpartido\b|\bpartito\b|\bparti\b|kuomintang|communist|union and progress|"
                        r"secretary[- ]general|general secretary|總書記|書記長|黨魁)", re.I)
# 個案：(人物 key, 職位 key) → 標 ambiguous 的理由；未列者由 PARTY_HINT 自動產生通用理由
PARTY_AMBIGUOUS_REASONS = {
    ("pt-salazar", "deputy-1921"): "標題「議員（天主教中央黨）」含政黨名稱，但 positionKind=legislator、機構為葡萄牙議會，"
                                   "較像以該黨身分當選的議會席位而非黨內職務；依指示不猜，留在 positions，待 Tai 決",
}

T14_OCC = re.compile(r"(colon|dependenc|netherlands indies|殖民|屬地|佔領|占領|occupation|occupied|protectorate|保護國)", re.I)
T14_GOV = re.compile(r"(governor|gouverneur|gobernador|總督|governor-general|resident-general|高級專員|high commissioner|軍政長官)", re.I)


def texts(x):
    t = x.get("title") or {}
    o = x.get("organization") or {}
    tl = [t.get(k) or "" for k in ("orig", "zh-Hant", "en")]
    ol = [o.get(k) or "" for k in ("zh-Hant", "en")]
    return [unicodedata.normalize("NFC", s).strip() for s in tl], [unicodedata.normalize("NFC", s) for s in ol]


def head_kind(x, pkey):
    ov = PERSON_OVERRIDES.get((pkey, x.get("key")))
    if ov:
        return ov
    titles, _ = texts(x)
    if any(GUARD.search(t) for t in titles):   # 任一語種標題出現副職／機構內職務字樣即不算首腦
        return None
    for kind, pat in HEAD_PATTERNS:
        for t in titles:
            if t and pat.search(t):
                return kind, f"職稱「{t}」起首符合 {kind} 規則（{pat.pattern[:40]}…）且無副職／機構內職務字樣"
    return None


def party_status(x, pkey):
    """回傳 'move'（黨職→de_facto_leader 候選）、('ambiguous', 理由) 或 None。"""
    pk = x.get("positionKind", x.get("roleKind"))
    if pk == "party":
        return "move"
    titles, orgs = texts(x)
    if any(PARTY_HINT.search(t) for t in titles + orgs if t):
        return ("ambiguous", PARTY_AMBIGUOUS_REASONS.get((pkey, x.get("key")),
                f"標題／機構含政黨字樣但 positionKind={pk}，無法確定是否為政黨內職務；依指示不猜，留在 positions，待 Tai 決"))
    return None


def to_candidate(y, role_kind, reason):
    """positions 項 → roleCandidates 項：positionKind 原位改名 originalPositionKind（值照搬），其餘欄位原樣，加 role_kind、reason。"""
    c = {("originalPositionKind" if k == "positionKind" else k): v for k, v in y.items()}
    c["role_kind"], c["reason"] = role_kind, reason
    return c


def normalize_candidate(c):
    """既有 roleCandidates 項（舊格式）統一：roleKind→originalPositionKind、candidateRoleKind→role_kind。"""
    out = {}
    for k, v in c.items():
        if k == "roleKind":
            out["originalPositionKind"] = v
        elif k == "candidateRoleKind":
            out["role_kind"] = v
        else:
            out[k] = v
    return out


def t14_kind(x):
    titles, orgs = texts(x)
    blob = " ".join(titles + orgs)
    if T14_GOV.search(" ".join(titles)) and T14_OCC.search(blob):
        return "occupation_colonial"
    pk = x.get("positionKind")
    if pk == "minister":
        return "cabinet"
    if pk == "military_command":
        return "general"
    return None


def move_entry(batch, p, x, role_kind, rule, reason):
    per = x.get("period") or {}
    t = x.get("title") or {}
    return {"batch": batch, "person": p.get("key"), "name": p.get("name"), "nameZh": p.get("nameZh"),
            "position": x.get("key"), "titleOrig": t.get("orig"), "title": t.get("zh-Hant"),
            "start": per.get("start"), "end": per.get("end"),
            "originalPositionKind": x.get("roleKind", x.get("positionKind")), "role_kind": role_kind,
            "rule": rule, "reason": reason}


def align_file(path):
    d = json.load(open(path, encoding="utf-8"))
    batch = path.parent.name
    st = {"renamed": 0, "movedToCandidates": {}, "movedPartyPosts": 0, "partyPostAmbiguous": 0, "t14": {},
          "movedList": [], "ambiguousList": [], "t14List": []}
    for p in d.get("people", []):
        pkey = p.get("key")
        keep, cands = [], [normalize_candidate(c) for c in (p.get("roleCandidates") or [])]
        for x in p.get("positions", []):
            had_role = "roleKind" in x
            y = {("positionKind" if k == "roleKind" else k): v for k, v in x.items()}   # 保持欄位順序
            if had_role:
                st["renamed"] += 1
            ps = party_status(y, pkey)
            if ps == "move":
                hk, rule = ("de_facto_leader", PARTY_REASON), "party_post"
                st["movedPartyPosts"] += 1
            else:
                hk, rule = head_kind(x, pkey), "head_pattern"
            if hk:
                cands.append(to_candidate(y, *hk))
                st["movedToCandidates"][hk[0]] = st["movedToCandidates"].get(hk[0], 0) + 1
                st["movedList"].append(move_entry(batch, p, x, hk[0], rule, hk[1]))
                continue
            if ps:
                y["partyPostAmbiguous"], y["partyPostAmbiguousReason"] = True, ps[1]
                st["partyPostAmbiguous"] += 1
                e = move_entry(batch, p, x, None, "ambiguous", ps[1])
                e.pop("role_kind"); e.pop("rule")
                st["ambiguousList"].append(e)
            tk = t14_kind(y)
            if tk:
                y["t14Overlap"] = tk
                st["t14"][tk] = st["t14"].get(tk, 0) + 1
                st["t14List"].append({"person": pkey, "position": x.get("key"), "t14Overlap": tk,
                                      "title": (x.get("title") or {}).get("zh-Hant")})
            keep.append(y)
        p["positions"] = keep
        if cands:
            p["roleCandidates"] = cands
        else:
            p.pop("roleCandidates", None)
    d["alignedTo"] = "b0b0e0f"
    d["alignNote"] = ALIGN_NOTE
    return d, st


def main():
    report = {"alignedTo": "b0b0e0f", "partyRule": PARTY_REASON, "batches": {},
              "total": {"renamed": 0, "movedToCandidates": {}, "movedPartyPosts": 0, "partyPostAmbiguous": 0, "t14": {}},
              "moves": [], "ambiguous": []}
    for f in sorted(HERE.glob("batch*/research.json")):
        d, st = align_file(f)
        (f.parent / "research.aligned.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        report["batches"][f.parent.name] = st
        t = report["total"]
        t["renamed"] += st["renamed"]
        t["movedPartyPosts"] += st["movedPartyPosts"]
        t["partyPostAmbiguous"] += st["partyPostAmbiguous"]
        report["moves"] += st["movedList"]
        report["ambiguous"] += st["ambiguousList"]
        for k in ("movedToCandidates", "t14"):
            for kk, v in st[k].items():
                t[k][kk] = t[k].get(kk, 0) + v
    (HERE / "align-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for b, s in report["batches"].items():
        print(b, "改名", s["renamed"], "移候選", s["movedToCandidates"], "黨職", s["movedPartyPosts"], "ambiguous", s["partyPostAmbiguous"], "T14", s["t14"])
    print("總計", json.dumps(report["total"], ensure_ascii=False))


main()
