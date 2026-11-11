import importlib.util, json, os, unittest

spec = importlib.util.spec_from_file_location("wb3", os.path.join(os.path.dirname(os.path.abspath(__file__)), "write_b3_paragraphs.py"))
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class Transforms(unittest.TestCase):
    def test_field_alias(self):
        self.assertEqual(w.norm_field_target("field:birth_date"), ("field:birthDate", True))
        self.assertEqual(w.norm_field_target("field:death_date"), ("field:deathDate", True))
        self.assertEqual(w.norm_field_target("field:birthDate"), ("field:birthDate", False))

    def test_field_not_in_seed_only(self):
        for t in ("field:recordIds", "field:positions", "field:biography"):
            self.assertEqual(w.norm_field_target(t), (None, False))

    def test_other_targets_pass(self):
        self.assertEqual(w.norm_field_target("position:presidency-1923")[0], "position:presidency-1923")
        self.assertEqual(w.norm_field_target("identity")[0], "identity")
        self.assertEqual(w.norm_field_target("paragraph:xx")[0], "paragraph:xx")
        self.assertIsNone(w.norm_field_target("position: bad")[0])
        self.assertIsNone(w.norm_field_target("paragraph:" + "x" * 60)[0])

    def test_claim_span_merge(self):
        self.assertEqual(w.merge_claim_span(None, "支撐『對德協議』"), ("支撐『對德協議』", True))
        self.assertEqual(w.merge_claim_span("只寫年份", "支撐A"), ("只寫年份；支撐A", True))
        self.assertEqual(w.merge_claim_span("x", None), ("x", False))
        with self.assertRaises(ValueError):
            w.merge_claim_span(None, [1, 2])

    def test_period(self):
        self.assertEqual(w.period_literal({"start": "1900-01-01", "end": None}), "[1900-01-01,)")
        self.assertEqual(w.period_literal({"start": "1900-01-01", "end": "1901-01-01"}), "[1900-01-01,1901-01-01)")
        self.assertIsNone(w.period_literal({"start": None, "end": "1930-12-17"}))
        with self.assertRaises(ValueError):
            w.period_literal({"start": "1901-01-01", "end": "1900-01-01"})

    def test_skip_zero_paragraph_people(self):
        self.assertEqual(w.SKIP_PEOPLE, {"pe-schreiber", "es-allendesalazar"})

    def test_role_layer_kinds_not_positions(self):
        self.assertFalse(w.ROLE_LAYER & w.POSITION_KINDS)
        self.assertIn("cabinet_minister", w.ROLE_KINDS)


class RoleConflict(unittest.TestCase):
    rec = [{"role": "head_of_government", "start": "1933-10-26", "end": "1933-11-26", "regime": "r"}]

    def cand(self, kind, s, e, reason=""):
        return {"role_kind": kind, "period": {"start": s, "end": e}, "reason": reason}

    def test_same_role_overlap_is_conflict(self):
        v, why, hits = w.classify_role(self.cand("head_of_government", "1933-11-01", "1934-01-01"), self.rec)
        self.assertEqual(v, "conflict"); self.assertIn("重複", why); self.assertEqual(len(hits), 1)

    def test_different_role_overlap_is_released(self):
        v, why, hits = w.classify_role(self.cand("de_facto_leader", "1930-01-01", None), self.rec)
        self.assertEqual(v, "ok"); self.assertIn("放行", why); self.assertEqual(len(hits), 1)

    def test_no_overlap_has_empty_reason(self):
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01"), self.rec), ("ok", "", []))

    def test_no_overlap_ok_without_records_or_overlap(self):
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01"), [])[0], "ok")
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01"), self.rec)[0], "ok")

    def test_pending_when_seed_says_to_compare(self):
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01", "待比對名單"), self.rec)[0], "pending")

    def test_half_open_touching_is_not_overlap(self):
        self.assertFalse(w.periods_overlap(("1900-01-01", "1901-01-01"), ("1901-01-01", None)))


class MissingStart(unittest.TestCase):
    def test_detects_missing_start(self):
        for p in (None, {}, {"start": None, "end": "1930-01-01"}, {"start": ""}):
            self.assertTrue(w.missing_start({"period": p}))
        self.assertFalse(w.missing_start({"period": {"start": "1900-01-01"}}))
        self.assertTrue(w.missing_start({}))

    def test_gap_for_position_and_role(self):
        g = w.missing_start_gap("b1", "position", {"key": "p-1", "title": {"orig": "外交部長"}, "period": {"start": None, "end": "1930-12-17"}})
        self.assertEqual((g["target"], g["kind"], g["cand"]), ("position:p-1", "not_found", []))
        self.assertIn("缺 period.start", g["note"]); self.assertIn("外交部長", g["note"]); self.assertIn("1930-12-17", g["note"])
        r = w.missing_start_gap("b1", "role", {"key": "r-1", "title": {"zh-Hant": "首相"}, "period": None})
        self.assertEqual(r["target"], "role:r-1")

    def test_role_target_normalizes_and_bad_key_rejected(self):
        self.assertEqual(w.norm_field_target("role:cn-x-1"), ("role:cn-x-1", False))
        self.assertIsNone(w.missing_start_gap("b1", "role", {"key": " lead-space", "title": {}, "period": None}))
        self.assertIsNone(w.missing_start_gap("b1", "role", {"key": "x" * 70, "title": {}, "period": None}))


class SourceKind(unittest.TestCase):
    def test_domains(self):
        self.assertEqual(w.guess_kind("https://www.encyclopedia.com/x"), "encyclopedia")
        self.assertEqual(w.guess_kind("https://www.senat.fr/x"), "official_website")
        self.assertIsNone(w.guess_kind("https://rulers.org/x"))
        self.assertEqual(w.guess_kind("https://rulers.org/x", {"rulers.org": "dataset"}), "dataset")

    def test_archive_kind_accepted_and_overridden(self):
        self.assertIn("archive", w.SOURCE_KINDS)
        self.assertEqual(w.guess_kind("https://hemerotecadigital.cm-lisboa.pt/x", {"hemerotecadigital.cm-lisboa.pt": "archive"}), "archive")
        ov = json.load(open(w.OVERRIDES))
        self.assertEqual(ov["hemerotecadigital.cm-lisboa.pt"], "archive")
        self.assertTrue(all(v is None or v == "drop" or v in w.SOURCE_KINDS for v in ov.values()))

    def test_override_drop(self):
        for v in (None, "drop"):
            self.assertEqual(w.guess_kind("https://p.example/x", {"p.example": v}), w.DROP)
        # URL 鍵優先於網域鍵
        ov = {"real.example": "peer_reviewed", "https://real.example/a": "official_history", "https://real.example/b": None}
        self.assertEqual(w.guess_kind("https://real.example/a", ov), "official_history")
        self.assertEqual(w.guess_kind("https://real.example/b", ov), w.DROP)
        self.assertEqual(w.guess_kind("https://real.example/c", ov), "peer_reviewed")

    def test_dropped_source_is_not_unclassified_and_cite_dropped(self):
        st = {"sources": {}, "bios": {"B"}, "regimes": set(), "existing": {"paragraphs": set(), "positions": set(), "roles": set()}, "records": {}}
        d = {"sources": {"s": {"url": "https://me.example/x", "title": "t", "publisher": "p"}}, "people": [{
            "key": "k", "bioId": "B", "positions": [], "roleCandidates": [], "gaps": [],
            "paragraphs": [{"ord": 1, "body": {"en": "x"}, "citations": [{"sourceKey": "s", "locator": "l", "quote": "q", "accessedOn": "2026-01-01"}]}]}]}
        P = w.plan([("b", d)], st, {"me.example": None})
        self.assertEqual((P["unclassified"], list(P["sources_dropped"]), P["sources_new"]), ({}, ["https://me.example/x"], {}))
        self.assertEqual(len(P["par"][0]["cit"]), 0)

    def test_plan_routes_missing_start_to_gaps_and_releases_role(self):
        st = {"sources": {}, "bios": {"B"}, "regimes": set(), "existing": {"paragraphs": set(), "positions": set(), "roles": set()},
              "records": {"B": [{"role": "head_of_state", "start": "1920-01-01", "end": "1925-01-01", "regime": "r"}]}}
        d = {"sources": {}, "people": [{"key": "k", "bioId": "B", "paragraphs": [{"ord": 1, "body": {"en": "x"}}], "gaps": [],
            "positions": [{"key": "p1", "positionKind": "minister", "title": {"orig": "部長"}, "period": {"start": None, "end": "1930-01-01"}}],
            "roleCandidates": [
                {"key": "r1", "role_kind": "head_of_state", "title": {"orig": "x"}, "period": None},
                {"key": "r2", "role_kind": "head_of_state", "title": {"orig": "x"}, "period": {"start": "1921-01-01", "end": "1922-01-01"}},
                {"key": "r3", "role_kind": "de_facto_leader", "title": {"orig": "x"}, "period": {"start": "1921-01-01", "end": "1922-01-01"}}]}]}
        P = w.plan([("b", d)], st, {})
        self.assertEqual(sorted(g["target"] for g in P["gaps"]), ["position:p1", "role:r1"])
        self.assertEqual((len(P["pos"]), len(P["bad"]), len(P["nostart"])), (0, 0, 2))
        self.assertEqual([r["key"] for r in P["role_ok"]], ["r3"])
        self.assertEqual([r["key"] for r in P["role_conflict"]], ["r2"])


class Safety(unittest.TestCase):
    def test_write_disabled(self):
        self.assertIs(w.WRITE_ENABLED, False)

    def test_write_needs_explicit_flag(self):
        self.assertFalse(w.write_allowed(False))
        self.assertTrue(w.write_allowed(True))


class Sql(unittest.TestCase):
    def test_quote(self):
        self.assertEqual(w.sql_lit("O'Brien"), "'O''Brien'")
        self.assertEqual(w.sql_lit(None), "NULL")


if __name__ == "__main__":
    unittest.main()
