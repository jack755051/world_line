#!/usr/bin/env python3
"""B3 v3 省 token 工具的離線測試。不連外網。"""
import importlib.util
import argparse
import copy
import json
import re
import subprocess
import sys
import tempfile
import threading
import unittest
import time
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TOOLS = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fetch = load("fetch_source", TOOLS / "fetch_source.py")
merge = load("merge_people", TOOLS / "merge_people.py")
evidence = load("evidence_pack", TOOLS / "evidence_pack.py")
plan = load("plan_work", TOOLS / "plan_work.py")
patch = load("patch_prompts", TOOLS / "patch_prompts.py")
check_min = load("check_min", REPO / "data/seed/leaders/b3-trial/full/v3/check_min.py")
verify = load("b3_verify", REPO / "data/seed/leaders/b3-trial/verify.py")


class FetchTests(unittest.TestCase):
    def test_curl_command_has_no_insecure_flag(self):
        cmd = fetch.build_curl_command("https://example.test/a", "/tmp/out")
        self.assertNotIn("-k", cmd)
        self.assertNotIn("--insecure", cmd)
        self.assertIn("Mozilla/5.0", cmd)
        self.assertEqual(cmd[cmd.index("-A") + 1], "Mozilla/5.0")

    def test_html_keywords_are_capped(self):
        page = "<html><style>body{}</style><p>" + ("雜訊 " * 5000) + "Johannes Schober Bundeskanzler 1921</p></html>"
        text = fetch.html_to_text(page.encode(), "text/html")
        self.assertNotIn("body{}", text)
        snippets = fetch.matching_snippets(text, ["Schober", "1921"])
        self.assertTrue(snippets)
        report = fetch.format_report(["RESULT=fetched"], snippets, 500)
        self.assertLessEqual(len(report), 500)
        self.assertGreater(len(text), len(report))
        self.assertIn("Schober", report)
        self.assertNotIn("<style>", report)

    def test_pdf_text_and_flate(self):
        plain = b"%PDF-1.4\n1 0 obj<<>>stream\nBT (Schober Bundeskanzler 1921) Tj ET\nendstream\n"
        self.assertIn("Schober", fetch.pdf_to_text(plain))
        payload = b"BT (Mosquera 1938) Tj ET"
        compressed = zlib.compress(payload)
        flate = b"%PDF-1.4\n1 0 obj<</Filter/FlateDecode>>stream\n" + compressed + b"\nendstream\n"
        self.assertIn("Mosquera", fetch.pdf_to_text(flate))

    def test_cached_source_is_not_refetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "demo.txt").write_text("Johannes Schober war Bundeskanzler 1921. " + "Text. " * 100, encoding="utf-8")
            rawmap = raw / "rawmap.json"
            rawmap.write_text('{"demo": "demo.txt", "tiny": "tiny.txt"}\n', encoding="utf-8")
            out = fetch.cmd_fetch(raw, rawmap, "demo", "http://127.0.0.1:9/unused", ["Schober"], 2000)
            self.assertIn("RESULT=cached", out)
            self.assertIn("offset=", out)
            self.assertNotIn("RESULT=fetched", out)
            # 共用 rawDir 已有原文、但 rawmap 沒登記 → 回 cached 並補登記
            (raw / "shared.txt").write_text("Schober 1921. " * 60, encoding="utf-8")
            out = fetch.cmd_fetch(raw, rawmap, "shared", "http://127.0.0.1:9/unused", ["Schober"], 2000)
            self.assertIn("RESULT=cached", out)
            self.assertEqual(json.loads(rawmap.read_text(encoding="utf-8"))["shared"], "shared.txt")
            # 不到 500 字又不是擋頁的快取 → 會重抓（這裡連不上，所以是 error，不是 cached）
            (raw / "tiny.txt").write_text("Eduskunta", encoding="utf-8")
            out = fetch.cmd_fetch(raw, rawmap, "tiny", "http://127.0.0.1:9/unused", ["Schober"], 2000)
            self.assertNotIn("RESULT=cached", out)

    def test_lookup_offset(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp)
            (raw / "demo.txt").write_text("aaaa Johannes Schober Bundeskanzler.", encoding="utf-8")
            out = fetch.cmd_lookup(raw, None, "demo", ["Schober"], 2000)
            self.assertIn("RESULT=lookup", out)
            self.assertIn("offset=14", out)

    def test_rejects_bad_source_key(self):
        with self.assertRaises(SystemExit):
            fetch.check_source_key("../secret")

    def test_local_http_fetch_and_block(self):
        hits = {"n": 0}

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                hits["n"] += 1
                if self.path.startswith("/block"):
                    body = b"Just a moment Cloudflare"
                    self.send_response(403)
                else:
                    body = ("<p>" + ("noise " * 3000) + "Kung Hsiang-hsi Minister of Finance 1933</p>").encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        port = server.server_address[1]
        try:
            with tempfile.TemporaryDirectory() as tmp:
                raw = Path(tmp)
                rawmap = raw / "rawmap.json"
                out = fetch.cmd_fetch(
                    raw, rawmap, "kung", f"http://127.0.0.1:{port}/bio",
                    ["Kung", "1933"], 800,
                )
                self.assertIn("RESULT=fetched", out)
                self.assertLessEqual(len(out), 800)
                self.assertTrue((raw / "kung.txt").exists())
                self.assertIn("kung.txt", rawmap.read_text(encoding="utf-8"))
                again = fetch.cmd_fetch(
                    raw, rawmap, "kung", f"http://127.0.0.1:{port}/bio", ["Kung"], 800,
                )
                self.assertIn("RESULT=cached", again)
                self.assertEqual(hits["n"], 1)
                blocked = fetch.cmd_fetch(
                    raw, rawmap, "nope", f"http://127.0.0.1:{port}/block", ["x"], 800,
                )
                self.assertIn("RESULT=blocked_403", blocked)
                self.assertFalse((raw / "nope.txt").exists())
        finally:
            server.shutdown()
            server.server_close()


class MergeEvidenceTests(unittest.TestCase):
    def test_merge_extract_and_quote_agreement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            (raw / "src.txt").write_text("He was minister of war in 1907 and left in 1909.", encoding="utf-8")
            out = root / "batch"
            people = out / "people"
            people.mkdir(parents=True)
            person = {
                "person": {
                    "key": "p", "bioId": "bio-1", "name": "N", "nameZh": "某",
                    "paragraphs": [{
                        "ord": 1,
                        "body": {"zh-Hant": "他在一九〇七年任陸軍部長。", "en": "War minister."},
                        "period": {"start": "1907-01-01", "end": "1910-01-01"},
                        "periodStartPrecision": "year", "periodEndPrecision": "year",
                        "citations": [{
                            "sourceKey": "src", "quote": "minister  of war in 1907",
                            "grade": "B", "locator": "p1", "accessedOn": "2026-11-17",
                            "datePrecision": "year",
                        }],
                    }],
                    "positions": [], "roleCandidates": [], "gaps": [],
                },
                "sources": {"src": {"title": "t", "url": "https://example.test/a", "grade": "B", "authors": ["A"]}},
                "rawMap": {"src": "src.txt"},
                "researchedOn": "2026-11-17",
                "policyVersion": "bio-2026-11-v0",
                "alignedTo": "b0b0e0f",
                "alignNote": "n", "schemaNote": "n",
            }
            (people / "bio-1.json").write_text(json.dumps(person, ensure_ascii=False), encoding="utf-8")
            merge.merge(out, raw, "b3-full-v3-batcht", ["bio-1"])
            research = out / "research.json"
            report = out / "verify-report.json"
            proc = subprocess.run(
                [sys.executable, "-I", str(REPO / "data/seed/leaders/b3-trial/verify.py"),
                 str(research), "--report", str(report)],
                capture_output=True, text=True,
            )
            errors = json.loads(report.read_text(encoding="utf-8"))["errors"]
            self.assertFalse(any("未逐字" in error for error in errors), errors)
            self.assertIn("minister  of war", person["person"]["paragraphs"][0]["citations"][0]["quote"])
            pack = evidence.build(research)
            self.assertEqual(pack["failedClaimIndexes"], [])
            self.assertEqual(pack["claims"][0]["where"], "段1")
            self.assertEqual(len(pack["claims"][0]["citations"]), 1)
            self.assertTrue(pack["claims"][0]["citations"][0]["verify"]["ok"])
            # 壞引文要同時被 verify.py 與證據包標出
            data = json.loads(research.read_text(encoding="utf-8"))
            data["people"][0]["paragraphs"][0]["citations"][0]["quote"] = "not in the source at all"
            research.write_text(json.dumps(data), encoding="utf-8")
            subprocess.run(
                [sys.executable, "-I", str(REPO / "data/seed/leaders/b3-trial/verify.py"),
                 str(research), "--report", str(report)],
                capture_output=True, text=True,
            )
            errors = json.loads(report.read_text(encoding="utf-8"))["errors"]
            self.assertTrue(any("未逐字" in error for error in errors))
            pack = evidence.build(research)
            self.assertEqual(pack["failedClaimIndexes"], [0])
            self.assertFalse(pack["claims"][0]["citations"][0]["verify"]["ok"])
            self.assertEqual(pack["claims"][0]["citations"][0]["verify"]["reason"], "引文未逐字出現")
            self.assertIsNone(pack["claims"][0]["citations"][0]["verify"]["normOffset"])
            extracted = people / "again.json"
            merge.extract(research, "bio-1", extracted)
            self.assertEqual(json.loads(extracted.read_text(encoding="utf-8"))["person"]["bioId"], "bio-1")
            self.assertEqual(proc.returncode in (0, 1), True)

    def test_string_rawmap_is_coerced_to_object(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            (raw / "custom.txt").write_text("minister of war in 1907.", encoding="utf-8")
            out = root / "batch"
            people = out / "people"
            people.mkdir(parents=True)
            (out / "rawmap.json").write_text('{"src": "custom.txt"}\n', encoding="utf-8")
            person = {
                "person": {
                    "key": "p", "bioId": "bio-1", "name": "N", "nameZh": "某",
                    "paragraphs": [], "positions": [], "roleCandidates": [], "gaps": [],
                },
                "sources": {"src": {"title": "t", "url": "https://example.test/a", "grade": "B"}},
                "rawMap": "rawmap.json",
                "researchedOn": "2026-11-17",
            }
            (people / "bio-1.json").write_text(json.dumps(person), encoding="utf-8")
            merge.merge(out, raw, "b3-full-v3-batcht", ["bio-1"])
            rawmap = json.loads((out / "rawmap.json").read_text(encoding="utf-8"))
            self.assertEqual(rawmap["src"], "custom.txt")
            self.assertIsInstance(rawmap, dict)
            research = json.loads((out / "research.json").read_text(encoding="utf-8"))
            self.assertEqual(research["rawMap"], "rawmap.json")

    def test_check_min_alias_goes_to_fixed_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            research = root / "research.json"
            research.write_text(json.dumps({"people": [{
                "key": "p", "name": "N", "paragraphs": [], "positions": [], "roleCandidates": [], "gaps": [],
            }]}), encoding="utf-8")
            saved = sys.argv
            sys.argv = ["check_min.py", str(research), "--out", str(root / "check-min.json")]
            try:
                check_min.main()
            finally:
                sys.argv = saved
            self.assertTrue((root / "check_min-report.json").exists())
            self.assertFalse((root / "check-min.json").exists())
            report = json.loads((root / "check_min-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["failingKeys"], ["p"])

    def test_paragraph_with_many_cites_is_one_unit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            raw = root / "raw"
            raw.mkdir()
            (raw / "src.txt").write_text(
                "He was minister of war in 1907 and left in 1909.",
                encoding="utf-8",
            )
            (root / "rawmap.json").write_text(
                json.dumps({"src": "src.txt", "nofile": "nofile.txt"}),
                encoding="utf-8",
            )
            paragraph = "他在一九〇七年任陸軍部長，一九〇九年離職。"
            research = {
                "batch": "b3-full-v3-batcht",
                "rawDir": str(raw),
                "rawMap": "rawmap.json",
                "people": [
                    {
                        "key": "p", "bioId": "bio-1", "name": "某人",
                        "paragraphs": [
                            {
                                "ord": 1,
                                "body": {"zh-Hant": paragraph},
                                "citations": [
                                    {"sourceKey": "src", "quote": "minister of war in 1907", "grade": "B"},
                                    {"sourceKey": "src", "quote": "not in the source", "grade": "A"},
                                    {"sourceKey": "nofile", "quote": "minister of war", "grade": "B"},
                                    {"sourceKey": "unknown", "quote": "minister of war", "grade": "C"},
                                ],
                            },
                            {
                                "ord": 2,
                                "body": {"zh-Hant": "第二段只有一筆。"},
                                "citations": [
                                    {"sourceKey": "src", "quote": "left in 1909", "grade": "B"},
                                ],
                            },
                        ],
                        "positions": [{
                            "key": "job",
                            "title": {"zh-Hant": "陸軍部長"},
                            "organization": {"zh-Hant": "陸軍部"},
                            "period": {"start": "1907-01-01", "end": "1909-01-01"},
                            "citations": [
                                {"sourceKey": "src", "quote": "minister of war", "grade": "B"},
                                {"sourceKey": "src", "quote": "left in 1909", "grade": "B"},
                            ],
                        }],
                        "roleCandidates": [{
                            "key": "role-1",
                            "title": {"zh-Hant": "首相"},
                            "period": {"start": "1908-01-01", "end": "1909-01-01"},
                            "citations": [
                                {"sourceKey": "src", "quote": "in 1907", "grade": "A"},
                                {"sourceKey": "src", "quote": "in 1909", "grade": "A"},
                            ],
                        }],
                        "gaps": [
                            {
                                "target": "position:x",
                                "note": "待查證：缺迄日 A",
                                "candidateCitations": [
                                    {"sourceKey": "src", "quote": "minister of war", "grade": "B"},
                                ],
                            },
                            {
                                "target": "position:x",
                                "note": "待查證：缺迄日 B",
                                "candidateCitations": [
                                    {"sourceKey": "src", "quote": "left in 1909", "grade": "B"},
                                ],
                            },
                        ],
                    },
                    {
                        "key": "q", "bioId": "bio-2", "name": "別人",
                        "paragraphs": [{
                            "ord": 1,
                            "body": {"zh-Hant": "另一個人。"},
                            "citations": [{"sourceKey": "src", "quote": "left in 1909", "grade": "B"}],
                        }],
                        "positions": [], "roleCandidates": [], "gaps": [],
                    },
                ],
            }
            path = root / "research.json"
            path.write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")
            pack = evidence.build(path)
            units = [claim for claim in pack["claims"] if claim["personKey"] == "p"]
            paragraph_unit = units[0]
            self.assertEqual(paragraph_unit["where"], "段1")
            self.assertEqual(paragraph_unit["text"], paragraph)
            self.assertEqual(len(paragraph_unit["citations"]), 4)
            self.assertEqual(json.dumps(paragraph_unit, ensure_ascii=False).count(paragraph), 1)
            indexes = [cite["index"] for cite in paragraph_unit["citations"]]
            self.assertEqual(indexes, [0, 1, 2, 3])
            hit, miss, absent, unloaded = paragraph_unit["citations"]
            self.assertEqual(hit["quote"], "minister of war in 1907")
            self.assertEqual(hit["sourceKey"], "src")
            self.assertEqual(hit["grade"], "B")
            self.assertTrue(hit["verify"]["ok"])
            self.assertIsInstance(hit["verify"]["normOffset"], int)
            self.assertEqual(miss["grade"], "A")
            self.assertFalse(miss["verify"]["ok"])
            self.assertIsNone(miss["verify"]["normOffset"])
            self.assertEqual(miss["verify"]["reason"], "引文未逐字出現")
            self.assertEqual(absent["verify"], {"ok": False, "reason": "原文檔不存在"})
            self.assertEqual(unloaded["verify"], {"ok": False, "reason": "沒有載入此 sourceKey 的原文"})
            self.assertEqual(units[1]["where"], "段2")
            self.assertEqual(len(units[1]["citations"]), 1)
            position = next(claim for claim in units if claim["where"] == "職位 job")
            self.assertEqual(len(position["citations"]), 2)
            self.assertEqual(json.dumps(position, ensure_ascii=False).count("陸軍部長"), 1)
            self.assertTrue(all(cite["verify"]["ok"] for cite in position["citations"]))
            role = next(claim for claim in units if claim["where"] == "候選角色 role-1")
            self.assertEqual([cite["index"] for cite in role["citations"]], [0, 1])
            gaps = [claim for claim in units if claim["where"] == "gap position:x"]
            self.assertEqual([claim["text"] for claim in gaps], ["待查證：缺迄日 A", "待查證：缺迄日 B"])
            self.assertEqual(pack["claimCount"], len(pack["claims"]))
            self.assertEqual(pack["citationCount"], 4 + 1 + 2 + 2 + 1 + 1 + 1)
            self.assertEqual(pack["failedClaimIndexes"], [0])
            sliced = evidence.slice_person(pack, "p")
            self.assertEqual(sliced["personKey"], "p")
            self.assertEqual(sliced["claimCount"], len(units))
            self.assertEqual(sliced["citationCount"], 11)
            self.assertEqual(sliced["failedClaimIndexes"], [0])
            self.assertTrue(all(claim["personKey"] == "p" for claim in sliced["claims"]))
            other = evidence.slice_person(pack, "q")
            self.assertEqual(other["failedClaimIndexes"], [])
            self.assertEqual(other["citationCount"], 1)
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "evidence_pack.py"), str(path),
                 "--out", str(root / "evidence-pack.json"), "--person", "bio-2"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("claims=1", proc.stdout)
            self.assertIn("citations=1", proc.stdout)
            written = json.loads((root / "evidence-pack.json").read_text(encoding="utf-8"))
            self.assertEqual(written["claims"][0]["personKey"], "q")
            self.assertEqual(written["claimCount"], 1)
            self.assertIn("citationCount", written)
            self.assertIn("quoteCheck", written)

    def test_batch094_grouped_pack_is_smaller(self):
        path = REPO / "data/seed/leaders/b3-trial/full/v3/batch094/research.json"
        pack = evidence.build(path)
        multi = [claim for claim in pack["claims"] if len(claim.get("citations") or []) > 1]
        self.assertTrue(multi)
        sample = max(multi, key=lambda claim: len(claim["citations"]))
        blob = json.dumps(sample, ensure_ascii=False)
        self.assertEqual(blob.count(json.dumps(sample["text"], ensure_ascii=False)), 1)
        old = _flat_pack(pack)
        before = _dump_bytes(old)
        after = _dump_bytes(pack)
        self.assertLess(after, before)
        by_person = {}
        for claim in pack["claims"]:
            by_person.setdefault(claim["personKey"], []).append(claim)
        person_before = person_after = 0
        biggest = None
        for key, claims in by_person.items():
            new_n = _dump_bytes(claims)
            old_claims = []
            for unit in claims:
                for cite in unit["citations"]:
                    old_claims.append({
                        "personKey": unit["personKey"],
                        "personName": unit["personName"],
                        "where": f"{unit['where']} c{cite['index']}",
                        "text": unit["text"],
                        "quote": cite["quote"],
                        "sourceKey": cite["sourceKey"],
                        "grade": cite["grade"],
                        "verify": cite["verify"],
                    })
            old_n = _dump_bytes(old_claims)
            person_before += old_n
            person_after += new_n
            saved = old_n - new_n
            if biggest is None or saved > biggest[0]:
                biggest = (saved, key, old_n, new_n, len(claims), sum(len(c["citations"]) for c in claims))
        self.assertLess(person_after, person_before)
        print(
            f"SIZE batch094 evidence-pack.json before={before} after={after} "
            f"saved={before - after} claims={pack['claimCount']} citations={pack['citationCount']}"
        )
        print(
            f"SIZE batch094 per-person claims before={person_before} after={person_after} "
            f"saved={person_before - person_after} largest={biggest[1]} "
            f"before={biggest[2]} after={biggest[3]} units={biggest[4]} citations={biggest[5]}"
        )


def _dump_bytes(data):
    return len((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


def _flat_pack(pack):
    """舊版證據包：每筆引文重複整段 text。用來跟分組後的位元組比較。"""
    claims = []
    failed = []
    for unit in pack["claims"]:
        for cite in unit["citations"]:
            if not (cite.get("verify") or {}).get("ok"):
                failed.append(len(claims))
            claims.append({
                "personKey": unit["personKey"],
                "personName": unit["personName"],
                "where": f"{unit['where']} c{cite['index']}",
                "text": unit["text"],
                "quote": cite["quote"],
                "sourceKey": cite["sourceKey"],
                "grade": cite["grade"],
                "verify": cite["verify"],
            })
    return {
        "batch": pack["batch"],
        "generatedBy": pack["generatedBy"],
        "quoteCheck": pack["quoteCheck"],
        "verifyReport": pack["verifyReport"],
        "claimCount": len(claims),
        "failedClaimIndexes": failed,
        "claims": claims,
    }


def _cited_paragraphs(count=3, chars=100):
    return [
        {
            "ord": index + 1,
            "body": {"zh-Hant": "字" * chars},
            "citations": [{"sourceKey": "src", "quote": "quoted"}],
        }
        for index in range(count)
    ]


def _term(key, end):
    return {
        "key": key,
        "period": {"start": "1908-01-01", "end": end},
        "citations": [{"sourceKey": "src", "quote": "quoted"}],
    }


def _fixture_person(key, name, bio_id, positions, gaps=None, paragraphs=None):
    return {
        "key": key,
        "name": name,
        "nameZh": name,
        "bioId": bio_id,
        "paragraphs": _cited_paragraphs() if paragraphs is None else paragraphs,
        "positions": positions,
        "roleCandidates": [],
        "gaps": gaps or [],
    }


def _write_prompt(directory, nn, people):
    lines = ["## 本批"]
    for person in people:
        lines.append(f"- {person['nameZh']}｜{person['name']}｜{person['bioId']}｜1908")
    lines.extend(["", "結束"])
    (directory / f"research-{nn}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_batch(root, nn, people, review=False, errors=None):
    out = root / f"batch{nn}"
    out.mkdir(parents=True)
    (out / "research.json").write_text(json.dumps({"people": people}, ensure_ascii=False), encoding="utf-8")
    (out / "verify-report.json").write_text(
        json.dumps({"errors": errors or []}, ensure_ascii=False), encoding="utf-8",
    )
    if review:
        (out / "review.json").write_text("{}\n", encoding="utf-8")


def build_end_date_fixture(tmp):
    """三批合成資料：已標註缺迄日不重跑，未標註的仍重跑，兩者混在同一人時只重跑未標註的。"""
    root = Path(tmp)
    prompts = root / "prompts"
    prompts.mkdir()
    out = root / "out"
    flagged = _fixture_person(
        "flagged", "Flagged End", "bio-flagged",
        [_term("job", None)],
        gaps=[{"target": "position:job", "note": "待查證：缺迄日；已查 A/B"}],
    )
    open_end = _fixture_person(
        "open", "Open End", "bio-open",
        [_term("job", None)],
    )
    mixed = _fixture_person(
        "mixed", "Mixed Ends", "bio-mixed",
        [_term("open", None), _term("shut", None)],
        gaps=[{"target": "position:shut", "note": "待查證：缺迄日；已查"}],
    )
    short = _fixture_person(
        "short", "Short Flagged", "bio-short",
        [_term("job", None)],
        gaps=[
            {"target": "position:job", "note": "待查證：缺迄日"},
            {"target": "paragraph:length", "note": "篇幅不足：來源只有這些"},
        ],
        paragraphs=[{"ord": 1, "body": {"zh-Hant": "短"}, "citations": [{"sourceKey": "src", "quote": "quoted"}]}],
    )
    done_open = _fixture_person("would-retry", "Would Retry", "bio-would", [_term("job", None)])
    done_flagged = _fixture_person(
        "already-done", "Already Done", "bio-done",
        [_term("job", None)],
        gaps=[{"target": "position:job", "note": "待查證：缺迄日"}],
    )
    ok = _fixture_person("ok-person", "Ok Person", "bio-ok", [_term("job", "1910-01-01")])
    only_flagged = _fixture_person(
        "only-flagged", "Only Flagged", "bio-only",
        [_term("job", None)],
        gaps=[{"target": "position:job", "note": "待查證：缺迄日"}],
    )
    batch094 = [flagged, open_end, mixed, short]
    batch095 = [ok]
    batch096 = [done_open, done_flagged]
    _write_batch(out, "094", batch094)
    _write_batch(out, "095", batch095, review=True, errors=["ok-person quote failed"])
    _write_batch(out, "096", batch096)
    _write_batch(out, "097", [only_flagged])
    for nn, people in (("094", batch094), ("095", batch095), ("096", batch096)):
        _write_prompt(prompts, nn, people)
    remaining = {
        "reviewed": ["093"],
        "needs_research": [],
        "needs_retry_and_review": {"094": ["Open End", "Mixed Ends"]},
        "needs_review_only": ["096"],
        "recheck_review": ["095"],
        "retryDone": ["096"],
        "shortfall_review": {"094": ["Short Flagged"]},
    }
    resume = root / "remaining.json"
    resume.write_text(json.dumps(remaining, ensure_ascii=False), encoding="utf-8")
    return root


class PlanTests(unittest.TestCase):
    def test_resume_plan_schedules_saved_batches(self):
        proc = subprocess.run(
            [sys.executable, "-I", str(TOOLS / "plan_work.py"),
             "--repo", str(REPO),
             "--prompt-dir", ".dev/b3v3/prompts",
             "--out-root", "data/seed/leaders/b3-trial/full/v3",
             "--raw-root", "/tmp/b3-raw",
             "--resume", ".dev/b3v3/partial/chunk4-remaining.json"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["batchCount"], 25)
        self.assertEqual(data["skipped"], ["093", "097", "098", "100", "105"])
        by_nn = {item["nn"]: item for item in data["batches"]}
        for skipped in ("093", "097", "098", "100", "105"):
            self.assertNotIn(skipped, by_nn)
        self.assertFalse(by_nn["122"]["research"])
        self.assertEqual(by_nn["122"]["retry"]["mode"], "none")
        self.assertTrue(by_nn["122"]["review"])
        self.assertEqual(by_nn["122"]["retry"]["people"], [])
        self.assertEqual(by_nn["095"]["retry"]["mode"], "none")
        # 2026-11-20 tiers-run111 併回後，這三人改判「A/B不足，已用C補」，不再列為篇幅不足
        self.assertEqual([person["name"] for person in by_nn["095"]["shortfall"]], [])
        self.assertTrue(by_nn["096"]["recheck"])
        self.assertFalse(by_nn["096"]["research"])
        trial = subprocess.run(
            [sys.executable, "-I", str(TOOLS / "plan_work.py"),
             "--repo", str(REPO),
             "--prompt-dir", ".dev/b3v3/prompts",
             "--out-root", "data/seed/leaders/b3-trial/full/v3",
             "--raw-root", "/tmp/b3-raw",
             "--resume", ".dev/b3v3/partial/chunk4-remaining.json",
             "--chunk", "094,122,096"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(trial.returncode, 0, trial.stderr)
        trial_nns = [item["nn"] for item in json.loads(trial.stdout)["batches"]]
        self.assertEqual(trial_nns, ["094", "122", "096"])

    def test_flagged_end_dates_skip_retry_round(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_end_date_fixture(tmp)
            fresh = plan.recompute_chunk(root / "out", start=94, end=97, retry_done=("096",), recheck=("095",))
            self.assertEqual(fresh["needs_retry_and_review"], {"094": ["Open End", "Mixed Ends"]})
            self.assertEqual(fresh["shortfall_review"], {"094": ["Short Flagged"]})
            self.assertEqual(fresh["needs_review_only"], ["096", "097"])
            self.assertTrue(fresh["missingFields"]["097"]["only-flagged"][0]["alreadyFlagged"])
            self.assertNotIn("Flagged End", fresh["needs_retry_and_review"]["094"])
            self.assertNotIn("Already Done", json.dumps(fresh["needs_retry_and_review"]))
            flagged_fields = fresh["missingFields"]["094"]["flagged"]
            self.assertEqual(flagged_fields[0]["field"], "position:job.end")
            self.assertFalse(flagged_fields[0]["fixable"])
            self.assertTrue(flagged_fields[0]["alreadyFlagged"])
            mixed_fields = {field["field"]: field for field in fresh["missingFields"]["094"]["mixed"]}
            self.assertTrue(mixed_fields["position:open.end"]["fixable"])
            self.assertFalse(mixed_fields["position:shut.end"]["fixable"])
            self.assertTrue(mixed_fields["position:shut.end"]["alreadyFlagged"])
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "plan_work.py"),
                 "--repo", str(root),
                 "--prompt-dir", "prompts",
                 "--out-root", "out",
                 "--raw-root", "raw",
                 "--resume", "remaining.json"],
                capture_output=True, text=True, cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            by_nn = {item["nn"]: item for item in json.loads(proc.stdout)["batches"]}
            self.assertEqual([item["nn"] for item in json.loads(proc.stdout)["batches"]], ["094", "096", "095"])
            retry_people = by_nn["094"]["retry"]["people"]
            self.assertEqual([person["name"] for person in retry_people], ["Open End", "Mixed Ends"])
            mixed = next(person for person in retry_people if person["name"] == "Mixed Ends")
            self.assertEqual([field["field"] for field in mixed["missingFields"]], ["position:open.end"])
            self.assertTrue(mixed["missingFields"][0]["fixable"])
            details = {person["name"]: person for person in by_nn["094"]["details"]}
            self.assertEqual(details["Flagged End"]["action"], "review")
            self.assertEqual(details["Flagged End"]["fixableFields"], [])
            self.assertFalse(details["Flagged End"]["shortfallFlag"])
            self.assertTrue(details["Flagged End"]["missingFields"][0]["alreadyFlagged"])
            self.assertEqual(
                [person["name"] for person in by_nn["094"]["shortfall"]],
                ["Short Flagged"],
            )
            self.assertEqual(by_nn["096"]["retry"]["mode"], "none")
            self.assertEqual(by_nn["096"]["retry"]["people"], [])
            self.assertEqual(
                [person["name"] for person in by_nn["096"]["retrySkipped"]],
                ["Would Retry"],
            )
            self.assertTrue(by_nn["095"]["recheck"])
            self.assertFalse(by_nn["095"]["research"])

    def test_prompt_patch_is_idempotent_on_disk(self):
        sample = (REPO / ".dev/b3v3/prompts/research-093.md").read_text(encoding="utf-8")
        self.assertIn("tools/b3v3/fetch_source.py", sample)
        self.assertNotIn("curl -sSL", sample)
        again, notes = patch.patch_text("research-093.md", sample)
        self.assertEqual(again, sample)
        self.assertEqual(notes, [])
        review = (REPO / ".dev/b3v3/prompts/review-096.md").read_text(encoding="utf-8")
        self.assertIn("evidence-pack.json", review)
        self.assertIn("每個 claim 單位寫一次 text", review)
        self.assertIn("該 claim 單位只寫一次的 text", review)
        self.assertNotIn("每筆 claim 的段落文字", review)
        self.assertNotIn("每人至少抽 1 個來源重抓", review)
        self.assertNotIn("raw/*.txt", review)
        again, notes = patch.patch_text("review-096.md", review)
        self.assertEqual(again, review)
        self.assertEqual(notes, [])


class CheckMinVerdictTests(unittest.TestCase):
    def _person(self, **overrides):
        person = {
            "key": "p", "name": "N",
            "paragraphs": [{"body": {"zh-Hant": "字" * 100}} for _ in range(3)],
            "positions": [{
                "key": "job",
                "period": {"start": "1908-01-01", "end": "1910-01-01"},
            }],
            "roleCandidates": [],
            "gaps": [],
        }
        person.update(overrides)
        return person

    def test_flagged_end_is_explicit_and_not_labeled_weida(self):
        person = self._person(
            positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}}],
            gaps=[{"target": "position:job", "note": "待查證：缺迄日；審查拿掉推論迄日"}],
        )
        row = check_min.check(person)
        self.assertFalse(row["meetsMinimum"])
        self.assertEqual(row["verdict"], "已標註缺迄日")
        self.assertEqual(row["openTerms"][0]["missing"], "end")
        self.assertTrue(row["openTerms"][0]["flagged"])

    def test_missing_end_without_gap_is_weida(self):
        person = self._person(positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}}])
        row = check_min.check(person)
        self.assertEqual(row["verdict"], "未達")
        info = plan.classify_person(person, row)
        self.assertEqual(info["action"], "retry")
        self.assertEqual(info["fixableFields"][0]["field"], "position:job.end")
        self.assertTrue(info["fixableFields"][0]["fixable"])
        self.assertNotIn("alreadyFlagged", info["fixableFields"][0])

    def test_flagged_missing_end_does_not_retry(self):
        cited = [{"quote": "q", "sourceKey": "s"}]
        paragraphs = [
            {"ord": index + 1, "body": {"zh-Hant": "字" * 100}, "citations": cited}
            for index in range(3)
        ]
        person = self._person(
            paragraphs=paragraphs,
            positions=[],
            roleCandidates=[{
                "key": "party",
                "period": {"start": "1906-01-01", "end": None},
                "citations": cited,
            }],
            gaps=[{"target": "role:party", "note": "待查證：缺迄日；已查 A/B 來源"}],
        )
        info = plan.classify_person(person, check_min.check(person))
        self.assertEqual(info["action"], "review")
        self.assertEqual(info["fixableFields"], [])
        self.assertFalse(info["shortfallFlag"])
        field = info["missingFields"][0]
        self.assertEqual(field["field"], "role:party.end")
        self.assertEqual(field["kind"], "missing-end")
        self.assertFalse(field["fixable"])
        self.assertTrue(field["alreadyFlagged"])
        self.assertIn("待查證：缺迄日", field["detail"])

        buried = self._person(
            paragraphs=paragraphs,
            positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}, "citations": cited}],
            gaps=[{"target": "position:job", "note": "加強重跑後仍無迄日，維持待查證：缺迄日"}],
        )
        buried_info = plan.classify_person(buried, check_min.check(buried))
        self.assertEqual(buried_info["action"], "review")
        self.assertTrue(buried_info["missingFields"][0]["alreadyFlagged"])
        self.assertFalse(buried_info["missingFields"][0]["fixable"])

        other_target = self._person(
            paragraphs=paragraphs,
            positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}, "citations": cited}],
            gaps=[{"target": "position:other", "note": "待查證：缺迄日"}],
        )
        other_info = plan.classify_person(other_target, check_min.check(other_target))
        self.assertEqual(other_info["action"], "retry")
        self.assertEqual(other_info["fixableFields"][0]["field"], "position:job.end")

    def test_unflagged_missing_end_still_retries(self):
        cited = [{"quote": "q", "sourceKey": "s"}]
        paragraphs = [
            {"ord": index + 1, "body": {"zh-Hant": "字" * 100}, "citations": cited}
            for index in range(3)
        ]
        person = self._person(
            paragraphs=paragraphs,
            positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}, "citations": cited}],
        )
        info = plan.classify_person(person, check_min.check(person))
        self.assertEqual(info["action"], "retry")
        self.assertEqual(
            [(field["field"], field["fixable"]) for field in info["fixableFields"]],
            [("position:job.end", True)],
        )

        start = self._person(
            paragraphs=paragraphs,
            positions=[{
                "key": "job",
                "period": {"start": None, "end": "1910-01-01"},
                "citations": [{"quote": "  ", "sourceKey": "s"}],
            }],
            gaps=[{"target": "position:job", "note": "待查證：缺起日；已查"}],
        )
        start_info = plan.classify_person(start, check_min.check(start))
        self.assertEqual(start_info["action"], "retry")
        by_kind = {field["kind"]: field for field in start_info["fixableFields"]}
        self.assertTrue(by_kind["missing-start"]["fixable"])
        self.assertEqual(by_kind["missing-start"]["field"], "position:job.start")
        self.assertTrue(by_kind["empty-quote"]["fixable"])
        self.assertNotIn("missing-end", by_kind)

    def test_mixed_flagged_and_unflagged_ends(self):
        cited = [{"quote": "q", "sourceKey": "s"}]
        paragraphs = [
            {"ord": index + 1, "body": {"zh-Hant": "字" * 100}, "citations": cited}
            for index in range(3)
        ]
        person = self._person(
            paragraphs=paragraphs,
            positions=[
                {"key": "open", "period": {"start": "1908-01-01", "end": None}, "citations": cited},
                {"key": "shut", "period": {"start": "1910-01-01", "end": None}, "citations": cited},
            ],
            gaps=[{"target": "position:shut", "note": "待查證：缺迄日；已查"}],
        )
        info = plan.classify_person(person, check_min.check(person))
        self.assertEqual(info["action"], "retry")
        self.assertEqual(
            [field["field"] for field in info["fixableFields"]],
            ["position:open.end"],
        )
        flagged = [field for field in info["missingFields"] if field["field"] == "position:shut.end"]
        self.assertEqual(len(flagged), 1)
        self.assertFalse(flagged[0]["fixable"])
        self.assertTrue(flagged[0]["alreadyFlagged"])

        both = self._person(
            paragraphs=[{"body": {"zh-Hant": "短"}, "citations": cited}],
            positions=[{"key": "job", "period": {"start": "1908-01-01", "end": None}, "citations": cited}],
            gaps=[
                {"target": "position:job", "note": "待查證：缺迄日"},
                {"target": "paragraph:length", "note": "篇幅不足：來源只有這些"},
            ],
        )
        both_info = plan.classify_person(both, check_min.check(both))
        self.assertEqual(both_info["action"], "shortfall")
        self.assertTrue(both_info["shortfallFlag"])
        self.assertEqual(both_info["fixableFields"], [])
        self.assertTrue(any(field["kind"] == "paragraphs" for field in both_info["missingFields"]))
        end = next(field for field in both_info["missingFields"] if field["kind"] == "missing-end")
        self.assertFalse(end["fixable"])
        self.assertTrue(end["alreadyFlagged"])

    def test_documented_shortfall_is_not_retried(self):
        person = self._person(
            paragraphs=[{"body": {"zh-Hant": "短"}}],
            gaps=[{"target": "paragraph:length", "note": "篇幅不足：來源只有這些"}],
        )
        row = check_min.check(person)
        self.assertEqual(row["verdict"], "篇幅不足")
        self.assertTrue(row["documentedShortfall"])
        self.assertEqual(plan.classify_person(person, row)["action"], "shortfall")


class DriverTests(unittest.TestCase):
    def test_workflow_does_not_touch_the_filesystem(self):
        text = (REPO / ".dev/b3v3/workflow/b3-v3-chunk1-and-major-retry.js").read_text(encoding="utf-8")
        self.assertNotIn("node:fs", text)
        self.assertNotIn("node:child_process", text)
        self.assertNotIn("execFile", text)
        self.assertNotIn("readFileSync", text)
        self.assertIn("show-prompt", text)

    def test_retry_prompt_lists_only_missing_fields(self):
        agent_specs = load("agent_specs", TOOLS / "agent_specs.py")
        batch = {"nn": "094", "outDir": "/tmp/out", "rawDir": "/tmp/raw", "retryPrompt": "/tmp/retry.md"}
        person = {
            "name": "Milan Hodža", "nameZh": "霍扎", "bioId": "bio-hodza",
            "line": "霍扎｜Milan Hodža｜bio-hodza｜1920",
            "missingFields": [{
                "field": "role:hodza-sns-1906.end", "kind": "missing-end", "fixable": True, "detail": "缺迄日",
            }],
        }
        text = agent_specs.retry_prompt(batch, person, "/repo")
        self.assertIn("role:hodza-sns-1906.end", text)
        self.assertIn("不要追求 15 次查詢", text)
        self.assertNotIn("至少 5 種來源類型", text)
        self.assertIn("不可以寫成字串", text)
        hint = agent_specs.keyword_hint({
            "name": "Alexandru Averescu", "nameZh": "阿維雷斯庫",
            "bioId": "01a1b512-8b4a-70ef-8767-04121fb4dcc2",
            "line": "阿維雷斯庫｜Alexandru Averescu｜01a1b512-8b4a-70ef-8767-04121fb4dcc2｜1920-03-13",
        })
        self.assertNotIn("8767", hint)
        self.assertIn("1920", hint)
        review = agent_specs.review_prompt(
            {"nn": "095", "outDir": "/tmp/out", "rawDir": "/tmp/raw", "reviewPrompt": "/tmp/review.md", "recheck": False},
            {"name": "某人", "nameZh": "某人", "bioId": "bio", "line": "某人", "shortfallFlag": True},
            "/repo",
        )
        self.assertIn("篇幅不足", review)
        self.assertIn("佩納", review)
        self.assertIn(".evidence.json", review)
        self.assertIn("citations", review)
        self.assertIn("checkMin", review)
        self.assertIn("text 只寫一次", review)
        self.assertNotIn("/tmp/review.md", review)
        self.assertIn("person_patch.py", review)
        self.assertIn("review-done", review)

    def test_dry_run_skips_flagged_ends_and_keeps_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = build_end_date_fixture(tmp)
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "dry-run",
                 "--repo", str(root),
                 "--prompt-dir", "prompts",
                 "--out-root", "out",
                 "--raw-root", "raw",
                 "--resume", "remaining.json",
                 "--concurrency", "3", "--json"],
                capture_output=True, text=True, cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual(data["researchAgents"], 0)
            self.assertEqual(
                [(agent["batch"], agent["name"], agent["fields"]) for agent in data["retryPeople"]],
                [
                    ("094", "Open End", ["position:job.end"]),
                    ("094", "Mixed Ends", ["position:open.end"]),
                ],
            )
            self.assertEqual(data["retryAgents"], 2)
            self.assertEqual(data["shortfallPeople"], 1)
            self.assertEqual(data["reviewAgents"], 7)
            review_models = {
                (agent["batch"], agent["name"]): agent["model"]
                for wave in data["waves"] if wave["phase"] == "review"
                for agent in wave["agents"]
            }
            # 審查一律先 Sonnet（含 verify 有錯、check_min 未達的人）；Opus 只在 Sonnet 審查後仍有錯時出現。
            self.assertEqual(set(review_models.values()), {"sonnet"})
            self.assertEqual(data["escalateAgents"], 0)
            self.assertNotIn("Flagged End", [agent["name"] for agent in data["retryPeople"]])
            self.assertNotIn("prompt", json.dumps(data["waves"][0]["agents"][0]))
            # 095 的 Ok Person 審查做完（agent-done stage=review），verify 仍有錯 → 只有他升 Opus。
            people_dir = root / "out" / "batch095" / "people"
            people_dir.mkdir(parents=True)
            (people_dir / "bio-ok.agent-done.json").write_text(
                json.dumps({"stage": "review", "bioId": "bio-ok", "ok": True}), encoding="utf-8")
            again = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "dry-run",
                 "--repo", str(root), "--prompt-dir", "prompts", "--out-root", "out", "--raw-root", "raw",
                 "--resume", "remaining.json", "--concurrency", "3", "--json"],
                capture_output=True, text=True, cwd=root,
            )
            self.assertEqual(again.returncode, 0, again.stderr)
            later = json.loads(again.stdout)
            self.assertEqual(later["escalateAgents"], 1)
            escalated = [agent for wave in later["waves"] if wave["phase"] == "escalate" for agent in wave["agents"]]
            self.assertEqual([(a["name"], a["model"]) for a in escalated], [("Ok Person", "opus")])
            self.assertNotIn("Ok Person", [a["name"] for w in later["waves"] if w["phase"] == "review" for a in w["agents"]])

    def test_show_prompt_prints_only_that_agent(self):
        with tempfile.TemporaryDirectory() as tmp:
            spec = Path(tmp) / "spec.json"
            spec.write_text(json.dumps({"agents": [
                {"id": "retry:094:bio", "prompt": "只補 role:hodza-sns-1906.end\n"},
                {"id": "other", "prompt": "不要印這段\n"},
            ]}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "show-prompt",
                 "--spec", str(spec), "--id", "retry:094:bio"],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("role:hodza-sns-1906.end", proc.stdout)
            self.assertNotIn("不要印這段", proc.stdout)

    def test_evidence_file_keeps_check_min_and_marks_missing_raw(self):
        run_chunk = load("run_chunk", TOOLS / "run_chunk.py")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = root / "batch"
            out.mkdir()
            raw = root / "raw"
            raw.mkdir()
            (raw / "src.txt").write_text("minister of war in 1907 and left in 1909.", encoding="utf-8")
            empty = root / "empty"
            empty.mkdir()
            paragraph = "他在一九〇七年任陸軍部長，一九〇九年離職，並留任到次年。"
            research = {
                "batch": "b3-full-v3-batcht",
                "rawDir": str(raw),
                "rawMap": "rawmap.json",
                "people": [{
                    "key": "p", "bioId": "bio-1", "name": "某人",
                    "paragraphs": [{
                        "ord": 1,
                        "body": {"zh-Hant": paragraph},
                        "citations": [
                            {"sourceKey": "src", "quote": "minister of war in 1907", "grade": "B"},
                            {"sourceKey": "src", "quote": "left in 1909", "grade": "A"},
                        ],
                    }],
                    "positions": [], "roleCandidates": [], "gaps": [],
                }],
            }
            (out / "research.json").write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")
            (out / "rawmap.json").write_text('{"src": "src.txt"}\n', encoding="utf-8")
            (out / "verify-report.json").write_text(
                json.dumps({"ok": False, "errors": ["p 引文未逐字出現"]}),
                encoding="utf-8",
            )
            agent = {
                "kind": "review", "outDir": str(out), "rawDir": str(raw),
                "bioId": "bio-1", "batch": "t",
            }
            run_chunk.prepare_files([agent])
            evidence_path = out / "people" / "bio-1.evidence.json"
            doc = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(doc["bioId"], "bio-1")
            self.assertTrue(doc["rawLoaded"])
            self.assertEqual(set(doc["checkMin"]), {
                "verdict", "paragraphs", "zhChars", "meetsMinimum", "documentedShortfall", "openTerms",
            })
            self.assertEqual(doc["verifyErrors"], ["p 引文未逐字出現"])
            self.assertEqual(len(doc["claims"]), 1)
            self.assertEqual(doc["claims"][0]["where"], "段1")
            self.assertEqual(doc["claims"][0]["text"], paragraph)
            self.assertEqual(len(doc["claims"][0]["citations"]), 2)
            self.assertEqual(evidence_path.read_text(encoding="utf-8").count(paragraph), 1)
            self.assertTrue(all(cite["verify"]["ok"] for cite in doc["claims"][0]["citations"]))
            self.assertEqual(
                [cite["quote"] for cite in doc["claims"][0]["citations"]],
                ["minister of war in 1907", "left in 1909"],
            )
            agent["rawDir"] = str(empty)
            run_chunk.prepare_files([agent])
            marked = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertFalse(marked["rawLoaded"])
            self.assertEqual(marked["checkMin"]["verdict"], doc["checkMin"]["verdict"])
            self.assertEqual(marked["verifyErrors"], doc["verifyErrors"])
            self.assertEqual(evidence_path.read_text(encoding="utf-8").count(paragraph), 1)
            for cite in marked["claims"][0]["citations"]:
                self.assertEqual(cite["verify"], {"ok": None, "reason": "這台機器沒有原文快取，不要依這格改引文"})
                self.assertIn("quote", cite)
                self.assertIn("grade", cite)




prefilter = load("prefilter", TOOLS / "prefilter.py")
draft_mod = load("person_draft", TOOLS / "person_draft.py")
patch_mod = load("person_patch", TOOLS / "person_patch.py")
specs_mod = load("agent_specs", TOOLS / "agent_specs.py")
loop_mod = load("run_loop", TOOLS / "run_loop.py")
cost_mod = load("session_cost", TOOLS / "session_cost.py")

RAMEK_LINE = ("魯道夫·拉梅克｜Rudolf Ramek｜bio-ramek｜federal-state-of-austria｜首任 1924-11-20｜薄（離線推定）｜"
              "federal-state-of-austria head_of_government「Bundeskanzler」1924-11-20～1926-10-20"
              "（recordId 01a1aa4a-a0bc-76d1-999e-fd43d3dd18df）")
RAMEK_TEXT = (
    "Navigation Home Suche\n" + "x " * 400 +
    "\nRamek, Rudolf (1881-1941), Politiker. Geb. Teschen, 12. 4. 1881; gest. Salzburg, 24. 7. 1941.\n"
    "Ramek war vom 20. November 1924 bis 20. Oktober 1926 Bundeskanzler der Republik Österreich.\n"
    + "y " * 600 + "\nAutor: Max Mustermann\n"
)


class FakeHttp:
    def __init__(self, entities=None):
        self.calls = 0
        self.urls = []
        self.entities = entities or {}

    def wait(self, url):
        self.urls.append(("wait", url))

    def get_json(self, url):
        self.calls += 1
        self.urls.append(("json", url))
        if "wbsearchentities" in url:
            return {"search": [{"id": "Q1"}, {"id": "Q2"}]}
        if "wbgetentities" in url and "props=claims&" in url:
            return {"entities": {
                "P227": {"claims": {"P1630": [{"mainsnak": {"datavalue": {"value": "https://www.deutsche-biographie.de/pnd$1.html"}}}]}},
                "P9999": {"claims": {"P1630": [{"mainsnak": {"datavalue": {"value": "https://example.blogspot.com/$1"}}}]}},
            }}
        if "wbgetentities" in url:
            return {"entities": self.entities}
        return None


def _human(label, born, died, ext=None):
    claims = {
        "P31": [{"mainsnak": {"datavalue": {"value": {"id": "Q5"}}}}],
        "P569": [{"mainsnak": {"datavalue": {"value": {"time": f"+{born}-01-01T00:00:00Z"}}}}],
        "P570": [{"mainsnak": {"datavalue": {"value": {"time": f"+{died}-01-01T00:00:00Z"}}}}],
    }
    for pid, value in (ext or {}).items():
        claims[pid] = [{"mainsnak": {"datatype": "external-id", "datavalue": {"value": value}}}]
    return {"labels": {"de": {"value": label}}, "aliases": {}, "claims": claims}


def _agent(root, kind="research", bio="bio-ramek", nn="123"):
    out = root / "out" / f"batch{nn}"
    raw = root / "raw" / f"batch{nn}" / "raw"
    return {
        "id": f"{kind}:{nn}:{bio}", "kind": kind, "model": "sonnet", "batch": nn, "bioId": bio,
        "name": "Rudolf Ramek", "line": RAMEK_LINE, "outDir": str(out), "rawDir": str(raw),
        "batchId": f"b3-full-v3-batch{nn}", "doneMarker": str(out / "people" / f"{bio}.agent-done.json"),
    }


class PrefilterTests(unittest.TestCase):
    def test_name_variants_keep_inverted_surname_before_aliases(self):
        info = {"name": "Rudolf Ramek", "nameZh": "魯道夫·拉梅克"}
        aliases = ["Rudolf Ramek", "رودلف رامك", "Рудольф Рамек", "ルドルフ・ラメク", "a1", "a2", "a3", "a4", "a5", "a6"]
        names = prefilter.name_variants(info, aliases)
        self.assertIn("Ramek, Rudolf", names)
        self.assertIn("Ramek", names)
        self.assertNotIn("Рудольф Рамек", names)

    def test_canonical_url_and_treccani_grade(self):
        self.assertEqual(prefilter.canonical_url("https://www.deutsche-biographie.de/126762589.html#indexcontent"),
                         "https://www.deutsche-biographie.de/pnd126762589.html")
        self.assertEqual(prefilter.host_info("https://www.treccani.it/enciclopedia/rudolf-ramek")["grade"], "B")
        self.assertEqual(prefilter.host_info(
            "https://www.treccani.it/enciclopedia/x_(Dizionario-Biografico)/")["grade"], "A")

    def test_cjk_name_searched_in_ja_and_zh(self):
        seen = []

        class FakeHttp:
            calls = 0

            def get_json(self, url):
                seen.append(url)
                return {}

        prefilter.index_lookup(FakeHttp(), {"name": "若槻禮次郎", "nameZh": "若槻禮次郎", "years": ["1926"]})
        langs = sorted(re.search(r"language=(\w+)", url).group(1) for url in seen)
        self.assertEqual(langs, ["ja", "zh"])

    def test_parse_line_and_names(self):
        info = prefilter.parse_line(RAMEK_LINE, "bio-ramek")
        self.assertEqual(info["name"], "Rudolf Ramek")
        self.assertEqual(info["nameZh"], "魯道夫·拉梅克")
        self.assertEqual(info["titles"], ["Bundeskanzler"])
        self.assertIn("1924", info["years"])
        self.assertNotIn("0001", "".join(info["years"]))
        self.assertEqual(info["recordIds"], ["01a1aa4a-a0bc-76d1-999e-fd43d3dd18df"])
        self.assertIn("Ramek", prefilter.name_variants(info))
        wakatsuki = prefilter.parse_line("若槻禮次郎（臨時兼任）｜若槻禮次郎｜bio-w｜empire-of-japan｜首任 1926-01-28", "bio-w")
        self.assertEqual(wakatsuki["nameZh"], "若槻禮次郎")
        self.assertIn("若槻", prefilter.name_variants(wakatsuki))

    def test_snippets_need_the_name_and_rank_years(self):
        names = ["Rudolf Ramek", "Ramek"]
        picked = prefilter.select_snippets(RAMEK_TEXT, names, ["1924", "Bundeskanzler"])
        joined = " ".join(snippet for _, snippet in picked)
        self.assertIn("Bundeskanzler", joined)
        self.assertIn("Autor: Max Mustermann", joined)
        self.assertLess(len(joined), len(RAMEK_TEXT))
        self.assertEqual(prefilter.select_snippets("nothing about him", names, ["1924"]), [])
        # 段落是原文的逐字片段：verify 的空白正規化後必是子字串
        norm_text = verify.norm(RAMEK_TEXT)
        for _, snippet in picked:
            self.assertIn(verify.norm(snippet), norm_text)

    def test_blocked_hosts(self):
        self.assertTrue(prefilter.blocked_host("https://de.wikipedia.org/wiki/Rudolf_Ramek"))
        self.assertTrue(prefilter.blocked_host("https://www.wikidata.org/wiki/Q1"))
        self.assertTrue(prefilter.blocked_host("https://foo.blogspot.com/x"))
        self.assertIsNone(prefilter.blocked_host("https://www.biographien.ac.at/oebl/x"))
        self.assertEqual(prefilter.host_info("https://www.biographien.ac.at/oebl/x")["grade"], "A")

    def test_pick_person_rejects_wrong_era(self):
        info = prefilter.parse_line(RAMEK_LINE, "bio-ramek")
        entities = {"Q1": _human("Rudolf Ramek", 1950, 2010), "Q2": _human("Rudolf Ramek", 1881, 1941)}
        self.assertEqual(prefilter.pick_person(entities, info), "Q2")
        self.assertIsNone(prefilter.pick_person({"Q1": _human("Rudolf Ramek", 1950, 2010)}, info))

    def test_run_fetches_whitelist_only_and_never_refetches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = _agent(root)
            http = FakeHttp({"Q2": _human("Rudolf Ramek", 1881, 1941, {"P227": "118597930", "P9999": "x"})})
            fetched = []

            def fake_fetch(rawdir, rawmap, key, url, keywords, max_chars):
                fetched.append(url)
                Path(rawdir, f"{key}.txt").write_text(RAMEK_TEXT, encoding="utf-8")
                fetch.update_rawmap(rawmap, key, f"{key}.txt")
                return f"RESULT=fetched\nsourceKey={key}\n"

            summary = prefilter.run(agent, http=http, fetcher=fake_fetch, today="2026-11-18")
            self.assertEqual(summary["relevant"], 1)
            self.assertEqual(fetched, ["https://www.deutsche-biographie.de/pnd118597930.html"])
            people = Path(agent["outDir"]) / "people"
            md = (people / "bio-ramek.snippets.md").read_text(encoding="utf-8")
            self.assertIn("Bundeskanzler", md)
            self.assertNotIn("wikidata", md.lower())
            self.assertNotIn("blogspot", md)
            pre = json.loads((people / "bio-ramek.prefilter.json").read_text(encoding="utf-8"))
            self.assertNotIn("wikidata.org", json.dumps(pre["searchLog"]))
            self.assertEqual(pre["person"]["key"], "rudolf-ramek")
            # 第二次（例如補了網址）不重抓已存的頁，也不再做索引查詢
            calls = http.calls
            prefilter.run(agent, http=http, fetcher=fake_fetch, today="2026-11-18")
            self.assertEqual(len(fetched), 1)
            self.assertEqual(http.calls, calls)

    def test_offline_run_skips_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = _agent(Path(tmp))

            def boom(*args, **kwargs):
                raise AssertionError("offline 不可抓")

            http = prefilter.Http(Path(tmp) / "idx", offline=True)
            summary = prefilter.run(agent, offline=True, extra_urls=["https://www.biographien.ac.at/x"],
                                    http=http, fetcher=boom)
            self.assertEqual(summary["relevant"], 0)
            self.assertEqual(http.calls, 0)


def _write_draft_fixture(root, quote="Ramek war vom 20. November 1924 bis 20. Oktober 1926 Bundeskanzler"):
    agent = _agent(root)
    raw = Path(agent["rawDir"])
    raw.mkdir(parents=True)
    (raw / "oebl-ramek.txt").write_text(RAMEK_TEXT, encoding="utf-8")
    out = Path(agent["outDir"])
    people = out / "people"
    people.mkdir(parents=True)
    (out / "rawmap.json").write_text('{"oebl-ramek": "oebl-ramek.txt"}\n', encoding="utf-8")
    (people / "bio-ramek.prefilter.json").write_text(json.dumps({
        "person": {"key": "rudolf-ramek", "name": "Rudolf Ramek", "nameZh": "魯道夫·拉梅克", "recordIds": ["r1"]},
        "sources": {"oebl-ramek": {"url": "https://www.biographien.ac.at/oebl/x", "suggestedGrade": "A",
                                    "label": "Österreichisches Biographisches Lexikon", "title": "Ramek, Rudolf",
                                    "accessedOn": "2026-11-18"}},
        "searchLog": [{"step": 1, "sourceType": "authority", "query": "q", "url": None, "result": "unrated", "note": "n"}],
    }, ensure_ascii=False), encoding="utf-8")
    body = "拉梅克於1924年11月20日至1926年10月20日任奧地利聯邦總理。" * 3
    draft = {
        "thickness": "薄",
        "sources": {"oebl-ramek": {"authors": ["Max Mustermann"], "gradeBasis": "ÖBL 具名作者"}},
        "paragraphs": [{
            "ord": i, "period": {"start": "1924-11-20", "end": "1926-10-20"},
            "periodStartPrecision": "day", "periodEndPrecision": "day",
            "heading": {"zh-Hant": "總理", "en": "Chancellor"},
            "body": {"zh-Hant": body, "en": "Ramek was chancellor."},
            "citations": [{"sourceKey": "oebl-ramek", "quote": quote, "quoteLang": "de", "datePrecision": "day"}],
        } for i in (1, 2, 3)],
        "positions": [], "roleCandidates": [],
        "gaps": [{"target": "role:ramek-chancellor", "gapKind": "not_found", "note": "不重建：名單 5442 已有"}],
        "searchLog": [{"sourceType": "other", "query": "extra", "url": None, "result": "no_result", "note": "x"}],
    }
    (people / "bio-ramek.draft.json").write_text(json.dumps(draft, ensure_ascii=False), encoding="utf-8")
    spec = root / "spec.json"
    spec.write_text(json.dumps({"agents": [agent, dict(agent, id="review:123:bio-ramek", kind="review")]}), encoding="utf-8")
    return agent, spec


class DraftTests(unittest.TestCase):
    def test_assemble_keeps_person_file_format_and_passes_verify(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec = _write_draft_fixture(Path(tmp))
            out = io_capture(lambda: draft_mod.cmd_check(str(spec), agent["id"], done=True, today="2026-11-18"))
            self.assertIn("SELFCHECK ok", out)
            self.assertIn("CHECKMIN OK", out)
            person_file = Path(agent["outDir"]) / "people" / "bio-ramek.json"
            doc = json.loads(person_file.read_text(encoding="utf-8"))
            self.assertEqual(set(doc), {"person", "sources", "rawMap", "researchedOn", "policyVersion",
                                        "alignedTo", "alignNote", "schemaNote"})
            self.assertIsInstance(doc["rawMap"], dict)
            self.assertEqual(doc["rawMap"], {"oebl-ramek": "oebl-ramek.txt"})
            cite = doc["person"]["paragraphs"][0]["citations"][0]
            self.assertEqual(cite["grade"], "A")
            self.assertEqual(cite["accessedOn"], "2026-11-18")
            self.assertTrue(cite["locator"].startswith("正文"))
            self.assertEqual([s["step"] for s in doc["person"]["searchLog"]], [1, 2])
            self.assertEqual(doc["sources"]["oebl-ramek"]["authors"], ["Max Mustermann"])
            marker = json.loads((Path(agent["outDir"]) / "people" / "bio-ramek.agent-done.json").read_text())
            self.assertEqual((marker["stage"], marker["ok"]), ("research", True))
            # 合併後與原本流程相同：merge_people 收得下這個單人檔
            io_capture(lambda: merge.merge(agent["outDir"], agent["rawDir"], agent["batchId"], ["bio-ramek"]))
            self.assertTrue((Path(agent["outDir"]) / "research.json").exists())

    def test_check_reports_quote_not_in_raw(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec = _write_draft_fixture(Path(tmp), quote="Ramek war ein erfundener Satz")
            out = io_capture(lambda: draft_mod.cmd_check(str(spec), agent["id"], today="2026-11-18"))
            self.assertIn("SELFCHECK fail", out)
            self.assertIn("引文未逐字出現", out)
            self.assertFalse((Path(agent["outDir"]) / "people" / "bio-ramek.agent-done.json").exists())

    def test_review_done_writes_note_and_marker(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec = _write_draft_fixture(Path(tmp))
            io_capture(lambda: draft_mod.cmd_check(str(spec), agent["id"], today="2026-11-18"))
            out = io_capture(lambda: draft_mod.cmd_review_done(str(spec), "review:123:bio-ramek", "pass", "ok", '["無"]'))
            self.assertIn("REVIEW_DONE pass verify錯誤 0", out)
            people = Path(agent["outDir"]) / "people"
            self.assertEqual(json.loads((people / "bio-ramek.review.json").read_text())["verdict"], "pass")
            self.assertEqual(json.loads((people / "bio-ramek.agent-done.json").read_text())["stage"], "review")

    def test_person_patch_paths(self):
        doc = {"person": {"paragraphs": [{"citations": [{"quote": "a"}, {"quote": "b"}]}], "gaps": []}}
        patch_mod.apply(doc, "set", "person.paragraphs[0].citations[1].quote", "c")
        patch_mod.apply(doc, "del", "person.paragraphs[0].citations[0]")
        patch_mod.apply(doc, "append", "person.gaps", {"target": "identity"})
        self.assertEqual(patch_mod.apply(doc, "get", "person.paragraphs[0].citations"), [{"quote": "c"}])
        self.assertEqual(doc["person"]["gaps"], [{"target": "identity"}])
        with self.assertRaises(SystemExit):
            patch_mod.apply(doc, "get", "person.positions[0]")


def io_capture(func):
    import contextlib
    import io as _io
    buffer = _io.StringIO()
    with contextlib.redirect_stdout(buffer):
        func()
    return buffer.getvalue()


class LeanPromptTests(unittest.TestCase):
    def _batch(self):
        return {"nn": "123", "outDir": "/repo/out/batch123", "rawDir": "/raw/batch123/raw",
                "researchPrompt": "/repo/.dev/b3v3/prompts/research-123.md", "reviewPrompt": "/repo/review-123.md",
                "specPath": ".dev/b3v3/run/pilot-spec.json"}

    def test_research_prompt_is_compact_and_self_contained(self):
        person = {"bioId": "bio-ramek", "line": RAMEK_LINE, "name": "Rudolf Ramek", "nameZh": "拉梅克"}
        text = specs_mod.research_prompt(self._batch(), person, "/repo")
        self.assertLess(len(text.encode("utf-8")), 9000)
        self.assertNotIn("research-123.md", text)
        self.assertIn("bio-ramek.draft.json", text)
        self.assertIn("person_draft.py check --spec .dev/b3v3/run/pilot-spec.json --id research:123:bio-ramek", text)
        self.assertIn("WebSearch 最多 2 次", text)
        self.assertNotIn("至少 8 次", text)

    def test_review_prompt_reads_only_the_slice(self):
        person = {"bioId": "bio", "line": "某人", "name": "某人"}
        text = specs_mod.review_prompt(self._batch(), person, "/repo")
        self.assertLess(len(text.encode("utf-8")), 6000)
        self.assertNotIn("review-123.md", text)
        self.assertIn("不要讀單人檔全文", text)
        self.assertIn("review-done --spec .dev/b3v3/run/pilot-spec.json --id review:123:bio", text)
        esc = specs_mod.review_prompt(self._batch(), person, "/repo", escalate=True)
        self.assertIn("--id escalate:123:bio", esc)

    def test_every_launch_pins_model_turns_and_tools(self):
        base = {"outDir": "/repo/out/batch123", "bioId": "bio", "model": None}
        expect = {"research": ("sonnet", 11), "retry": ("sonnet", 9), "review": ("sonnet", 6),
                  "escalate": ("opus", 6), "discover": ("haiku", 4)}
        for kind, (model, turns) in expect.items():
            profile = specs_mod.launch_profile(dict(base, kind=kind), "/repo")
            self.assertEqual((profile["model"], profile["maxTurns"]), (model, turns), kind)
            cmd = loop_mod.build_command(dict(base, kind=kind), "p", "sid", profile, "n")
            for flag in ("--model", "--max-turns", "--tools", "--allowedTools", "--strict-mcp-config",
                         "--system-prompt", "--session-id"):
                self.assertIn(flag, cmd)
            self.assertEqual(cmd[cmd.index("--permission-mode") + 1], "dontAsk")
            self.assertEqual(cmd[cmd.index("--model") + 1], model)
        research = specs_mod.launch_profile(dict(base, kind="research"), "/repo")
        self.assertIn("Write(out/batch123/people/bio.draft.json)", research["allowed"])
        self.assertNotIn("Bash", [rule for rule in research["allowed"] if rule == "Bash"])

    def test_show_prompt_attaches_snippets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agent = _agent(root)
            people = Path(agent["outDir"]) / "people"
            people.mkdir(parents=True)
            (people / "bio-ramek.snippets.md").write_text("@12: Ramek war Bundeskanzler\n", encoding="utf-8")
            spec = root / "spec.json"
            spec.write_text(json.dumps({"agents": [dict(agent, prompt="任務\n")]}), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "show-prompt", "--spec", str(spec), "--id", agent["id"]],
                capture_output=True, text=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("任務", proc.stdout)
            self.assertIn("Ramek war Bundeskanzler", proc.stdout)


class PartialBatchTests(unittest.TestCase):
    def test_unresearched_people_get_their_own_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prompts = root / "prompts"
            prompts.mkdir()
            people = [_fixture_person("a", "Person A", "bio-a", []), _fixture_person("b", "Person B", "bio-b", [])]
            _write_prompt(prompts, "123", people)
            _write_batch(root / "out", "123", people[:1])
            items = plan.from_chunk(str(root), "prompts", "out", "raw", ["123"], False)
            self.assertTrue(items[0]["research"])
            self.assertEqual(items[0]["researchPeople"], ["bio-b"])
            proc = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "dry-run", "--repo", str(root),
                 "--prompt-dir", "prompts", "--out-root", "out", "--raw-root", "raw", "--chunk", "123",
                 "--concurrency", "1", "--json"],
                capture_output=True, text=True, cwd=root,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            data = json.loads(proc.stdout)
            self.assertEqual([a["name"] for w in data["waves"] if w["phase"] == "research" for a in w["agents"]], ["Person B"])
            only = subprocess.run(
                [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "dry-run", "--repo", str(root),
                 "--prompt-dir", "prompts", "--out-root", "out", "--raw-root", "raw", "--chunk", "123",
                 "--people", "bio-a", "--concurrency", "1", "--json"],
                capture_output=True, text=True, cwd=root,
            )
            self.assertEqual(only.returncode, 0, only.stderr)
            self.assertEqual(json.loads(only.stdout)["researchAgents"], 0)


class LoopTests(unittest.TestCase):
    def test_discover_only_when_thin(self):
        self.assertFalse(loop_mod.needs_discover({"relevant": 6, "narrative": 4, "snippetChars": 12769}))
        self.assertTrue(loop_mod.needs_discover({"relevant": 2, "narrative": 1, "snippetChars": 2912}))
        self.assertTrue(loop_mod.needs_discover({"relevant": 3, "narrative": 3, "snippetChars": 900}))

    def test_research_marker_does_not_count_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = Path(tmp) / "x.agent-done.json"
            marker.write_text(json.dumps({"ok": True, "bioId": "b1", "stage": "research"}), encoding="utf-8")
            review = {"doneMarker": str(marker), "bioId": "b1", "kind": "review"}
            research = dict(review, kind="research")
            self.assertTrue(loop_mod.marker_ok(research))
            self.assertFalse(loop_mod.marker_ok(review))
            marker.write_text(json.dumps({"ok": True, "bioId": "b1", "stage": "review"}), encoding="utf-8")
            self.assertTrue(loop_mod.marker_ok(review))

    def _journal(self, tmp):
        return loop_mod.Journal(Path(tmp) / "logs")

    def test_network_errors_kill_fast(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._journal(tmp)
            log = journal.dir / "a.jsonl"
            script = ("import time,sys\n"
                      "for i in range(3):\n"
                      "    print('{\"type\":\"system\",\"subtype\":\"api_retry\",\"error\":\"getaddrinfo ENOTFOUND api.anthropic.com\"}', flush=True)\n"
                      "time.sleep(60)\n")
            with log.open("ab") as fh:
                proc = subprocess.Popen([sys.executable, "-c", script], stdout=fh, stderr=subprocess.STDOUT,
                                        start_new_session=True)
                started = time.time()
                outcome, rc = loop_mod.watch(proc, log, 300, journal, "a", dns_probe=lambda: True)
            self.assertEqual(outcome, "network")
            self.assertLess(time.time() - started, 40)

    def test_dns_outage_kills_without_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = self._journal(tmp)
            log = journal.dir / "b.jsonl"
            old = (loop_mod.DNS_EVERY_SECONDS, loop_mod.POLL_SECONDS)
            loop_mod.DNS_EVERY_SECONDS, loop_mod.POLL_SECONDS = 0, 0.05
            try:
                with log.open("ab") as fh:
                    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"], stdout=fh,
                                            start_new_session=True)
                    outcome, _ = loop_mod.watch(proc, log, 300, journal, "b", dns_probe=lambda: False)
            finally:
                loop_mod.DNS_EVERY_SECONDS, loop_mod.POLL_SECONDS = old
            self.assertEqual(outcome, "network")

    def test_parse_urls_and_session_cost(self):
        self.assertEqual(loop_mod.parse_urls('ok {"urls":["https://a.test/x","ftp://no"]}'), ["https://a.test/x"])
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "s.jsonl"
            usage = {"input_tokens": 2, "cache_creation_input_tokens": 100, "cache_read_input_tokens": 1000, "output_tokens": 10}
            lines = [
                {"type": "assistant", "message": {"id": "m1", "model": "claude-sonnet", "usage": usage}},
                {"type": "assistant", "message": {"id": "m1", "model": "claude-sonnet", "usage": usage}},
                {"type": "assistant", "message": {"id": "m2", "model": "claude-sonnet", "usage": usage}},
            ]
            path.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            row = cost_mod.session_usage(path)
            self.assertEqual(row["calls"], 2)
            self.assertEqual(row["total"], 2 * 1112)
            self.assertEqual(row["maxContext"], 1102)


tiers_mod = load("tiers", TOOLS / "tiers.py")
uncited_mod = load("uncited", TOOLS / "uncited.py")
c_rules = load("c_rules", TOOLS.parent / "c_rules.py")
WIKI_TEXT = "Rudolf Ramek (* 12. April 1881 in Teschen; † 24. Juli 1941 in Wien) war ein österreichischer Politiker der CS."


def _tier_fixture(root):
    """一個已組好的單人檔（主內容 A）＋ C 級原文（Wikipedia）在 RAWDIR。"""
    agent, spec = _write_draft_fixture(root)
    io_capture(lambda: draft_mod.cmd_check(str(spec), agent["id"], today="2026-11-18"))
    raw = Path(agent["rawDir"])
    (raw / "c-wp-de-abc123.txt").write_text(WIKI_TEXT, encoding="utf-8")
    people = Path(agent["outDir"]) / "people"
    (people / "bio-ramek.c.json").write_text(json.dumps({"sources": {"c-wp-de-abc123": {
        "url": "https://de.wikipedia.org/wiki/Rudolf_Ramek", "title": "Rudolf Ramek – Wikipedia（de）",
        "publisher": "Wikipedia", "lang": "de", "grade": "C", "accessedOn": "2026-11-18"}}}, ensure_ascii=False),
        encoding="utf-8")
    tier_agent = dict(agent, id="csupp:123:bio-ramek", kind="csupp", specPath=str(spec))
    spec.write_text(json.dumps({"agents": [agent, tier_agent]}), encoding="utf-8")
    return tier_agent, spec, people / "bio-ramek.json"


def _add_unit(doc, key, start):
    """測試用：借主內容第一條引文，補一筆只有起日的職位。"""
    cite = dict(doc["person"]["paragraphs"][0]["citations"][0])
    doc["person"].setdefault("positions", []).append({"key": key, "title": {"zh-Hant": "職位", "en": "Post"},
                                                       "period": {"start": start, "end": None}, "startPrecision": "day",
                                                       "endPrecision": None, "positionKind": "legislator",
                                                       "organization": "Test", "citations": [cite]})


def _research_of(doc, agent):
    return {"batch": "t", "rawDir": agent["rawDir"], "rawMap": "rawmap.json", "sources": doc["sources"],
            "people": [doc["person"]], "alignedTo": "b0b0e0f", "alignNote": "x"}


class TierTests(unittest.TestCase):
    def _supp(self, agent, person_file, patch):
        base = json.loads(person_file.read_text(encoding="utf-8"))
        doc, problems = tiers_mod.apply_csupp(agent, base, patch, today="2026-11-18")
        return doc, problems

    def test_supplement_c_is_isolated_and_quotes_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            doc, problems = self._supp(agent, person_file, {
                "clauses": [{"target": "paragraph:length", "text": {"zh-Hant": "他是基督教社會黨政治人物。", "en": "CS politician."},
                             "cKey": "c-wp-de-abc123", "quote": "war ein österreichischer Politiker der CS"}],
                "dates": [{"target": "position:x.end", "value": "1941-07-24", "precision": "day",
                           "cKey": "c-wp-de-abc123", "quote": "† 24. Juli 1941 in Wien"}]})
            self.assertEqual(problems, [])
            doc["person"]["supplementC"]["dates"][0]["target"] = "position:x.end"
            _add_unit(doc, "x", "1926-01-01")
            supp = doc["person"]["supplementC"]
            self.assertEqual((supp["grade"], supp["status"], supp["displayFlag"]), ("C", "A/B不足，已用C補", "未查證・維基百科補充"))
            self.assertTrue(all(c["url"].startswith("https://de.wikipedia.org/") for c in supp["clauses"] + supp["dates"]))
            self.assertTrue(supp["dates"][0]["status"].startswith("待查證"))
            errors, c_errors, row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertEqual((errors, c_errors), ([], []))  # Wikipedia 網址只在補充區：主內容不報錯
            # 主段落仍只算 A／B：同一份資料的 check_min 不因 C 改變段數字數
            self.assertEqual(row["zhChars"], check_min.check({k: v for k, v in doc["person"].items() if k != "supplementC"})["zhChars"])
            # C 引文不逐字 → 另列 supplementCErrors，主內容 errors 仍空
            doc["person"]["supplementC"]["clauses"][0]["quote"] = "erfundener Satz"
            doc["person"]["supplementC"]["dates"][0]["confirmed"] = True
            errors, c_errors, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertEqual(errors, [])
            self.assertTrue(any("引文未逐字" in e for e in c_errors))
            self.assertTrue(any("不能確認日期" in e for e in c_errors))

    def test_supplement_c_conflict_with_ab_is_error_then_moved_to_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            doc, _ = self._supp(agent, person_file, {"dates": [{"target": "position:x.end", "value": "1941-07-24", "precision": "day",
                                                                 "cKey": "c-wp-de-abc123", "quote": "† 24. Juli 1941 in Wien"}]})
            _add_unit(doc, "x", "1950-01-01")          # A／B 起日 1950：C 迄日 1941 衝突
            _errors, c_errors, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertTrue(any("以 A／B 為準" in e for e in c_errors))
            log = tiers_mod.screen_supplement(doc["person"])
            self.assertEqual(log[0]["action"], "conflict→note")
            supp = doc["person"]["supplementC"]
            self.assertEqual(supp["dates"], [])
            self.assertEqual(supp["conflictNotes"][0]["conflictsWithAB"]["ref"], "position:x.end")
            errors, c_errors, row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertEqual((errors, c_errors), ([], []))
            self.assertEqual(row.get("cDates"), 0)        # 衝突註記不算、不顯示
            doc["person"]["supplementC"]["dates"].append(dict(supp["conflictNotes"][0], target="position:nope.end"))
            _errors, c_errors, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertTrue(any("主內容沒有 nope" in e for e in c_errors))

    def test_date_conflict_rules_duan_case(self):
        unit = {"key": "w16", "title": {"zh-Hant": "陸軍總長（兼國務總理）"}, "period": {"start": "1916-04-01", "end": None}}
        person = {"positions": [unit], "roleCandidates": []}
        duan = {"target": "position:w16.end", "value": "1915-08-29", "quote": "任期 1912年 3月29日 – 1915年 8月29日"}
        clash = c_rules.date_conflict(person, duan)
        self.assertIn("早於 A／B 起日", clash["reason"])
        self.assertIn("不重疊", clash["reason"])
        # 同一端 A／B 已有值、不同 → 衝突；同年（year 精度）→ 不衝突
        person2 = {"positions": [dict(unit, period={"start": "1916-04-01", "end": "1917-05-23"}, endPrecision="day")]}
        self.assertIn("A／B 已有 end", c_rules.date_conflict(person2, dict(duan, value="1918-01-01", quote="1918"))["reason"])
        person3 = {"positions": [dict(unit, period={"start": "1916-04-01", "end": "1917-01-01"}, endPrecision="year")]}
        self.assertIsNone(c_rules.date_conflict(person3, dict(duan, value="1917-05-23", quote="1917年5月23日")))
        # 落在另一筆同名任期
        other = {"key": "w12", "title": {"zh-Hant": "陸軍總長"}, "period": {"start": "1912-03-29", "end": "1915-08-29"}}
        person4 = {"positions": [dict(unit, period={"start": "1912-01-01", "end": None}), other]}
        self.assertIn("另一筆同名", c_rules.date_conflict(person4, dict(duan, value="1913-01-01", quote="1913"))["reason"])
        # 正確的 C 日期不擋（田中：1926 起、C 迄日 1929）
        ok = {"positions": [{"key": "t", "title": {"zh-Hant": "貴族院議員"}, "period": {"start": "1926-01-01", "end": None}}]}
        self.assertIsNone(c_rules.date_conflict(ok, {"target": "position:t.end", "value": "1929-09-29",
                                                     "quote": "1926年 1月29日 - 1929年9月29日"}))
        # 句子層：提到 A／B 職稱但年份全在任期外
        clause = {"text": {"zh-Hant": "他在1912年出任陸軍總長。"}}
        self.assertIsNotNone(c_rules.clause_conflict(person, clause))
        self.assertIsNone(c_rules.clause_conflict(person, {"text": {"zh-Hant": "他在1916年出任陸軍總長。"}}))

    def test_support_gaps_normalize_eras_kanji_months(self):
        self.assertEqual(c_rules.support_gaps("首相官邸記錄在職期間為大正15年1月30日至昭和2年4月20日。",
                                              "在職期間 大正15年1月30日 ～昭和2年4月20日"), [])
        self.assertEqual(c_rules.support_gaps("1918年9月29日就任。", "大正七年九月二十九日"), [])
        self.assertEqual(c_rules.support_gaps("1917年3月出任總理。", "appointed Premier in March 1917"), [])
        self.assertEqual(c_rules.support_gaps("陸軍總長，1917年。", "陸軍總長 民國6年"), [])
        self.assertEqual(c_rules.support_gaps("他在1918年2月被選為議長。", "ザカフカス国会議長に選出された"), ["1918", "2"])
        self.assertEqual(c_rules.support_gaps("他與Kerensky會面。", "met Lenin"), ["Kerensky"])
        self.assertEqual(c_rules.support_gaps("他創辦《時報》。", "創辦「時報」"), [])
        self.assertEqual(c_rules.support_gaps("若槻禮次郎組閣。", "若槻礼次郎が組閣"), [])
        self.assertEqual(c_rules.norm(c_rules.norm("終年65歲國")), c_rules.norm("終年65歲國"))   # 正規化要冪等
        self.assertEqual(c_rules.support_gaps("原文：「9月29日去世，終年65歲」", "9月29日去世，終年65歲"), [])
        self.assertEqual(c_rules.support_gaps("他一度主張嚴懲。", "主張"), [])      # 「一度」不是數字
        self.assertIsNotNone(c_rules.overreach("中文維基百科稱，皇姑屯事件後田中一度主張嚴懲主謀，後因陸軍反對而改口，受到批評，終在1929年7月被迫辭職。",
                                               "並於1929年7月2日被迫向天皇辞职"))
        self.assertIsNone(c_rules.overreach("1929年7月2日被迫辭職。", "並於1929年7月2日被迫向天皇辞职"))

    def test_support_fix_trims_or_falls_back_to_quote(self):
        clause = {"target": "paragraph:length", "quote": "1929年7月2日被迫向天皇辞职", "quoteLang": "zh",
                  "text": {"zh-Hant": "1929年7月2日被迫辭職。他在1930年去世。", "en": "He resigned on 2 July 1929. He died in 1930."}}
        fixed, entry = tiers_mod.support_fix(clause)
        self.assertEqual(entry["action"], "trimmed-unsupported")
        self.assertEqual(fixed["text"]["zh-Hant"], "1929年7月2日被迫辭職。")
        self.assertEqual(fixed["text"]["en"], "He resigned on 2 July 1929.")
        clause["text"] = {"zh-Hant": "他在1930年去世。", "en": "He died in 1930."}
        fixed, entry = tiers_mod.support_fix(clause)
        self.assertEqual(entry["action"], "quote-only")
        self.assertIn("1929年7月2日被迫向天皇辞职", fixed["text"]["zh-Hant"])
        self.assertEqual(c_rules.support_gaps(fixed["text"]["zh-Hant"], clause["quote"]), [])
        # C 日期年份不在引文 → 刪；C 單獨的日期一律 待查證
        person = {"positions": [{"key": "x", "title": {"zh-Hant": "職"}, "period": {"start": "1920-01-01", "end": None}}],
                  "supplementC": {"sources": {"k": {}}, "clauses": [],
                                  "dates": [{"target": "position:x.end", "value": "1931-01-01", "quote": "1930年", "cKey": "k",
                                             "status": "待查證（只有 C 級來源）", "confirmed": False}]}}
        log = tiers_mod.screen_supplement(person)
        self.assertEqual(log[0]["action"], "dropped-unsupported")
        self.assertNotIn("supplementC", person)

    def test_stage2_support_drops_sentence_with_year_not_in_quote(self):
        para = {"ord": 4, "body": {"zh-Hant": "1906年任大藏次官。1910年任大臣。", "en": "Vice-minister in 1906. Minister in 1910."},
                "citations": [{"quote": "1906年（明治39）大蔵次官", "claimSpan": [1, 2]}]}
        person = {"paragraphs": [para]}
        log = tiers_mod.stage2_support(person, ["4"])
        self.assertEqual([(i["s"], i["dropped"]) for i in log], [(2, True)])
        self.assertEqual(para["body"]["zh-Hant"], "1906年任大藏次官。")
        self.assertEqual(para["citations"][0]["claimSpan"], [1])
        # 只缺月日（非年份）：不自動刪，回報
        para2 = {"ord": 5, "body": {"zh-Hant": "1906年3月任次官。", "en": "In March 1906."},
                 "citations": [{"quote": "1906年 次官", "claimSpan": [1]}]}
        log = tiers_mod.stage2_support({"paragraphs": [para2]}, ["5"])
        self.assertEqual(log[0]["dropped"], False)
        self.assertIn("3", log[0]["gaps"])

    def test_stage2_candidates_only_short_or_missing_end(self):
        needs = ["篇幅（現 3 段／182 字，目標 3 段／300 字）", "position:a.start", "position:b.end（已標待查證）", "role:c.end"]
        self.assertEqual(tiers_mod.stage2_needs(needs), [needs[0], needs[2], needs[3]])
        self.assertEqual(tiers_mod.stage2_needs(["position:a.start"]), [])

    def test_office_hints_from_index(self):
        class Offline:
            offline = True
            calls = 0
            cache_dir = Path(tempfile.mkdtemp())

            def get_json(self, url):
                return None
        entity = {"claims": {"P39": [{"mainsnak": {"datavalue": {"value": {"id": "Q1"}}},
                                      "qualifiers": {"P580": [{"datavalue": {"value": {"time": "+1916-04-23T00:00:00Z"}}}],
                                                     "P582": [{"datavalue": {"value": {"time": "+1917-05-23T00:00:00Z"}}}],
                                                     "P1366": [{"datavalue": {"value": {"id": "Q2"}}}]}}]}}
        hints = prefilter.office_hints(Offline(), entity)
        self.assertEqual((hints[0]["start"], hints[0]["end"], hints[0]["successor"]), ("1916-04-23", "1917-05-23", ["Q2"]))
        self.assertIn("後任 Q2", prefilter.render_office_hints(hints))
        self.assertIn("不是出處", prefilter.render_office_hints(hints))

    def test_c_end_date_needs_end_evidence_and_day_precision_needs_day(self):
        # 齊赫澤：「1919年3月成為制憲議會議長」不能當外高加索議會的迄日
        self.assertFalse(c_rules.end_quote_ok("1919年 3月、 グルジア民主共和国 憲法制定議会（制憲議会）の議長となった"))
        self.assertTrue(c_rules.end_quote_ok("1926年 1月29日 - 1929年9月29日"))
        self.assertTrue(c_rules.end_quote_ok("1918年5月26日に議会は解散した"))
        person = {"positions": [{"key": "seim", "title": {"zh-Hant": "議長"}, "period": {"start": "1918-01-01", "end": None}}],
                  "supplementC": {"sources": {"k": {}}, "clauses": [], "dates": [
                      {"target": "position:seim.end", "value": "1919-03-01", "cKey": "k", "status": "待查證（只有 C 級來源）",
                       "confirmed": False, "quote": "1919年 3月、 グルジア民主共和国 憲法制定議会（制憲議会）の議長となった"}]}}
        log = tiers_mod.screen_supplement(person)
        self.assertEqual(log[0]["action"], "dropped-unsupported")
        # 段祺瑞：4 月 24 日的電報不能撐 1916-04-01 日精度
        cites = [{"quote": "American Legation, Peking, April 24, 1916, 6 p.m."}]
        self.assertTrue(tiers_mod.date_problems("p", {"start": "1916-04-01"}, cites, {"start": "day"}))
        self.assertEqual(tiers_mod.date_problems("p", {"start": "1916-04-24"}, cites, {"start": "day"}), [])
        self.assertEqual(tiers_mod.date_problems("p", {"start": "1916-04-01"}, cites, {"start": "month"}), [])

    def test_usage_limit_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "a.jsonl"
            log.write_text('{"type":"assistant","error":"rate_limit","api_error":"usage_limit_reached"}\n', encoding="utf-8")
            self.assertTrue(tiers_mod.usage_limited(log))
            log.write_text('{"type":"result","subtype":"success"}\n', encoding="utf-8")
            self.assertFalse(tiers_mod.usage_limited(log))

    def test_merge_back_dry_run_leaves_files_and_apply_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            doc = json.loads(person_file.read_text(encoding="utf-8"))
            out_root = Path(tmp) / "real"
            batch = out_root / "batch123"
            (batch / "people").mkdir(parents=True)
            research = _research_of(doc, agent)
            (batch / "research.json").write_text(json.dumps(research, ensure_ascii=False), encoding="utf-8")
            (batch / "rawmap.json").write_text(json.dumps(doc.get("rawMap") or {}), encoding="utf-8")
            before = (batch / "research.json").read_text(encoding="utf-8")
            work = Path(tmp) / "work" / "batch123" / "people"
            work.mkdir(parents=True)
            new = json.loads(json.dumps(doc))
            new["person"]["paragraphs"].append(dict(new["person"]["paragraphs"][0], ord=99))
            new["rawMap"] = dict(new.get("rawMap") or {}, **{"extra-key": "extra-key.txt"})
            bio = new["person"]["bioId"]
            (work / f"{bio}.json").write_text(json.dumps(new, ensure_ascii=False), encoding="utf-8")
            report = tiers_mod.merge_back([f"123:{bio}"], Path(tmp) / "work", out_root, apply=False)
            entry = report["batches"]["123"]
            self.assertEqual((batch / "research.json").read_text(encoding="utf-8"), before)   # dry-run 不動正式檔
            self.assertFalse((batch / "people" / f"{bio}.json").exists())
            self.assertIn("段落", entry["people"][0]["diff"][0])
            self.assertEqual(entry["rawmapAdded"], 1)
            self.assertIn("exit", entry["verify"])
            self.assertTrue(entry["checkMin"])
            tiers_mod.merge_back([f"123:{bio}"], Path(tmp) / "work", out_root, apply=True)
            merged = json.loads((batch / "research.json").read_text(encoding="utf-8"))
            self.assertEqual(len(merged["people"][0]["paragraphs"]), len(new["person"]["paragraphs"]))
            self.assertTrue((batch / "people" / f"{bio}.json").exists())

    def test_main_paragraph_cannot_cite_c_or_wikipedia(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            doc, _ = self._supp(agent, person_file, {"clauses": [{"target": "paragraph:length", "text": {"zh-Hant": "政治人物。"},
                                                                  "cKey": "c-wp-de-abc123", "quote": "österreichischer Politiker"}]})
            doc["person"]["paragraphs"][0]["citations"].append({"sourceKey": "c-wp-de-abc123", "quote": "österreichischer Politiker",
                                                                "grade": "C", "locator": "x", "accessedOn": "2026-11-18"})
            errors, _c, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertTrue(any("未知來源 c-wp-de-abc123" in e for e in errors))
            doc["person"]["paragraphs"][0]["citations"].pop()
            doc["sources"]["wp"] = {"url": "https://en.wikipedia.org/wiki/X", "grade": "B", "title": "x"}
            errors, _c, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertTrue(any("Wikipedia" in e or "網域被排除" in e for e in errors))

    def test_check_min_verdict_with_c(self):
        person = {"key": "k", "paragraphs": [{"body": {"zh-Hant": "短。"}}], "positions": [], "gaps": [
            {"target": "paragraph:length", "note": "篇幅不足：只找到一段"}]}
        self.assertEqual(check_min.check(person)["verdict"], "篇幅不足")
        person["supplementC"] = {"grade": "C", "clauses": [{"text": {"zh-Hant": "補充一句。"}}], "dates": []}
        row = check_min.check(person)
        self.assertEqual(row["verdict"], "A/B不足，已用C補")
        self.assertFalse(row["meetsMinimum"])
        self.assertEqual(row["zhChars"], 2)

    def test_prune_when_ab_found(self):
        person = {"positions": [{"key": "x", "period": {"start": "1920-01-01", "end": "1925-01-01"}}],
                  "supplementC": {"sources": {"c1": {}}, "clauses": [{"cKey": "c1"}],
                                  "dates": [{"target": "position:x.end", "cKey": "c1"}]}}
        removed = tiers_mod.prune_supplement(person, {"paragraphs": 3, "zhChars": 320})
        self.assertEqual(removed, 2)
        self.assertNotIn("supplementC", person)

    def test_stage2_patch_applies_and_keeps_old_citation_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, kind="deep")
            base = json.loads(person_file.read_text(encoding="utf-8"))
            old = base["person"]["paragraphs"][0]["citations"][0]
            new_para = dict(base["person"]["paragraphs"][0], ord=4)
            new_para["citations"] = [{"sourceKey": "oebl-ramek", "quote": old["quote"], "claimSpan": [1]}]
            doc, problems = tiers_mod.apply_stage2(agent, base, {
                "paragraphsAppend": [new_para], "gapsRemove": ["role:ramek-chancellor"],
                "searchLog": [{"sourceType": "official", "query": "JACAR", "url": None, "result": "no_result", "note": "x"}]},
                today="2026-11-18")
            self.assertEqual(problems, [])
            self.assertEqual(len(doc["person"]["paragraphs"]), 4)
            self.assertEqual(doc["person"]["paragraphs"][3]["citations"][0]["locator"], old["locator"])
            self.assertEqual(doc["person"]["gaps"], [])
            self.assertEqual(doc["person"]["searchLog"][-1]["round"], "stage2")
            errors, _c, _row = draft_mod.check_person_full(doc, agent["rawDir"])
            self.assertEqual(errors, [])
            _doc, problems = tiers_mod.apply_stage2(agent, base, {"sources": {"wp": {
                "url": "https://en.wikipedia.org/wiki/X", "grade": "C", "gradeBasis": "x"}}})
            self.assertTrue(any("只收 A／B" in p for p in problems))

    def _duan_like(self, base):
        """段祺瑞式：任期只有起日（month），段落寫了中途免職。"""
        person = base["person"]
        cite = dict(person["paragraphs"][0]["citations"][0])
        person["positions"] = [{"key": "war", "title": {"zh-Hant": "國務總理兼陸軍總長", "en": "Premier"},
                                "period": {"start": "1916-04-01", "end": None}, "startPrecision": "month",
                                "endPrecision": None, "positionKind": "executive", "organization": "Test",
                                "citations": [cite]}]
        person["paragraphs"][0]["body"]["zh-Hant"] += "1917年5月23日他被免去總理職務。"
        person["gaps"] = [{"target": "position:war", "status": "待查證", "reason": "缺迄日"}]
        return base

    def test_stage2_refuses_bad_precision_merged_term_and_caps_inferred_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, kind="deep")
            base = self._duan_like(json.loads(person_file.read_text(encoding="utf-8")))
            tele = {"sourceKey": "oebl-ramek", "quote": "Peking, November 21, 1917, 8 p.m."}
            appt = {"sourceKey": "oebl-ramek", "quote": "Wang Shi-chen has been appointed Minister of War"}
            patch = {"positionsUpdate": {"war": {
                "period": {"start": "1916-04-01", "end": "1917-11-21"}, "startPrecision": "day", "endPrecision": "day",
                "evidenceNote": "推論：下一任 1917-11-21 已獲任命", "addCitations": [
                    {"sourceKey": "oebl-ramek", "quote": "Peking, April 24, 1916"}, tele, appt]}},
                "gapsRemove": ["position:war"]}
            doc, problems = tiers_mod.apply_stage2(agent, copy.deepcopy(base), patch)
            unit = doc["person"]["positions"][0]
            self.assertEqual(unit["period"], {"start": "1916-04-01", "end": None})   # 整筆退回
            self.assertEqual(unit["startPrecision"], "month")
            self.assertEqual(len(unit["citations"]), 1)
            self.assertIn("position:war", [g["target"] for g in doc["person"]["gaps"]])
            self.assertTrue(any(p.startswith("REFUSED") and "日精度" in p for p in problems))
            self.assertTrue(any(p.startswith("CAPPED") for p in problems))
            self.assertTrue(any("免職" in p and "1917-05-23" in p for p in problems))
            # 沒有中途免職：推論迄日只封頂到月
            base2 = copy.deepcopy(base)
            base2["person"]["paragraphs"][0]["body"]["zh-Hant"] = base["person"]["paragraphs"][0]["body"]["zh-Hant"].replace(
                "1917年5月23日他被免去總理職務。", "")
            patch2 = {"positionsUpdate": {"war": {"period": {"end": "1917-11-21"}, "endPrecision": "day",
                                                  "evidenceNote": "推論：後任已獲任命", "addCitations": [tele, appt]}},
                      "gapsRemove": ["position:war"]}
            doc2, problems2 = tiers_mod.apply_stage2(agent, base2, copy.deepcopy(patch2))
            unit2 = doc2["person"]["positions"][0]
            self.assertEqual(unit2["period"]["end"], "1917-12-01")   # 下一個月第一天
            self.assertEqual(tiers_mod.next_month_first("1917-12-21"), "1918-01-01")
            self.assertEqual(unit2["endPrecision"], "month")
            self.assertIn("推論上限", unit2["evidenceNote"])
            self.assertNotIn("position:war", [g["target"] for g in doc2["person"]["gaps"]])
            # 引文寫出後任任命那一天：保留 day
            patch2["positionsUpdate"]["war"]["addCitations"] = [
                {"sourceKey": "oebl-ramek", "quote": "On November 21, 1917 Wang Shi-chen was appointed Minister of War"}]
            doc3, _p = tiers_mod.apply_stage2(agent, copy.deepcopy(base2), patch2)
            self.assertEqual(doc3["person"]["positions"][0]["period"]["end"], "1917-11-21")

    def test_term_breaks_and_review_extras(self):
        person = {"paragraphs": [{"ord": 1, "body": {"zh-Hant": "1916年4月他任總理。6月30日總統再度任命他為總理。1917年5月23日他被免去總理職務。他辭職回家。"}}],
                  "positions": [{"key": "pm", "title": {"zh-Hant": "國務總理"}, "period": {"start": "1916-04-01", "end": "1917-11-21"},
                                 "startPrecision": "day", "endPrecision": "day", "evidenceNote": "推論", "citations": []}],
                  "gaps": []}
        hits = c_rules.term_breaks(person, person["positions"][0])
        self.assertEqual([h["date"] for h in hits], ["1916-06-30", "1917-05-23"])
        self.assertEqual(c_rules.term_breaks(person, person["positions"][0], {"start": "1917-06-01", "end": "1917-11-21"}), [])
        self.assertEqual(c_rules.term_breaks(person, {"title": {"zh-Hant": "陸軍總長"}, "period": person["positions"][0]["period"]}), [])
        self.assertEqual(c_rules.term_breaks(person, dict(person["positions"][0], period={"start": "1916-04-01", "end": None})), [])
        self.assertEqual(c_rules.text_dates("The Premier resigned on May 23, 1917.")[0], ["1917-05-23"])
        madsen = {"paragraphs": [{"ord": 5, "body": {"zh-Hant": "1933年8月5日他辭去下院議席，1941年辭去自由黨全國組織主席。"}}]}
        self.assertEqual(c_rules.term_breaks(madsen, {"title": {"zh-Hant": "自由黨全國組織主席"},
                                                      "period": {"start": "1929-01-01", "end": "1942-01-01"}}), [])
        stage1 = copy.deepcopy(person)
        stage1["positions"][0].update(period={"start": "1916-04-01", "end": None}, startPrecision="month", endPrecision=None, evidenceNote=None)
        stage1["gaps"] = [{"target": "position:pm"}]
        ex = tiers_mod.review_extras(person, stage1)
        self.assertEqual(ex["units"][0]["startPrecision"], "day")
        self.assertEqual(len(ex["units"][0]["termBreaks"]), 2)
        joined = "\n".join(ex["stage2Changes"])
        for want in ("startPrecision：month → day", "evidenceNote：None → 推論", "gap 移除 position:pm", "period"):
            self.assertIn(want, joined)
        self.assertEqual(tiers_mod.review_extras(person, None)["stage2Changes"], [])

    def test_sync_gaps_dedupes_and_drops_met_length_gap(self):
        long_body = {"zh-Hant": "甲" * 120}
        person = {"paragraphs": [{"ord": i, "body": long_body} for i in (1, 2, 3)],
                  "gaps": [{"target": "paragraph:length", "note": "篇幅不足：舊"},
                           {"target": "position:x", "note": "待查證：缺迄日"},
                           {"target": "position:x", "note": "待查證：缺起日"},
                           {"target": "position:x", "note": "待查證：缺迄日（新）"}]}
        actions = tiers_mod.sync_gaps(person)
        self.assertEqual([g["note"] for g in person["gaps"]], ["待查證：缺起日", "待查證：缺迄日（新）"])
        self.assertEqual(len(actions), 2)
        short = {"paragraphs": [{"ord": 1, "body": {"zh-Hant": "甲" * 100}}, {"ord": 2, "body": {"zh-Hant": "乙" * 90}}],
                 "gaps": [{"target": "paragraph:length", "note": "篇幅不足：舊"},
                          {"target": "paragraph:length", "note": "篇幅不足：現2段"}]}
        tiers_mod.sync_gaps(short)   # Genden：兩筆篇幅不足留最新的一筆
        self.assertEqual([g["note"] for g in short["gaps"]], ["篇幅不足：現2段"])

    def test_stage2_gap_add_dedupes_and_length_gap_cleared(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, kind="deep")
            base = json.loads(person_file.read_text(encoding="utf-8"))
            base["person"]["gaps"] = [{"target": "role:ramek-chancellor", "note": "待查證：缺迄日"}]
            doc, _p = tiers_mod.apply_stage2(agent, copy.deepcopy(base), {"gapsAdd": [
                {"target": "role:ramek-chancellor", "note": "待查證：缺迄日（查過 3 處）"}]})
            self.assertEqual([g["note"] for g in doc["person"]["gaps"]], ["待查證：缺迄日（查過 3 處）"])
            base["person"]["gaps"].append({"target": "paragraph:length", "note": "篇幅不足：舊"})
            body = base["person"]["paragraphs"][0]["body"]["zh-Hant"]
            if sum(len(p["body"]["zh-Hant"]) for p in base["person"]["paragraphs"]) < 300 or len(base["person"]["paragraphs"]) < 3:
                self.skipTest("fixture 篇幅不足 300 字")
            doc, _p = tiers_mod.apply_stage2(agent, copy.deepcopy(base), {})
            self.assertNotIn("paragraph:length", [g["target"] for g in doc["person"]["gaps"]])
            self.assertTrue(body)

    def test_need_category_and_skip_flag(self):
        self.assertEqual(tiers_mod.need_category(["篇幅（現 1 段／70 字，目標 3 段／300 字）"]), "篇幅不足")
        self.assertEqual(tiers_mod.need_category(["position:a.end（已標待查證）"]), "只缺迄日")
        self.assertEqual(tiers_mod.need_category(["篇幅（現 1 段）", "role:b.end"]), "兩者")
        self.assertIsNone(tiers_mod.need_category(["position:a.start"]))
        on, off = argparse.Namespace(skip_stage2_end_only=True), argparse.Namespace(skip_stage2_end_only=False)
        self.assertTrue(tiers_mod.skips_stage2(on, ["position:a.end（已標待查證）", "position:a.start"]))
        self.assertFalse(tiers_mod.skips_stage2(on, ["篇幅（現 1 段）", "position:a.end"]))
        self.assertFalse(tiers_mod.skips_stage2(off, ["position:a.end"]))
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "results.json"
            f.write_text(json.dumps([{"bioId": "b1"}, {"bioId": "b2"}]), encoding="utf-8")
            self.assertEqual(tiers_mod.done_bios([str(f), str(Path(tmp) / "missing.json")]), {"b1", "b2"})

    def test_partial_usage_cost_and_retry_restore(self):
        loop = load("run_loop", TOOLS / "run_loop.py")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "a.1.jsonl"
            events = [{"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 2, "cache_creation_input_tokens": 1000,
                                                                              "cache_read_input_tokens": 0, "output_tokens": 5}}},
                      {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 2, "cache_creation_input_tokens": 1000,
                                                                              "cache_read_input_tokens": 0, "output_tokens": 50}}},
                      {"type": "assistant", "message": {"id": "m2", "usage": {"input_tokens": 1, "cache_creation_input_tokens": 0,
                                                                              "cache_read_input_tokens": 10000, "output_tokens": 100}}}]
            log.write_text("\n".join(json.dumps(e) for e in events) + "\nnot json\n", encoding="utf-8")
            usage = loop.partial_usage(log)
            self.assertEqual(usage["messages"], 2)
            self.assertEqual(usage["output_tokens"], 150)
            self.assertAlmostEqual(usage["estCostUSD"], round((3 * 2 + 1000 * 4 + 10000 * 0.2 + 150 * 10) / 1e6, 4))
            self.assertIsNone(loop.partial_usage(Path(tmp) / "none.jsonl"))
            cost = tiers_mod.stage_cost([{"modelUsage": None, "partialUsage": usage},
                                         {"modelUsage": {"s": {"costUSD": 0.05}, "h": {"costUSD": 0.01}}}])
            self.assertEqual(cost["actual"], 0.06)
            self.assertEqual(cost["estimatedPartial"], usage["estCostUSD"])
            # 重試前還原：第一輪寫了一半的 stage2.json 移到 .attempt1-partial，person 檔還原
            people = Path(tmp) / "people"
            people.mkdir()
            (people / "b.json").write_text("orig", encoding="utf-8")
            runner = tiers_mod.Runner.__new__(tiers_mod.Runner)
            runner.journal = loop.Journal(Path(tmp) / "logs")
            before = runner.retry_guard({"id": "deep:1:b", "outDir": tmp, "bioId": "b"})
            before(1)
            (people / "b.json").write_text("half", encoding="utf-8")
            (people / "b.stage2.json").write_text("{half", encoding="utf-8")
            before(2)
            self.assertEqual((people / "b.json").read_text(encoding="utf-8"), "orig")
            self.assertFalse((people / "b.stage2.json").exists())
            self.assertEqual((people / "b.stage2.json.attempt1-partial").read_text(encoding="utf-8"), "{half")
            self.assertEqual((people / "b.json.attempt1-partial").read_text(encoding="utf-8"), "half")
            before(3)   # 第二輪什麼都沒寫：不動
            self.assertFalse((people / "b.stage2.json.attempt2-partial").exists())

    def test_uncited_detect_map_finalize(self):
        para = {"ord": 1, "body": {"zh-Hant": "他生於1881年。他是律師。他任總理。", "en": "Born 1881. A lawyer. He was chancellor."},
                "citations": [{"quote": "geb. 1881"}, {"quote": "Rechtsanwalt"}]}
        person = {"paragraphs": [para], "gaps": []}
        found = uncited_mod.find_uncited(person)
        self.assertEqual([i["s"] for i in found], [2, 3])  # 第 1 句靠年份對上
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "p.json"
            f.write_text(json.dumps({"person": person}, ensure_ascii=False), encoding="utf-8")
            out = io_capture(lambda: uncited_mod.cmd_map(str(f), '{"1":{"0":[1],"1":[2]},"drop":{"1":[3]}}'))
            self.assertIn("UNCITED 0", out)
            data = json.loads(f.read_text(encoding="utf-8"))
            self.assertEqual(data["person"]["paragraphs"][0]["body"]["zh-Hant"], "他生於1881年。他是律師。")
            self.assertEqual(data["person"]["paragraphs"][0]["body"]["en"], "Born 1881. A lawyer.")
            self.assertTrue(data["person"]["gaps"][0]["note"].startswith("待補引文：已刪除"))
        # 中英句數不同：不刪，標 待補
        person = {"paragraphs": [{"ord": 2, "body": {"zh-Hant": "甲事。乙事。", "en": "One thing and another."},
                                  "citations": [{"quote": "x", "claimSpan": [1]}]}], "gaps": []}
        removed, marked = uncited_mod.finalize(person)
        self.assertEqual((removed, marked), (0, 1))
        self.assertEqual(person["paragraphs"][0]["pendingCitation"][0]["status"], "待補")
        errors = []
        # 標記與 gap 都讓 verify 照常通過（target 格式 paragraph:<ord>）
        self.assertTrue(re.fullmatch(r"(field:\w+|position:[\w-]+|role:[\w-]+|paragraph:[\w-]+|identity)",
                                     person["gaps"][0]["target"]))

    def test_uncited_legacy_fallback_survives_partial_mapping(self):
        # 補掛一句 claimSpan 之後，其他靠年份推定有出處的舊句子不能變成「沒出處」而被刪
        para = {"ord": 1, "body": {"zh-Hant": "他生於1881年。他是律師。", "en": "Born 1881. A lawyer."},
                "citations": [{"quote": "geb. 1881"}, {"quote": "Rechtsanwalt", "claimSpan": [2]}]}
        self.assertEqual(uncited_mod.find_uncited({"paragraphs": [para]}), [])

    def test_stage2_date_year_must_be_in_quote(self):
        self.assertEqual(tiers_mod.quote_years("陸軍總長 民國6年"), {1917})
        self.assertIn(1918, tiers_mod.quote_years("大正7年9月29日"))
        self.assertIn(1912, tiers_mod.quote_years("大正元年"))
        bad = tiers_mod.date_problems("positionsUpdate:x", {"end": "1918-01-01"}, [{"quote": "陸軍總長 民國6年"}])
        self.assertEqual(len(bad), 1)
        self.assertEqual(tiers_mod.date_problems("positionsUpdate:x", {"end": "1917"}, [{"quote": "陸軍總長 民國6年"}]), [])

    def test_japan_urls_try_new_kanji_on_kotobank(self):
        class Offline:
            offline = True
            cache_dir = Path(tempfile.mkdtemp())
        urls = prefilter.japan_urls(Offline(), ["若槻禮次郎"])
        from urllib.parse import quote as q
        self.assertIn(f"https://kotobank.jp/word/{q('若槻礼次郎')}", urls)

    def test_candidates_include_reeval_and_flagged_ends(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "out"
            (root / "batch901").mkdir(parents=True)
            person = {"key": "p1", "bioId": "b1", "name": "P One", "paragraphs": [{"body": {"zh-Hant": "字" * 320}}] * 3,
                      "positions": [{"key": "x", "period": {"start": "1920-01-01", "end": None}}],
                      "gaps": [{"target": "position:x", "note": "待查證：缺迄日；查過 A"}],
                      "searchLog": [{"result": "blocked_403"}]}
            ok = dict(person, key="p2", bioId="b2", positions=[], gaps=[])
            (root / "batch901" / "research.json").write_text(json.dumps({"people": [person, ok]}), encoding="utf-8")
            reeval = Path(tmp) / "reeval.json"
            reeval.write_text(json.dumps({"people": [{"batch": "777", "key": "z", "bioId": "bz", "name": "Z",
                                                       "missingEnds": [{"field": "position:z.end"}]}]}), encoding="utf-8")
            rows = tiers_mod.candidates(root, reeval)
            self.assertEqual(sorted(r["bioId"] for r in rows), ["b1", "bz"])
            b1 = next(r for r in rows if r["bioId"] == "b1")
            self.assertEqual(b1["fetchFailures"], 1)
            self.assertIn("position:x.end（已標待查證）", b1["needs"])

    def test_tier_profiles_pin_models(self):
        base = {"outDir": str(REPO / "x"), "bioId": "b"}
        for kind, model in (("deep", "sonnet"), ("csupp", "sonnet"), ("citefix", "sonnet"), ("discover", "haiku")):
            prof = specs_mod.launch_profile(dict(base, kind=kind, model="opus" if kind != "discover" else None), REPO)
            self.assertEqual(prof["model"], model)
        self.assertLessEqual(specs_mod.launch_profile(dict(base, kind="citefix"), REPO)["maxTurns"], 3)
        self.assertNotIn("WebSearch", specs_mod.launch_profile(dict(base, kind="csupp"), REPO)["tools"])


class Pilot6FixTests(unittest.TestCase):
    """2026-11-19 pilot5 診斷後的修正：watchdog、壓縮、薄快取、harvest、候選網址關卡、本人語言。"""

    def test_watchdog_ignores_tool_and_assistant_text(self):
        lines = [
            json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "fetch failed ENOTFOUND"}]}}),
            json.dumps({"type": "user", "message": {"content": [{"type": "tool_result", "content": "RESULT=error fetch failed"}]}}),
            json.dumps({"type": "system", "subtype": "api_retry", "error": "ECONNRESET"}),
            "Error: getaddrinfo ENOTFOUND api.anthropic.com",
        ]
        self.assertEqual(loop_mod.net_hits_in("\n".join(lines[:2])), 0)
        self.assertGreaterEqual(loop_mod.net_hits_in("\n".join(lines)), 2)

    def test_decompress_gzip_and_zlib(self):
        import gzip, zlib
        body = "Lázaro Cárdenas 1932".encode()
        self.assertEqual(fetch.decompress(gzip.compress(body)), body)
        self.assertEqual(fetch.decompress(zlib.compress(body)), body)
        self.assertEqual(fetch.decompress(body), body)

    def test_thin_cache_refetches_only_real_short_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            short = Path(tmp) / "a.txt"
            short.write_text("Eduskunta", encoding="utf-8")
            self.assertTrue(fetch.thin_cache(short))
            bot = Path(tmp) / "b.txt"
            bot.write_text("Making sure you're not a bot! Anubis", encoding="utf-8")
            self.assertFalse(fetch.thin_cache(bot))
            login = Path(tmp) / "c.txt"
            login.write_text("403 Forbidden", encoding="utf-8")
            self.assertFalse(fetch.thin_cache(login))
            long = Path(tmp) / "d.txt"
            long.write_text("x" * 800, encoding="utf-8")
            self.assertFalse(fetch.thin_cache(long))

    def test_own_language_native_names(self):
        natives = {"ja": "ラサロ・カルデナス", "zh": "拉萨罗·卡德纳斯", "es": "Lázaro Cárdenas", "ru": "Ласаро Карденас"}
        self.assertEqual(tiers_mod.native_names_for({"key": "mx-cardenas"}, natives), {"es": "Lázaro Cárdenas"})
        self.assertEqual(set(tiers_mod.native_names_for({"key": "cn-song-xilian"}, {"zh": "宋希濂", "ja": "宋希濂"})), {"zh"})
        self.assertEqual(tiers_mod.own_langs({"key": "kung-hsiang-hsi", "name": "Kung Hsiang-hsi", "nameZh": "孔祥熙"}),
                         ["zh-hant", "zh"])
        self.assertIsNone(tiers_mod.own_langs({"key": "zzz", "name": "Somebody"}))

    def test_harvest_host_allowlist(self):
        h = tiers_mod.harvest_host
        self.assertEqual(h("https://www.gob.mx/x")[1], "A")
        self.assertEqual(h("https://historico.colmex.mx/a")[0], "academic")
        self.assertEqual(h("https://www.iranicaonline.org/articles/reza-shah")[1], "B")
        self.assertIsNotNone(h("https://www.deutsche-biographie.de/sfz1.html"))
        self.assertIsNone(h("https://es.wikipedia.org/wiki/L"))
        self.assertIsNone(h("https://www.generals.dk/general/x.html"))
        self.assertIsNone(h("https://viaf.org/viaf/1"))
        self.assertIsNone(h("https://example.com/a"))

    def test_same_site_url_only_switches_to_www(self):
        ok = {"www.iranicaonline.org"}
        url, note = tiers_mod.same_site_url("https://mail.iranicaonline.org/articles/x", lambda h: h in ok)
        self.assertEqual(url, "https://www.iranicaonline.org/articles/x")
        self.assertIn("同站", note)
        url, note = tiers_mod.same_site_url("https://dead.example.org/a", lambda h: False)
        self.assertIsNone(url)
        self.assertIn("dead host", note)

    def _log(self, path, links, query="Lázaro Cárdenas gobernador Michoacán"):
        text = f'Web search results for query: "{query}"\n\nLinks: {json.dumps(links)}\n\nsummary'
        event = {"type": "user", "message": {"content": [{"type": "tool_result", "content": text}]}}
        path.write_text(json.dumps({"type": "assistant", "message": {}}) + "\n" + json.dumps(event) + "\n",
                        encoding="utf-8")

    def test_search_links_and_harvest_fetch_order_and_spacing(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, id="deep:123:bio-ramek", kind="deep")
            logdir = Path(tmp) / "logs"
            logdir.mkdir()
            links = [{"title": "W", "url": "https://es.wikipedia.org/wiki/X"},
                     {"title": "N", "url": "https://paperspast.natlib.govt.nz/n/1"},
                     {"title": "G1", "url": "https://www.gob.mx/a"},
                     {"title": "G2", "url": "https://www.gob.mx/b"},
                     {"title": "U", "url": "https://revistas.unam.mx/c"},
                     {"title": "Z", "url": "https://example.com/z"}]
            self._log(logdir / "deep-123-bio-ramek.1.jsonl", links)
            parsed = tiers_mod.search_links(sorted(logdir.glob("*.jsonl")))
            self.assertEqual(len(parsed), 6)
            self.assertTrue(parsed[0]["query"].startswith("Lázaro"))
            calls, sleeps = [], []

            def fetcher(rawdir, rawmap, key, url, kw, mx):
                calls.append(url)
                Path(rawdir).mkdir(parents=True, exist_ok=True)
                (Path(rawdir) / f"{key}.txt").write_text(f"Rudolf Ramek 1926 Bundeskanzler {url}", encoding="utf-8")
                return "RESULT=fetched\n"
            report = tiers_mod.harvest(agent, logdir, resolves=lambda h: True, fetcher=fetcher, sleep=sleeps.append)
            self.assertEqual(calls, ["https://www.gob.mx/a", "https://www.gob.mx/b", "https://revistas.unam.mx/c"])
            self.assertEqual(len(sleeps), 1)          # 同一 host 第二次才等
            self.assertEqual(report["nonWikiLinks"], 5)
            self.assertEqual([c["status"] for c in report["candidates"]][-1], "not_fetched")
            self.assertTrue((person_file.parent / "bio-ramek.harvest.json").exists())
            self.assertIn("sourceKey=h-www-gob-mx-", tiers_mod.harvest_text(report))
            # 關卡：抓了 3 頁 → 過
            self.assertIsNone(tiers_mod.candidate_gate(agent, {}))
            # harvest 之後又搜 → 要重跑；重跑時已抓的沿用、不重抓，新的才抓
            agent = dict(agent, logDir=str(logdir))
            self._log(logdir / "deep-123-bio-ramek.2.jsonl", [{"title": "D", "url": "https://www.deutsche-biographie.de/x.html"}])
            self.assertIn("HARVEST", tiers_mod.candidate_gate(agent, {}))
            calls.clear()
            report = tiers_mod.harvest(agent, logdir, resolves=lambda h: True, fetcher=fetcher, sleep=sleeps.append)
            self.assertEqual(calls, ["https://www.deutsche-biographie.de/x.html", "https://paperspast.natlib.govt.nz/n/1"])
            self.assertIsNone(tiers_mod.candidate_gate(agent, {}))

    def test_harvest_skips_duplicate_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, id="deep:123:bio-ramek", kind="deep")
            logdir = Path(tmp) / "logs"
            logdir.mkdir()
            self._log(logdir / "deep-123-bio-ramek.1.jsonl", [{"title": t, "url": f"https://www.deutsche-biographie.de/{t}.html"}
                                                              for t in ("a", "b", "c", "d")])

            def fetcher(rawdir, rawmap, key, url, kw, mx):
                Path(rawdir).mkdir(parents=True, exist_ok=True)
                body = "same page" if url.endswith(("a.html", "b.html")) else url
                (Path(rawdir) / f"{key}.txt").write_text(body, encoding="utf-8")
                return "RESULT=fetched\n"
            report = tiers_mod.harvest(agent, logdir, resolves=lambda h: True, fetcher=fetcher, sleep=lambda s: None)
            self.assertEqual([c["status"] for c in report["candidates"]], ["fetched", "skipped", "fetched", "fetched"])

    def test_harvest_stops_on_blocked_host(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, id="deep:123:bio-ramek", kind="deep")
            logdir = Path(tmp) / "logs"
            logdir.mkdir()
            self._log(logdir / "deep-123-bio-ramek.1.jsonl", [{"title": "a", "url": "https://paperspast.natlib.govt.nz/n/1"},
                                                              {"title": "b", "url": "https://paperspast.natlib.govt.nz/n/2"}])
            calls = []

            def fetcher(rawdir, rawmap, key, url, kw, mx):
                calls.append(url)
                return "RESULT=error\nnote=curl: (47) Maximum (50) redirects followed\n"
            report = tiers_mod.harvest(agent, logdir, resolves=lambda h: True, fetcher=fetcher, sleep=lambda s: None)
            self.assertEqual(len(calls), 1)
            self.assertTrue(all(c["status"] == "skipped" and c["reason"] for c in report["candidates"]))
            self.assertIn("blocked_bot_protection", report["candidates"][0]["reason"])

    def test_candidate_gate_requires_handled_urls(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent, spec, person_file = _tier_fixture(Path(tmp))
            agent = dict(agent, kind="deep")
            self.assertIn("HARVEST", tiers_mod.candidate_gate(agent, {}))
            path = person_file.parent / "bio-ramek.harvest.json"
            path.write_text(json.dumps({"nonWikiLinks": 4, "candidates": [
                {"url": "https://a.gob.mx", "status": "skipped", "reason": "dead host（a.gob.mx 解析不到）"}]}),
                encoding="utf-8")
            self.assertIn("FETCH", tiers_mod.candidate_gate(agent, {}))
            self.assertIn("FETCH", tiers_mod.candidate_gate(agent, {"searchLog": [
                {"url": "https://es.wikipedia.org/x", "result": "fetched"}]}))
            self.assertIsNone(tiers_mod.candidate_gate(agent, {"searchLog": [
                {"url": "https://memoria.colmex.mx/x", "result": "skipped:blocked_403 擋頁"}]}))
            path.write_text(json.dumps({"nonWikiLinks": 0, "candidates": []}), encoding="utf-8")
            self.assertIsNone(tiers_mod.candidate_gate(agent, {}))

    def test_harvest_snippets_need_name_and_year(self):
        text = ("Intro. " * 80 + "El general Lázaro Cárdenas fue gobernador de Michoacán hasta 1932. " + "Filler. " * 80 +
                "Lázaro Cárdenas nació en Jiquilpan.")
        out = tiers_mod.harvest_snippets(text, {"Cárdenas"}, set(range(1928, 1949)))
        self.assertEqual(len(out), 1)
        self.assertIn("1932", out[0])
        self.assertEqual(tiers_mod.harvest_snippets(text, {"Cárdenas"}, {1950}), [])

    def test_garbled_pdf_text_detection(self):
        self.assertTrue(fetch.looks_garbled("ab\x01\x02\x03\x04" * 10))
        self.assertFalse(fetch.looks_garbled("Lázaro Cárdenas gobernador 1932.\n" * 10))
        self.assertIsNone(fetch.pdftotext_bin(b"not a pdf"))

    def test_harvest_snippets_rank_post_and_end_words(self):
        text = ("Lazaro Cardenas visitó Morelia en 1930. " + "x " * 300 +
                "En 1932 Lázaro Cárdenas dejó la gubernatura de Michoacán. " + "y " * 300)
        out = tiers_mod.harvest_snippets(text, {"Cárdenas"}, {1930, 1932}, radius=60, posts={"michoaca", "gobernad"})
        self.assertIn("gubernatura", out[0])

    def test_deep_profile_allows_harvest(self):
        prof = specs_mod.launch_profile({"kind": "deep", "batch": "1", "bioId": "b", "outDir": "o", "rawDir": "r",
                                         "specPath": "s", "id": "deep:1:b"}, REPO)
        self.assertTrue(any("tiers.py harvest" in a for a in prof["allowed"]))


class BrowserFetchTests(unittest.TestCase):
    """瀏覽器補抓 pilot（Claude in Chrome）的純 Python 部分。"""

    def setUp(self):
        self.bf = load("browser_fetch", TOOLS / "browser_fetch.py")

    def test_targets_rewrite_ojs_download_and_drop_duplicate_record(self):
        urls = ["https://revistas.inah.gob.mx/index.php/historias/article/download/13794/14885/27495",
                "https://historiamexicana.colmex.mx/index.php/RHM/article/download/1252/2804/3272",
                "https://revistas.colmex.mx/Record/oai:oai.historiamexicana.colmex.mx:article-1252/Description"]
        self.assertEqual(self.bf.browser_targets(urls), [
            "https://revistas.inah.gob.mx/index.php/historias/article/view/13794",
            "https://historiamexicana.colmex.mx/index.php/RHM/article/view/1252"])

    def test_order_by_host_treats_www_as_same_site(self):
        out = self.bf.order_by_host(["https://britannica.com/a", "https://www.britannica.com/b", "https://x.org/c"])
        self.assertEqual(out, ["https://britannica.com/a", "https://x.org/c", "https://www.britannica.com/b"])

    def test_command_is_scoped_and_budgeted(self):
        cmd = self.bf.session_command(["https://x.org/a"], budget=0.5)
        self.assertIn("--strict-mcp-config", cmd)
        self.assertEqual(cmd[cmd.index("--max-budget-usd") + 1], "0.50")
        self.assertEqual(cmd[cmd.index("--model") + 1], "sonnet")
        allowed = cmd[cmd.index("--allowedTools") + 1]
        self.assertIn("browser_batch", allowed)
        self.assertNotIn("computer", allowed)
        self.assertNotIn("javascript", allowed)
        self.assertNotIn("form_input", allowed)

    def _write_log(self, path, events):
        path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")

    def test_parse_log_batch_and_single_calls(self):
        page = "Title: A\nURL: https://www.x.org/a\nSource element: <main>\n---\n" + "Cárdenas 1932 " * 40
        page2 = "Title: B\nURL: https://y.org/b\nSource element: <main>\n---\n" + "texto " * 80
        batch = {"type": "tool_use", "id": "u1", "name": "mcp__claude-in-chrome__browser_batch", "input": {"actions": [
            {"name": "navigate", "input": {"url": "https://x.org/a", "tabId": 1}}, {"name": "get_page_text", "input": {"tabId": 1}},
            {"name": "navigate", "input": {"url": "https://y.org/b", "tabId": 1}}, {"name": "get_page_text", "input": {"tabId": 1}},
            {"name": "navigate", "input": {"url": "https://z.org/c", "tabId": 1}}, {"name": "get_page_text", "input": {"tabId": 1}}]}}
        events = [
            {"type": "system", "message": "init"},
            {"type": "assistant", "message": {"content": [batch]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u1",
                                                       "content": [{"type": "text", "text": page + "\n" + page2}]}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u2", "name": "mcp__claude-in-chrome__navigate",
                                                            "input": {"url": "https://w.org/d"}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "u3",
                                                            "name": "mcp__claude-in-chrome__get_page_text", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "u3", "is_error": True,
                                                       "content": "Can't interact with browser-internal or unparseable URLs."}]}},
            {"type": "result", "result": "OK https://x.org/a\nOK https://y.org/b\nBLOCKED https://z.org/c captcha",
             "total_cost_usd": 0.12, "num_turns": 4, "modelUsage": {"claude-sonnet-5-5": {"inputTokens": 3}}},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "b.jsonl"
            self._write_log(log, events)
            pages, result = self.bf.parse_log(log)
            self.assertEqual([p["url"] for p in pages], ["https://x.org/a", "https://y.org/b", "https://z.org/c", "https://w.org/d"])
            self.assertFalse(pages[0]["toolError"])
            self.assertIn("Cárdenas", pages[0]["text"])
            self.assertTrue(pages[2]["toolError"] and pages[3]["toolError"])
            raw = Path(tmp) / "raw"
            raw.mkdir()
            saved = self.bf.save_pages(pages, result, raw, raw / "rawmap.json", fetch.update_rawmap)
            self.assertEqual([s["status"] for s in saved], ["fetched", "fetched", "blocked", "blocked"])
            meta = json.loads((raw / f"{saved[0]['sourceKey']}.meta.json").read_text(encoding="utf-8"))
            self.assertIn("via", meta)
            self.assertIn(saved[0]["sourceKey"], json.loads((raw / "rawmap.json").read_text(encoding="utf-8")))
            self.assertEqual(self.bf.session_cost(result)["costUSD"], 0.12)

    def test_stop_reason_flags_challenge_login_paywall(self):
        self.assertTrue(self.bf.stop_reason("Please verify you are human " + "x" * 400))
        self.assertTrue(self.bf.stop_reason("Subscribe to continue reading " + "x" * 400))
        self.assertTrue(self.bf.stop_reason("short"))
        self.assertIsNone(self.bf.stop_reason("Lázaro Cárdenas fue gobernador de Michoacán. " * 20))

    def test_batch_partial_failure_marks_that_page(self):
        actions = [{"name": "navigate", "input": {"url": "https://a.org/1"}}, {"name": "get_page_text", "input": {}},
                   {"name": "navigate", "input": {"url": "https://b.org/2"}}, {"name": "get_page_text", "input": {}}]
        text = ("[navigate] Navigated to https://a.org/1\n\nactions[1] (get_page_text) failed: Permission denied for reading "
                "page content on this domain (1 completed, 2 remaining)")
        pages = self.bf.split_batch(actions, text, True)
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["url"], "https://a.org/1")
        self.assertIn("Permission denied", pages[0]["text"])
        self.assertTrue(self.bf.stop_reason("historiamexicana.colmex.mx 正在執行安全驗證 此網站使用安全服務抵禦惡意機器人。" * 3))

    def test_tab_context_trailer_is_not_saved(self):
        text = "Title: A\nURL: https://a.org\n---\nBody text\n\n\nTab Context:\n- Executed on tabId: 1\n"
        self.assertEqual(self.bf.strip_tab_context(text), "Title: A\nURL: https://a.org\n---\nBody text")

    def test_pdf_like_urls_are_not_opened(self):
        for url in ("https://ru.dgb.unam.mx/bitstream/20.500/x/0694033.pdf", "https://www.gob.mx/cms/uploads/attachment/file/1/x",
                    "https://a.org/files/report.PDF", "https://a.org/index.php/j/article/download/1/2/3"):
            self.assertTrue(self.bf.pdf_like(url), url)
        self.assertFalse(self.bf.pdf_like("https://revistas.inah.gob.mx/index.php/historias/article/view/13794"))
        self.assertFalse(self.bf.pdf_like("https://www.britannica.com/topic/Persian-Cossack-Brigade"))

    def test_usage_limit_text_detected(self):
        self.assertTrue(self.bf.limit_text("You've hit your 5-hour limit · resets 2:20am (Asia/Taipei)"))
        self.assertFalse(self.bf.limit_text("OK https://a.org"))
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "x.jsonl"
            log.write_text(json.dumps({"type": "result", "result": "You've hit your 5-hour limit · resets 2:20am"}), encoding="utf-8")
            self.assertTrue(tiers_mod.usage_limited(log))

    def test_connected_devices_parses_bridge_list(self):
        class P:
            stdout = json.dumps({"result": '[{"deviceId":"ef982cf7-0626","name":"Browser 1"}]', "total_cost_usd": 0.006})
        devices, cost, limited = self.bf.connected_devices(runner=lambda *a, **k: P())
        self.assertEqual([d["deviceId"] for d in devices], ["ef982cf7-0626"])
        self.assertFalse(limited)
        self.assertAlmostEqual(cost, 0.006)

    def test_pinned_browser_device_problem(self):
        bf = load("browser_fetch", TOOLS / "browser_fetch.py")
        pin, other = "44c34180-5202-4f69-9685-907c6a3ea7e2", "b7dfec23-2297-467e-92cd-7a67cbb2226e"
        with tempfile.TemporaryDirectory() as tmp:
            log, dbg = Path(tmp) / "c.jsonl", Path(tmp) / "c.debug.txt"
            def write(first_name, first_input, reply, routed):
                ev = [{"type": "assistant", "message": {"content": [
                          {"type": "tool_use", "id": "t1", "name": "mcp__claude-in-chrome__" + first_name, "input": first_input}]}},
                      {"type": "user", "message": {"content": [
                          {"type": "tool_result", "tool_use_id": "t1", "content": [{"type": "text", "text": reply}]}]}}]
                log.write_text("\n".join(json.dumps(e) for e in ev), encoding="utf-8")
                dbg.write_text("".join(f'x {{"type":"routing_ack","routed_to":"{d}"}}\n' for d in routed), encoding="utf-8")
            write("select_browser", {"deviceId": pin}, 'Selected browser "Browser 2".', [pin, pin])
            self.assertIsNone(bf.device_problem(log, dbg, pin))
            write("select_browser", {"deviceId": pin}, 'Selected browser "Browser 2".', [pin, other])
            self.assertEqual(bf.device_problem(log, dbg, pin), f"routed-to:{other}")
            write("navigate", {"url": "https://example.com"}, "Navigated", [other])
            self.assertEqual(bf.device_problem(log, dbg, pin), "first-tool-not-select")
            write("select_browser", {"deviceId": pin}, "No browser with that id", [])
            self.assertEqual(bf.device_problem(log, dbg, pin), "select-failed")
        cmd = bf.session_command(["https://example.com"], device=pin, debug_file="/tmp/d.txt")
        self.assertIn("mcp__claude-in-chrome__select_browser", cmd[cmd.index("--allowedTools") + 1])
        self.assertIn("--debug-file", cmd)
        self.assertIn(pin, cmd[-1])
        self.assertNotIn("select_browser", bf.session_command(["https://example.com"])[
            bf.session_command(["https://example.com"]).index("--allowedTools") + 1])

    def test_term_break_ignores_final_month_of_month_precision_end(self):
        tiers = tiers_mod
        unit = {"period": {"start": "1931-11-01", "end": "1932-01-01"}, "endPrecision": "month"}
        self.assertTrue(tiers.in_final_unit("1931-12-01", unit))
        self.assertFalse(tiers.in_final_unit("1931-11-15", unit))
        unit = {"period": {"start": "1927-01-01", "end": "1930-01-01"}, "endPrecision": "year"}
        self.assertTrue(tiers.in_final_unit("1929-06-01", unit))
        self.assertFalse(tiers.in_final_unit("1928-06-01", unit))
        self.assertFalse(tiers.in_final_unit("1929-12-01", {"period": {"end": "1930-01-01"}, "endPrecision": "day"}))

    def test_browser_missing_stops_run(self):
        tiers = tiers_mod
        class Args: pass
        runner = tiers.Runner.__new__(tiers.Runner)
        runner.results = []
        with tempfile.TemporaryDirectory() as tmp:
            class J: dir = Path(tmp)
            runner.journal = J()
            calls = []
            def one(nn, bio):
                calls.append(bio)
                raise tiers.BrowserMissing("device-missing:" + bio)
            runner.one = one
            out = runner.run(["106:a", "107:b"])
        self.assertEqual(calls, ["a"])
        self.assertEqual(out[0]["outcome"], "browser-missing-stop")

    def test_log_parsers_tolerate_string_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "deep-1-b.1.jsonl"
            log.write_text("\n".join([
                json.dumps({"type": "system", "subtype": "permission_denied", "message": "Permission to use Bash has been denied"}),
                json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "a", "name": "WebSearch", "input": {}}]}}),
            ]) + "\n", encoding="utf-8")
            self.assertEqual(tiers_mod.tool_counts(log).get("WebSearch"), 1)
            self.assertEqual(tiers_mod.search_links([log]), [])

    def test_inah_graded_by_longest_suffix(self):
        self.assertEqual(tiers_mod.harvest_host("https://revistas.inah.gob.mx/x")[:2], ("academic", "B"))
        self.assertEqual(tiers_mod.harvest_host("https://www.gob.mx/x")[1], "A")


if __name__ == "__main__":
    unittest.main()
