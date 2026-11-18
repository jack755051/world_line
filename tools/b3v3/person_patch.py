#!/usr/bin/env python3
"""審查／補欄用：只讀或改單人檔的一小塊，不把整份 JSON 讀進對話。

路徑寫法：person.paragraphs[1].citations[0].quote、person.positions[0].period.end、person.gaps、sources.<key>.grade
（證據切片 claims[].path 給的就是這種路徑）。

    python3 -I tools/b3v3/person_patch.py get --file F --path person.positions[0]
    python3 -I tools/b3v3/person_patch.py set --file F --path person.paragraphs[0].citations[1].quote --json '"新引文"'
    python3 -I tools/b3v3/person_patch.py del --file F --path person.paragraphs[0].citations[2]
    python3 -I tools/b3v3/person_patch.py append --file F --path person.gaps --json '{"target": "...", ...}'
get 最多印 2000 字。
"""
import argparse
import json
import re
from pathlib import Path

TOKEN_RE = re.compile(r"([^.\[\]]+)|\[(\d+)\]")
MAX_CHARS = 2000


def parse_path(path):
    tokens = []
    for match in TOKEN_RE.finditer(path or ""):
        name, index = match.groups()
        tokens.append(int(index) if index is not None else name)
    if not tokens:
        raise SystemExit(f"路徑不合法：{path!r}")
    return tokens


def walk(doc, tokens):
    node = doc
    for token in tokens:
        try:
            node = node[token]
        except (KeyError, IndexError, TypeError):
            raise SystemExit(f"路徑不存在：{token!r}")
    return node


def apply(doc, op, path, value=None):
    tokens = parse_path(path)
    if op == "get":
        return walk(doc, tokens)
    parent = walk(doc, tokens[:-1])
    last = tokens[-1]
    if op == "set":
        if isinstance(parent, list) and isinstance(last, int) and last == len(parent):
            parent.append(value)
        else:
            try:
                parent[last] = value
            except (IndexError, TypeError):
                raise SystemExit(f"不能設定：{path}")
    elif op == "del":
        try:
            del parent[last]
        except (KeyError, IndexError, TypeError):
            raise SystemExit(f"不能刪除：{path}")
    elif op == "append":
        target = walk(doc, tokens)
        if not isinstance(target, list):
            raise SystemExit(f"{path} 不是陣列")
        target.append(value)
    else:
        raise SystemExit(f"未知操作 {op}")
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="單人檔局部讀寫")
    parser.add_argument("op", choices=("get", "set", "del", "append"))
    parser.add_argument("--file", required=True)
    parser.add_argument("--path", required=True)
    parser.add_argument("--json")
    args = parser.parse_args(argv)
    path = Path(args.file)
    if not path.name.endswith(".json") or path.name.endswith((".evidence.json", ".agent-done.json")):
        raise SystemExit("只能改單人檔 people/<bioId>.json")
    doc = json.loads(path.read_text(encoding="utf-8"))
    value = None
    if args.op in ("set", "append"):
        if args.json is None:
            raise SystemExit("set／append 需要 --json")
        value = json.loads(args.json)
    result = apply(doc, args.op, args.path, value)
    if args.op == "get":
        text = json.dumps(result, ensure_ascii=False, indent=1)
        print(text if len(text) <= MAX_CHARS else text[:MAX_CHARS] + "\n…[截斷，改取更小的路徑]")
        return 0
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"OK {args.op} {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
