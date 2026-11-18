#!/usr/bin/env python3
"""S-tier quality report + save one Montgomery or Rommel full bio as markdown."""
import json, collections, datetime, pathlib, unicodedata, re, sys
HERE = pathlib.Path(__file__).resolve().parent
SDIR = HERE / "S"
TZ = datetime.timezone(datetime.timedelta(hours=8))

def zh_len(s):
    return sum(1 for ch in unicodedata.normalize("NFC", s or "") if not ch.isspace())

def bodies(p):
    out = []
    for g in p.get("paragraphs") or []:
        b = g.get("body") or {}
        out.append(b.get("zh-Hant") or b.get("zh") or "")
    return out

def load_all():
    people = []
    files = []
    for d in sorted(SDIR.glob("batch*")):
        f = d / "research.json"
        if not f.exists():
            continue
        files.append(f)
        data = json.loads(f.read_text(encoding="utf-8"))
        for p in data.get("people") or []:
            people.append((d.name, p))
    return people, files

def md_person(p):
    lines = [f"# {p.get('nameZh') or p.get('name')}（{p.get('name') or ''}）\n"]
    if p.get("sourceInsufficient"):
        lines.append("> 已標「來源不足」。\n")
    for i, t in enumerate(bodies(p), 1):
        lines.append(f"## 第 {i} 段（{zh_len(t)} 字）\n")
        lines.append(t.strip() + "\n")
    return "\n".join(lines)

def main():
    from check_min import check
    people, files = load_all()
    rows = []
    sample = None
    for batch, p in people:
        r = check(p)
        r["batch"] = batch
        r["nameZh"] = p.get("nameZh") or p.get("name")
        r["nameEn"] = p.get("name") or ""
        rows.append((r, p))
        blob = (p.get("name") or "") + (p.get("nameZh") or "")
        if sample is None and re.search(r"Montgomery|蒙哥馬利|Rommel|隆美爾|隆美尔", blob, re.I):
            # prefer Montgomery, else first Rommel
            if re.search(r"Montgomery|蒙哥馬利", blob, re.I):
                sample = p
            elif sample is None:
                sample = p
    if sample is None and people:
        sample = people[0][1]
    paras = [r["paragraphs"] for r, _ in rows]
    chars = [r["zhChars"] for r, _ in rows]
    fail = [r for r, _ in rows if not r["meetsMinimum"]]
    insuff = [r for r, _ in rows if r["sourceInsufficient"]]
    def dist(xs):
        if not xs: return "無資料"
        ctr = collections.Counter(xs)
        return "、".join(f"{k}：{ctr[k]} 人" for k in sorted(ctr))
    now = datetime.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S+08:00")
    L = []
    A = L.append
    A("# 將領 S 級生平品質檢查\n")
    A(f"產出時間：{now}（Asia/Taipei）。共讀取 {len(files)} 批、{len(rows)} 人。\n")
    A("## 段數分布\n")
    A(dist(paras) + f"。平均 {sum(paras)/len(paras):.1f} 段。" if paras else "無。")
    A("\n## 字數分布（中文 NFC 去空白）\n")
    if chars:
        buckets = collections.Counter()
        for n in chars:
            if n < 300: b = "<300"
            elif n < 400: b = "300–399"
            elif n < 600: b = "400–599"
            elif n < 800: b = "600–799"
            else: b = "≥800"
            buckets[b] += 1
        A("、".join(f"{k} {buckets[k]} 人" for k in ["<300","300–399","400–599","600–799","≥800"] if buckets[k]))
        A(f"平均 {sum(chars)/len(chars):.0f} 字；最低 {min(chars)}、最高 {max(chars)}。")
    A("\n## 未達標名單\n")
    if not fail:
        A("無。")
    else:
        A("| 批次 | key | 姓名 | 段數 | 字數 | 指揮 | 戰役 | 來源不足 |\n|---|---|---|---|---|---|---|---|")
        for r in fail:
            A(f"| {r['batch']} | {r['key']} | {r['nameZh']} | {r['paragraphs']} | {r['zhChars']} | {r['hasCommand']} | {r['hasBattle']} | {r['sourceInsufficient']} |")
    A(f"\n已標「來源不足」：{len(insuff)} 人。達標 {sum(1 for r,_ in rows if r['meetsMinimum'])}／{len(rows)}。\n")
    A("## 樣本文（蒙哥馬利或隆美爾）\n")
    if sample:
        who = sample.get("nameZh") or sample.get("name")
        dest = HERE / "S" / "sample-montgomery-or-rommel.md"
        dest.write_text(md_person(sample), encoding="utf-8")
        A(f"已另存 `{dest.relative_to(HERE.parent.parent.parent.parent)}`（{who}）。")
    (SDIR / "QUALITY.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"quality report: {len(rows)} people, fail {len(fail)}, insuff {len(insuff)}")

if __name__ == "__main__":
    sys.path.insert(0, str(HERE))
    main()
