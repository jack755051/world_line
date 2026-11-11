"""把 B3 試跑 research.json 對齊 ARCHITECTURE.md b0b0e0f（人物／角色／經歷三層；§16.3.2/16.3.3/16.9 T11,T12,T14）。

用法：python3 -I align_b0b0e0f.py        （在 b3-trial 目錄下或任意處皆可）
輸入：batchNN/research.json（不修改）；輸出：batchNN/research.aligned.json、align-report.json。可重跑、冪等（輸入固定→輸出逐位元相同；不含時間戳）。
做的事（只搬移／改名／加標記，不新增或改寫任何引文、日期、出處）：
 1. positions[*].roleKind → positionKind（值照搬）。
 2. 元首／國家首腦／政府首腦／實際掌權者的經歷 → 移出 positions，放進該人的 roleCandidates
    （保留原欄位含 citations；加 candidateRoleKind、reason）。不建立角色資料。
 3. T14 重疊類別留在 positions，加 t14Overlap：cabinet｜general｜occupation_colonial。
 4. 頂層加 alignedTo、alignNote。
判斷規則見下方 HEAD_PATTERNS／PERSON_OVERRIDES／T14 規則，可直接審視。
"""
import json, re, unicodedata
from pathlib import Path

HERE = Path(__file__).resolve().parent
ALIGN_NOTE = ("依 ARCHITECTURE.md b0b0e0f（Tai 2026-11-11 10:03，T11／T12）對齊：經歷層欄位 roleKind 改名 positionKind（值照搬）；"
              "元首／首腦／實際掌權者移至 roleCandidates（僅為候選，未建角色、未寫庫）；T14 重疊類別以 t14Overlap 標記，仍留在 positions。"
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

# 個案覆寫：(人物 key, 職位 key) → (candidateRoleKind, reason)。標題無法判斷、需依內容的才放這裡；全部列入 ALIGN.md 供 Tai 複核。
PERSON_OVERRIDES = {
    ("su-stalin", "stalin-gensec"): ("de_facto_leader", "蘇共（布）中央總書記：史達林未任國家元首，但以此職實際掌握蘇聯，屬實際掌權者（疑義，待 Tai 決）"),
    ("cn-chiang-kai-shek", "chiang-tsung-tsai"): ("de_facto_leader", "國民黨總裁：蔣介石以此黨內最高職實際領導黨國，屬實際掌權者（疑義，待 Tai 決）"),
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


def align_file(path):
    d = json.load(open(path, encoding="utf-8"))
    st = {"renamed": 0, "movedToCandidates": {}, "t14": {}, "movedList": [], "t14List": []}
    for p in d.get("people", []):
        pkey = p.get("key")
        keep, cands = [], list(p.get("roleCandidates") or [])
        for x in p.get("positions", []):
            had_role = "roleKind" in x
            y = {("positionKind" if k == "roleKind" else k): v for k, v in x.items()}   # 保持欄位順序
            if had_role:
                st["renamed"] += 1
            hk = head_kind(x, pkey)
            if hk:
                c = {("roleKind" if k == "positionKind" else k): v for k, v in y.items()}  # 候選保留原欄位名
                c["candidateRoleKind"], c["reason"] = hk
                cands.append(c)
                st["movedToCandidates"][hk[0]] = st["movedToCandidates"].get(hk[0], 0) + 1
                st["movedList"].append({"person": pkey, "position": x.get("key"), "candidateRoleKind": hk[0],
                                        "title": (x.get("title") or {}).get("zh-Hant"), "reason": hk[1]})
                continue
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
    report = {"alignedTo": "b0b0e0f", "batches": {}, "total": {"renamed": 0, "movedToCandidates": {}, "t14": {}}}
    for f in sorted(HERE.glob("batch*/research.json")):
        d, st = align_file(f)
        (f.parent / "research.aligned.json").write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        report["batches"][f.parent.name] = st
        t = report["total"]
        t["renamed"] += st["renamed"]
        for k in ("movedToCandidates", "t14"):
            for kk, v in st[k].items():
                t[k][kk] = t[k].get(kk, 0) + v
    (HERE / "align-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    for b, s in report["batches"].items():
        print(b, "改名", s["renamed"], "移候選", s["movedToCandidates"], "T14", s["t14"])
    print("總計", json.dumps(report["total"], ensure_ascii=False))


main()
