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
            self.assertTrue(pack["claims"][0]["verify"]["ok"])
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
            extracted = people / "again.json"
            merge.extract(research, "bio-1", extracted)
            self.assertEqual(json.loads(extracted.read_text(encoding="utf-8"))["person"]["bioId"], "bio-1")
            self.assertEqual(proc.returncode in (0, 1), True)

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
        self.assertEqual(data["batchCount"], 27)
        by_nn = {item["nn"]: item for item in data["batches"]}
        self.assertNotIn("097", by_nn)
        self.assertNotIn("098", by_nn)
        self.assertNotIn("100", by_nn)
        self.assertTrue(by_nn["122"]["research"])
        self.assertFalse(by_nn["093"]["research"])
        self.assertEqual(
            [person["name"] for person in by_nn["093"]["retry"]["people"]],
            ["Alexandru Averescu", "José Félix Uriburu"],
        )
        self.assertEqual(by_nn["105"]["retry"]["mode"], "none")
        self.assertTrue(by_nn["096"]["recheck"])
        self.assertFalse(by_nn["096"]["research"])
        trial = subprocess.run(
            [sys.executable, "-I", str(TOOLS / "plan_work.py"),
             "--repo", str(REPO),
             "--prompt-dir", ".dev/b3v3/prompts",
             "--out-root", "data/seed/leaders/b3-trial/full/v3",
             "--raw-root", "/tmp/b3-raw",
             "--resume", ".dev/b3v3/partial/chunk4-remaining.json",
             "--chunk", "122,093,105", "--limit", "3"],
            capture_output=True, text=True, cwd=REPO,
        )
        self.assertEqual(trial.returncode, 0, trial.stderr)
        trial_nns = [item["nn"] for item in json.loads(trial.stdout)["batches"]]
        self.assertEqual(trial_nns, ["122", "093", "105"])

    def test_prompt_patch_is_idempotent_on_disk(self):
        sample = (REPO / ".dev/b3v3/prompts/research-093.md").read_text(encoding="utf-8")
        self.assertIn("tools/b3v3/fetch_source.py", sample)
        self.assertNotIn("curl -sSL", sample)
        again, notes = patch.patch_text("research-093.md", sample)
        self.assertEqual(again, sample)
        self.assertEqual(notes, [])
        review = (REPO / ".dev/b3v3/prompts/review-096.md").read_text(encoding="utf-8")
        self.assertIn("evidence-pack.json", review)
        self.assertNotIn("每人至少抽 1 個來源重抓", review)
        self.assertNotIn("raw/*.txt", review)


if __name__ == "__main__":
    unittest.main()
