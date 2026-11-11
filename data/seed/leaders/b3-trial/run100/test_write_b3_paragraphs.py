import importlib.util, os, unittest

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

    def test_different_role_overlap_is_conflict(self):
        self.assertEqual(w.classify_role(self.cand("de_facto_leader", "1930-01-01", None), self.rec)[0], "conflict")

    def test_no_overlap_ok_without_records_or_overlap(self):
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01"), [])[0], "ok")
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01"), self.rec)[0], "ok")

    def test_pending_when_seed_says_to_compare(self):
        self.assertEqual(w.classify_role(self.cand("head_of_state", "1900-01-01", "1901-01-01", "待比對名單"), self.rec)[0], "pending")

    def test_half_open_touching_is_not_overlap(self):
        self.assertFalse(w.periods_overlap(("1900-01-01", "1901-01-01"), ("1901-01-01", None)))


class SourceKind(unittest.TestCase):
    def test_domains(self):
        self.assertEqual(w.guess_kind("https://www.encyclopedia.com/x"), "encyclopedia")
        self.assertEqual(w.guess_kind("https://www.senat.fr/x"), "official_website")
        self.assertIsNone(w.guess_kind("https://rulers.org/x"))
        self.assertEqual(w.guess_kind("https://rulers.org/x", {"rulers.org": "dataset"}), "dataset")


class Sql(unittest.TestCase):
    def test_quote(self):
        self.assertEqual(w.sql_lit("O'Brien"), "'O''Brien'")
        self.assertEqual(w.sql_lit(None), "NULL")


if __name__ == "__main__":
    unittest.main()
