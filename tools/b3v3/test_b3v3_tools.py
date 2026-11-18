#!/usr/bin/env python3
"""B3 v3 省 token 工具的離線測試。不連外網。"""
import importlib.util
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
            (raw / "demo.txt").write_text("Johannes Schober war Bundeskanzler 1921.", encoding="utf-8")
            rawmap = raw / "rawmap.json"
            rawmap.write_text('{"demo": "demo.txt"}\n', encoding="utf-8")
            out = fetch.cmd_fetch(raw, rawmap, "demo", "http://127.0.0.1:9/unused", ["Schober"], 2000)
            self.assertIn("RESULT=cached", out)
            self.assertIn("offset=", out)
            self.assertNotIn("RESULT=fetched", out)

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
        self.assertEqual(
            [person["name"] for person in by_nn["095"]["shortfall"]],
            ["Rafael Reyes Prieto", "Teleki Pál", "Hermann Rauschning"],
        )
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


if __name__ == "__main__":
    unittest.main()
