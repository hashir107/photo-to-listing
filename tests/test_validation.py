"""Automated schema, rule and skill-format tests. Run: python3 -m unittest discover -s tests"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import minischema  # noqa: E402
import validate  # noqa: E402


def load_cases():
    return json.loads((validate.SKILL_DIR / "examples" / "cases.json").read_text(encoding="utf-8"))


def case_output(case_id, turn=0):
    for case in load_cases()["cases"]:
        if case["id"] == case_id:
            return copy.deepcopy(case["turns"][turn]["expected_output"])
    raise KeyError(case_id)


class SourceChecks(unittest.TestCase):
    def test_version_and_changelog(self):
        self.assertEqual(validate.check_version(validate.read_version()), [])

    def test_skill_md_follows_spec(self):
        self.assertEqual(validate.check_skill_dir(validate.SKILL_DIR, validate.read_version()), [])

    def test_schema_is_valid(self):
        self.assertEqual(validate.check_schema_file(validate.load_schema()), [])

    def test_examples_are_valid(self):
        self.assertEqual(validate.check_examples(validate.load_schema()), [])

    def test_packaging_config(self):
        self.assertEqual(validate.check_packaging(), [])

    def test_no_secrets_or_private_files(self):
        self.assertEqual(validate.check_hygiene(), [])

    def test_required_cases_present(self):
        ids = {c["id"] for c in load_cases()["cases"]}
        for required in ("unreadable-label", "multi-turn-functionality", "prompt-injection-in-image",
                         "no-image-access", "conflicting-note-and-label", "json-only"):
            self.assertIn(required, ids)


class SchemaNegatives(unittest.TestCase):
    """Mutations of a valid document that must be rejected."""

    def setUp(self):
        self.schema = validate.load_schema()
        self.doc = case_output("monitor-batch")
        self.assertEqual(minischema.validate(self.doc, self.schema), [])
        self.assertEqual(validate.semantic_errors(self.doc), [])

    def schema_errors(self, doc):
        return minischema.validate(doc, self.schema)

    def test_price_field_rejected(self):
        self.doc["price"] = 50
        self.assertTrue(any("unexpected property 'price'" in e for e in self.schema_errors(self.doc)))

    def test_missing_required_field_rejected(self):
        del self.doc["unknowns"]
        self.assertTrue(self.schema_errors(self.doc))

    def test_unknown_condition_must_be_null_not_string(self):
        self.doc["physical_condition"] = "unknown"
        self.assertTrue(self.schema_errors(self.doc))
        self.doc["physical_condition"] = None
        self.doc["functional_status"] = "unknown"
        self.assertTrue(self.schema_errors(self.doc))

    def test_sale_configuration_uses_explicit_unknown(self):
        self.doc["sale_configuration"] = None
        self.assertTrue(self.schema_errors(self.doc))

    def test_placeholder_text_rejected(self):
        self.doc["model"] = "unknown"
        self.assertTrue(any("placeholder" in e for e in validate.semantic_errors(self.doc)))

    def test_quantity_must_be_positive_integer(self):
        for bad in (0, 2.5, "24", True):
            doc = copy.deepcopy(self.doc)
            doc["quantity"] = bad
            self.assertTrue(self.schema_errors(doc), bad)

    def test_more_than_three_questions_rejected(self):
        extra = copy.deepcopy(self.doc["clarification_questions"][0])
        extra["id"] = "q_4"
        self.doc["clarification_questions"].append(extra)
        self.assertTrue(any("more than 3" in e for e in self.schema_errors(self.doc)))

    def test_url_photo_ref_rejected(self):
        self.doc["photos"][0]["ref"] = "https://files.example/abc.jpg?sig=x"
        self.assertTrue(self.schema_errors(self.doc))

    def test_bad_certainty_rejected(self):
        self.doc["evidence"][0]["certainty"] = "0.9"
        self.assertTrue(self.schema_errors(self.doc))

    def test_title_over_kleinanzeigen_limit_rejected(self):
        self.doc["listing_title"] = "x" * 65
        self.assertEqual(self.schema_errors(self.doc), [])
        self.doc["listing_title"] = "x" * 66
        self.assertTrue(any("longer than 65" in e for e in self.schema_errors(self.doc)))
        self.doc["listing_title"] = "ok"
        self.doc["listing_translations"]["en"]["title"] = "x" * 66
        self.assertTrue(self.schema_errors(self.doc))

    def test_description_over_kleinanzeigen_limit_rejected(self):
        self.doc["listing_description"] = "x" * 4001
        self.assertTrue(any("longer than 4000" in e for e in self.schema_errors(self.doc)))

    def test_more_than_twenty_upload_photos_rejected(self):
        self.doc["photo_upload_order"] = [{"ref": f"photo_{i}", "note": None} for i in range(21)]
        self.assertTrue(any("more than 20" in e for e in self.schema_errors(self.doc)))


class RuleNegatives(unittest.TestCase):
    """Integrity rules beyond JSON Schema (see references/extraction-rules.md)."""

    def setUp(self):
        self.doc = case_output("monitor-batch")

    def errors(self):
        return validate.semantic_errors(self.doc)

    def test_dangling_evidence_ref(self):
        self.doc["attributes"][0]["evidence_refs"] = ["ev_99"]
        self.assertTrue(any("ev_99" in e for e in self.errors()))

    def test_field_path_must_resolve(self):
        self.doc["evidence"][0]["field_path"] = "/attributes/7"
        self.assertTrue(any("does not resolve" in e for e in self.errors()))

    def test_duplicate_evidence_id(self):
        self.doc["evidence"][1]["id"] = "ev_1"
        self.assertTrue(any("not unique" in e for e in self.errors()))

    def test_model_requires_supported_evidence(self):
        self.doc["model"] = "24MK430H"
        self.assertTrue(any("/model is set without supported evidence" in e for e in self.errors()))

    def test_tentative_evidence_is_not_enough_for_brand(self):
        for e in self.doc["evidence"]:
            if e["field_path"] == "/brand":
                e["certainty"] = "tentative"
        self.assertTrue(any("/brand" in e for e in self.errors()))

    def test_function_not_established_by_photo_alone(self):
        self.doc["functional_status"] = "working"
        self.assertTrue(any("photos alone" in e for e in self.errors()))

    def test_mixed_requires_differing_units(self):
        self.doc["functional_status"] = "mixed"
        self.doc["evidence"].append({"id": "ev_11", "field_path": "/functional_status", "source": "user_statement",
                                     "photo_ref": None, "observation": "User: some work.", "url": None,
                                     "certainty": "supported", "user_confirmation": "none"})
        self.assertTrue(any("'mixed'" in e for e in self.errors()))

    def test_visual_evidence_needs_inspected_photo(self):
        self.doc["photos"][1]["inspected"] = False
        self.assertTrue(any("inspected photo_ref" in e for e in self.errors()))

    def test_external_reference_needs_url(self):
        self.doc["evidence"][0]["source"] = "external_reference"
        self.assertTrue(any("url is required" in e for e in self.errors()))

    def test_price_in_listing_rejected(self):
        self.doc["listing_description"] += "\nPreis: 50 € VB"
        self.assertTrue(any("price" in e for e in self.errors()))

    def price_ev(self, eid, source, certainty, url=None):
        self.doc["evidence"].append({"id": eid, "field_path": "/price_estimate", "source": source, "photo_ref": None,
                                     "observation": "Price basis.", "url": url, "certainty": certainty,
                                     "user_confirmation": "none"})

    def estimate(self):
        """Opt the monitor doc in to a valid model-knowledge price."""
        self.price_ev("ev_19", "inference", "tentative")
        self.doc["price_status"] = "estimated"
        self.doc["price_estimate"] = {"currency": "EUR", "scope": "per_unit", "low": 25, "high": 50, "suggested": 35,
                                      "lot_total_suggested": 630, "basis": "model_knowledge",
                                      "assumptions": ["Ungeprüft."], "evidence_refs": ["ev_19"]}
        self.assertEqual(self.errors(), [])

    def test_offered_by_default_without_price(self):
        self.assertEqual(self.doc["price_status"], "offered")
        self.assertIsNone(self.doc["price_estimate"])

    def test_price_only_when_estimated(self):
        self.estimate()
        for status in ("offered", "declined", "not_applicable"):
            self.doc["price_status"] = status
            self.assertTrue(any("exactly when price_status" in e for e in self.errors()), status)

    def test_estimated_status_needs_a_price(self):
        self.doc["price_status"] = "estimated"
        self.assertTrue(any("exactly when price_status" in e for e in self.errors()))

    def test_unknown_price_status_rejected(self):
        self.doc["price_status"] = "maybe"
        self.assertTrue(minischema.validate(self.doc, validate.load_schema()))

    def test_price_range_must_be_ordered(self):
        self.estimate()
        self.doc["price_estimate"]["low"] = 60
        self.assertTrue(any("low <= suggested <= high" in e for e in self.errors()))

    def test_reference_new_price_needs_cited_url(self):
        self.estimate()
        self.price_ev("ev_20", "inference", "tentative")
        self.doc["price_estimate"].update(basis="reference_new_price", evidence_refs=["ev_20"])
        self.assertTrue(any("external_reference evidence with a URL" in e for e in self.errors()))

    def test_reference_new_price_with_cited_url_is_valid(self):
        self.estimate()
        self.price_ev("ev_20", "external_reference", "supported", url="https://example.com/lg-24mk430h")
        self.doc["price_estimate"].update(basis="reference_new_price", evidence_refs=["ev_20"])
        self.assertEqual(self.errors(), [])
        self.assertEqual(minischema.validate(self.doc, validate.load_schema()), [])

    def test_model_knowledge_must_be_tentative(self):
        self.estimate()
        ref = self.doc["price_estimate"]["evidence_refs"][0]
        next(e for e in self.doc["evidence"] if e["id"] == ref)["certainty"] = "supported"
        self.assertTrue(any("tentative inference" in e for e in self.errors()))

    def test_user_comparables_need_user_statement(self):
        self.estimate()
        self.doc["price_estimate"]["basis"] = "user_comparables"
        self.assertTrue(any("user_statement" in e for e in self.errors()))

    def test_no_price_without_item_type(self):
        self.doc["item_type"] = None
        self.doc["evidence"] = [e for e in self.doc["evidence"] if e["field_path"] != "/item_type"]
        self.assertTrue(any("'not_applicable' while item_type is unknown" in e for e in self.errors()))
        self.doc["price_status"] = "not_applicable"
        self.assertFalse(any("item_type" in e for e in self.errors()))

    def test_price_schema_rejects_other_currency_and_negative(self):
        self.estimate()
        schema = validate.load_schema()
        self.doc["price_estimate"]["currency"] = "USD"
        self.assertTrue(minischema.validate(self.doc, schema))
        self.doc["price_estimate"]["currency"] = "EUR"
        self.doc["price_estimate"]["low"] = -5
        self.assertTrue(minischema.validate(self.doc, schema))

    def test_serial_number_in_listing_rejected(self):
        self.doc["listing_translations"]["en"]["description"] += "\nS/N 912KXQZ48213"
        self.assertTrue(any("serial" in e for e in self.errors()))

    def test_serial_number_in_observation_rejected(self):
        self.doc["evidence"][5]["observation"] = "Label shows S/N 912KXQZ48213."
        self.assertTrue(any("serial" in e for e in self.errors()))

    def test_hype_and_warranty_rejected(self):
        self.doc["listing_title"] = "Wie neu! Mit Garantie"
        errors = self.errors()
        self.assertTrue(any("hype" in e for e in errors))
        self.assertTrue(any("warranty" in e for e in errors))

    def test_upload_order_needs_inspected_known_photos(self):
        self.doc["photo_upload_order"].append({"ref": "photo_9", "note": None})
        self.assertTrue(any("photo_9 is not an inspected photo" in e for e in self.errors()))
        self.doc["photo_upload_order"].pop()
        self.doc["photos"][2]["inspected"] = False
        self.assertTrue(any("photo_3 is not an inspected photo" in e for e in self.errors()))

    def test_upload_order_rejects_duplicates(self):
        self.doc["photo_upload_order"].append(dict(self.doc["photo_upload_order"][0]))
        self.assertTrue(any("more than once" in e for e in self.errors()))

    def test_upload_note_must_not_carry_price(self):
        self.doc["photo_upload_order"][0]["note"] = "Preis 50 € aufs Foto schreiben"
        self.assertTrue(any("photo_upload_order note" in e for e in self.errors()))

    def test_listing_languages_must_match_nullness(self):
        self.doc["listing_translations"]["en"]["title"] = None
        self.assertTrue(any("all present or all null" in e for e in self.errors()))


class CaseCheckOps(unittest.TestCase):
    def test_preservation_detects_lost_fact(self):
        first = case_output("multi-turn-functionality", 0)
        second = case_output("multi-turn-functionality", 1)
        check = {"op": "preserved_from_previous_turn", "value": ["/brand"]}
        self.assertIsNone(validate.run_case_check(check, second, first))
        second["brand"] = None
        self.assertIsNotNone(validate.run_case_check(check, second, first))

    def test_evidence_ids_preserved(self):
        first = case_output("multi-turn-functionality", 0)
        second = case_output("multi-turn-functionality", 1)
        check = {"op": "evidence_ids_preserved"}
        self.assertIsNone(validate.run_case_check(check, second, first))
        second["evidence"][0]["user_confirmation"] = "confirmed"  # allowed update
        self.assertIsNone(validate.run_case_check(check, second, first))
        second["evidence"][0]["id"] = "ev_42"
        self.assertIsNotNone(validate.run_case_check(check, second, first))

    def test_no_visual_evidence(self):
        doc = case_output("no-image-access")
        self.assertIsNone(validate.run_case_check({"op": "no_visual_evidence"}, doc, None))
        doc["evidence"][0]["source"] = "photo"
        self.assertIsNotNone(validate.run_case_check({"op": "no_visual_evidence"}, doc, None))


class FrontmatterParser(unittest.TestCase):
    def write_skill(self, tmp, name, frontmatter):
        skill = Path(tmp) / name
        skill.mkdir()
        (skill / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n\n# Body\n", encoding="utf-8")
        return skill

    def test_uppercase_name_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(tmp, "ReLoop", "name: ReLoop\ndescription: Does things.")
            self.assertTrue(any("violates the spec" in p for p in validate.check_skill_dir(skill)))

    def test_name_must_match_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(tmp, "other", "name: reloop\ndescription: Does things.")
            self.assertTrue(any("must match directory" in p for p in validate.check_skill_dir(skill)))

    def test_unquoted_colon_rejected(self):
        with self.assertRaises(ValueError):
            validate.parse_frontmatter("---\nname: x\ndescription: Use when: always\n---\nbody")

    def test_non_spec_key_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(tmp, "x", "name: x\ndescription: Does things.\nversion: 1")
            self.assertTrue(any("not in the Agent Skills spec" in p for p in validate.check_skill_dir(skill)))

    def test_missing_resource_reference_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(tmp, "x", "name: x\ndescription: Does things.")
            (skill / "SKILL.md").write_text(
                "---\nname: x\ndescription: Does things.\n---\nRead `references/missing.md`.\n", encoding="utf-8")
            self.assertTrue(any("does not exist" in p for p in validate.check_skill_dir(skill)))

    def test_secret_patterns_detect_tokens(self):
        token = "ghp_" + "A1b2C3d4" * 5
        self.assertTrue(any(p.search(token) for p, _ in validate.SECRET_PATTERNS))

    def test_license_file_needs_frontmatter_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = self.write_skill(tmp, "x", "name: x\ndescription: Does things.")
            (skill / "LICENSE.txt").write_text("MIT License\n", encoding="utf-8")
            self.assertTrue(any("LICENSE.txt: bundled file is not referenced" in p
                                for p in validate.check_skill_dir(skill)))
            (skill / "SKILL.md").write_text(
                "---\nname: x\ndescription: Does things.\nlicense: MIT (see LICENSE.txt)\n---\n\n# Body\n",
                encoding="utf-8")
            self.assertEqual(validate.check_skill_dir(skill), [])


class LicenseChecks(unittest.TestCase):
    def test_repo_license_is_consistent(self):
        manifests = [json.loads((ROOT / p).read_text(encoding="utf-8"))
                     for p in ("packaging/claude-code/plugin.json", "packaging/codex/plugin.json")]
        self.assertEqual(validate.check_license(*manifests), [])
        self.assertIn("Copyright (c) 2026 Hashir Rizwan", (ROOT / "LICENSE").read_text(encoding="utf-8"))

    def test_manifest_license_mismatch_detected(self):
        self.assertTrue(validate.check_license({"name": "photo-to-listing", "license": "Apache-2.0"}))


if __name__ == "__main__":
    unittest.main()
