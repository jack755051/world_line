#!/usr/bin/env python3
"""B3 v3 省 token 工具的離線測試。不連外網。"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
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


class PlanTests(unittest.TestCase):
    def test_resume_plan_matches_recomputed_list(self):
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
        self.assertIn("Johannes Schober", [person["name"] for person in by_nn["122"]["retrySkipped"]])
        self.assertEqual(
            [person["name"] for person in by_nn["094"]["retry"]["people"]],
            ["Milan Hodža"],
        )
        fields = by_nn["094"]["retry"]["people"][0]["missingFields"]
        self.assertEqual(fields[0]["field"], "role:hodza-sns-1906.end")
        self.assertTrue(fields[0]["fixable"])
        self.assertEqual(by_nn["095"]["retry"]["mode"], "none")
        self.assertEqual(
            [person["name"] for person in by_nn["095"]["shortfall"]],
            ["Rafael Reyes Prieto", "Teleki Pál", "Hermann Rauschning"],
        )
        self.assertTrue(by_nn["096"]["recheck"])
        self.assertFalse(by_nn["096"]["research"])
        fresh = plan.recompute_chunk(REPO / "data/seed/leaders/b3-trial/full/v3")
        on_disk = json.loads((REPO / ".dev/b3v3/partial/chunk4-remaining.json").read_text(encoding="utf-8"))
        for key in (
            "reviewed", "needs_retry_and_review", "shortfall_review", "needs_review_only",
            "retryDone", "recheck_review", "needs_research",
        ):
            self.assertEqual(on_disk[key], fresh[key], key)
        self.assertEqual(fresh["counts"]["retryPeople"], 16)
        self.assertEqual(fresh["counts"]["shortfallPeople"], 12)
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

    def test_dry_run_chunk4_models_and_counts(self):
        proc = subprocess.run(
            [sys.executable, "-I", str(TOOLS / "run_chunk.py"), "dry-run",
             "--repo", str(REPO),
             "--prompt-dir", ".dev/b3v3/prompts",
             "--out-root", "data/seed/leaders/b3-trial/full/v3",
             "--raw-root", "/tmp/b3-raw",
             "--resume", ".dev/b3v3/partial/chunk4-remaining.json",
             "--concurrency", "3", "--json"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        data = json.loads(proc.stdout)
        self.assertEqual(data["researchAgents"], 0)
        self.assertEqual(data["retryAgents"], 16)
        self.assertEqual(data["reviewAgents"], 75)
        self.assertEqual(data["reviewModels"], {"sonnet": 72, "opus": 3})
        self.assertEqual(data["shortfallPeople"], 12)
        opus = [
            agent for wave in data["waves"] if wave["phase"] == "review"
            for agent in wave["agents"] if agent["model"] == "opus"
        ]
        self.assertEqual(sorted(agent["batch"] for agent in opus), ["122", "122", "122"])
        self.assertNotIn("prompt", json.dumps(data["waves"][0]["agents"][0]))

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


if __name__ == "__main__":
    unittest.main()
