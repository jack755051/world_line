#!/usr/bin/env python3
"""把一人一份的研究檔合併成批次 research.json（schema 與既有批次相同）。

單人檔 OUTDIR/people/<bioId>.json：
  person, sources, rawMap, researchedOn, policyVersion, alignedTo, alignNote, schemaNote

    python3 -I tools/b3v3/merge_people.py merge --outdir OUT --rawdir RAW \\
        --batch b3-full-v3-batch093 --order bio1,bio2,bio3
    python3 -I tools/b3v3/merge_people.py merge --outdir OUT --rawdir RAW \\
        --batch b3-full-v3-batch093 --order bio1 --replace
    python3 -I tools/b3v3/merge_people.py extract --research OUT/research.json \\
        --bio-id BIO --out OUT/people/BIO.json
"""
import argparse
import json
import sys
from pathlib import Path

DEFAULT_ALIGN = "直接寫 b0b0e0f 對齊格式；名單5442已有的元首／首腦任期不重建；regimeId 因不連庫一律 null＋organization。"
DEFAULT_SCHEMA = (
    "結構依 ARCHITECTURE §16.2（paragraphs）、§16.3（positions）、§16.4.1（citation 欄位）、"
    "§16.4.2（gaps）；sources 以 sourceKey 對應 source_id；來源規則依 docs/source-rules.md。"
)


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(data):
    return json.dumps(data, ensure_ascii=False, indent=1) + "\n"


def source_keys(obj, out=None):
    out = set() if out is None else out
    if isinstance(obj, dict):
        key = obj.get("sourceKey")
        if isinstance(key, str):
            out.add(key)
        for value in obj.values():
            source_keys(value, out)
    elif isinstance(obj, list):
        for value in obj:
            source_keys(value, out)
    return out


def read_person_file(path):
    data = load_json(path)
    person = data.get("person")
    if not isinstance(person, dict) or not person.get("bioId") or not person.get("key"):
        raise SystemExit(f"單人檔缺 person.bioId 或 person.key：{path}")
    sources = data.get("sources") or {}
    if not isinstance(sources, dict):
        raise SystemExit(f"單人檔 sources 必須是物件：{path}")
    raw_map = data.get("rawMap")
    if raw_map is None:
        raw_map = {}
    if not isinstance(raw_map, (dict, str)):
        raise SystemExit(f"單人檔 rawMap 必須是物件或檔名字串：{path}")
    return data


def coerce_raw_map(raw_map, sources, person, rawmap_path=None):
    """單人檔的 rawMap 必須是 sourceKey → 檔名。

    研究 agent 常把 research.json 頂層的檔名 \"rawmap.json\" 抄進單人檔。
    那是字串，這裡改成物件：能對上現有 rawmap 的用原檔名，其餘用 <sourceKey>.txt。
    """
    keys = set(sources or [])
    keys.update(source_keys(person))
    if isinstance(raw_map, dict):
        found = {k: v for k, v in raw_map.items() if isinstance(k, str) and isinstance(v, str)}
    else:
        found = {}
        if isinstance(raw_map, str) and raw_map.strip():
            print(f"rawMap 是字串 {raw_map!r}，已改成物件", file=sys.stderr)
        path = Path(rawmap_path) if rawmap_path else None
        if path and path.exists():
            try:
                loaded = load_json(path)
            except json.JSONDecodeError:
                loaded = None
            if isinstance(loaded, dict):
                found = {k: v for k, v in loaded.items() if k in keys and isinstance(v, str)}
    for key in sorted(keys):
        found.setdefault(key, f"{key}.txt")
    return found


def union_sources(base, incoming, conflicts):
    for key, value in incoming.items():
        if key in base and base[key] != value:
            conflicts.append(key)
        base[key] = value
    return base


def union_rawmap(path, incoming):
    path = Path(path)
    current = {}
    if path.exists():
        try:
            loaded = load_json(path)
            if isinstance(loaded, dict):
                current = loaded
        except json.JSONDecodeError:
            current = {}
    current.update({k: v for k, v in incoming.items() if isinstance(v, str)})
    path.write_text(dump(current), encoding="utf-8")
    return current


def merge(outdir, rawdir, batch, order, replace=False, overwrite=False):
    outdir = Path(outdir)
    people_dir = outdir / "people"
    research_path = outdir / "research.json"
    if replace and overwrite:
        raise SystemExit("merge 不能同時 --replace 與 --overwrite")
    if research_path.exists() and not replace and not overwrite:
        raise SystemExit(f"已有 {research_path}。重跑單人用 --replace；整批以單人檔覆寫用 --overwrite")
    if (replace or overwrite) and not research_path.exists():
        raise SystemExit(f"--replace／--overwrite 需要既有的 {research_path}")

    loaded = []
    for bio_id in order:
        path = people_dir / f"{bio_id}.json"
        if not path.exists():
            raise SystemExit(f"缺單人檔：{path}")
        data = read_person_file(path)
        if data["person"]["bioId"] != bio_id:
            raise SystemExit(f"{path} 的 bioId 是 {data['person']['bioId']}，與檔名不符")
        loaded.append(data)
    if not loaded:
        raise SystemExit("沒有要合併的人")

    base = load_json(research_path) if research_path.exists() else {}
    conflicts = []
    sources = dict(base.get("sources") or {})
    raw_incoming = {}
    rawmap_path = outdir / "rawmap.json"
    for data in loaded:
        union_sources(sources, data.get("sources") or {}, conflicts)
        raw_incoming.update(coerce_raw_map(
            data.get("rawMap"), data.get("sources") or {}, data["person"], rawmap_path,
        ))

    if replace:
        people = list(base.get("people") or [])
        index = {p.get("bioId"): i for i, p in enumerate(people)}
        for data in loaded:
            person = data["person"]
            if person["bioId"] in index:
                people[index[person["bioId"]]] = person
            else:
                people.append(person)
    else:
        people = [data["person"] for data in loaded]

    first = loaded[-1]
    doc = {
        "batch": base.get("batch") or batch,
        "researchedOn": base.get("researchedOn") or first.get("researchedOn"),
        "policyVersion": base.get("policyVersion") or first.get("policyVersion") or "bio-2026-11-v0",
        "alignedTo": base.get("alignedTo") or first.get("alignedTo") or "b0b0e0f",
        "alignNote": base.get("alignNote") or first.get("alignNote") or DEFAULT_ALIGN,
        "schemaNote": base.get("schemaNote") or first.get("schemaNote") or DEFAULT_SCHEMA,
        "rawDir": str(rawdir),
        "rawMap": "rawmap.json",
        "sources": sources,
        "people": people,
    }
    if not doc["batch"]:
        raise SystemExit("缺 --batch")
    if not doc["researchedOn"]:
        raise SystemExit("單人檔缺 researchedOn")
    outdir.mkdir(parents=True, exist_ok=True)
    research_path.write_text(dump(doc), encoding="utf-8")
    union_rawmap(outdir / "rawmap.json", raw_incoming)
    if conflicts:
        print("CONFLICT " + ",".join(conflicts), file=sys.stderr)
    print(f"merged {len(loaded)} people -> {research_path} ({len(people)} total)")
    return 0


def extract(research, bio_id, out_path):
    data = load_json(research)
    person = next((p for p in data.get("people") or [] if p.get("bioId") == bio_id), None)
    if person is None:
        raise SystemExit(f"research.json 沒有 bioId {bio_id}")
    keys = source_keys(person)
    sources = {k: v for k, v in (data.get("sources") or {}).items() if k in keys}
    raw_map = {}
    rawmap_path = Path(research).parent / (data.get("rawMap") or "rawmap.json")
    if rawmap_path.exists():
        loaded = load_json(rawmap_path)
        if isinstance(loaded, dict):
            raw_map = {k: v for k, v in loaded.items() if k in keys}
    for key in keys:
        raw_map.setdefault(key, f"{key}.txt")
    doc = {
        "person": person,
        "sources": sources,
        "rawMap": raw_map,
        "researchedOn": data.get("researchedOn"),
        "policyVersion": data.get("policyVersion"),
        "alignedTo": data.get("alignedTo"),
        "alignNote": data.get("alignNote"),
        "schemaNote": data.get("schemaNote"),
    }
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(dump(doc), encoding="utf-8")
    print(f"extracted {bio_id} -> {out_path}")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="合併或抽出 B3 v3 單人研究檔")
    sub = parser.add_subparsers(dest="cmd", required=True)
    merge_cmd = sub.add_parser("merge")
    merge_cmd.add_argument("--outdir", required=True)
    merge_cmd.add_argument("--rawdir", required=True)
    merge_cmd.add_argument("--batch", required=True)
    merge_cmd.add_argument("--order", required=True, help="逗號分隔的 bioId")
    merge_cmd.add_argument("--replace", action="store_true")
    merge_cmd.add_argument("--overwrite", action="store_true")
    extract_cmd = sub.add_parser("extract")
    extract_cmd.add_argument("--research", required=True)
    extract_cmd.add_argument("--bio-id", required=True)
    extract_cmd.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "extract":
        return extract(args.research, args.bio_id, args.out)
    order = [part.strip() for part in args.order.split(",") if part.strip()]
    return merge(args.outdir, args.rawdir, args.batch, order, args.replace, args.overwrite)


if __name__ == "__main__":
    raise SystemExit(main())
