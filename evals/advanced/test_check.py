"""Synthetic archive fixtures only: no benchmark answers, gold, maps, or holdouts are read."""
from __future__ import annotations

import contextlib
from copy import deepcopy
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))
spec = importlib.util.spec_from_file_location("synthetic_advanced_checker", HERE / "check.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
from core import BUNDLE_MODE, bundle_digest, canonical, constraint_checks, format_packet, sha, word_count


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


class SyntheticArchive:
    def __init__(self, root, failure=None):
        self.root, self.files = root, {}
        self.hard = [{"id": f"SYNTH-{number:03d}", "split": "development" if number <= 36 else "validation" if number <= 48 else "holdout",
                      "category": "SYNTHETIC ONLY", "prompt": f"SYNTHETIC invented case {number}. " + "fixture " * 400,
                      "constraints": {"max_words": 20, "exact_sentences": 1}} for number in range(1, 61)]
        self.short = [{"id": f"N{number:02d}", "split": "development", "category": "SYNTHETIC ONLY",
                       "prompt": f"SYNTHETIC short case {number}.", "constraints": {"max_words": 20}} for number in range(1, 7)]
        self.cases = {case["id"]: case for case in self.hard + self.short}
        self.resources = {"old": {"SKILL.md": b"SYNTHETIC old guidance.\r\n"},
                          "new": {"SKILL.md": b"SYNTHETIC new guidance.\r\n", "references/guide.md": b"SYNTHETIC reference.  \r\n"}}
        inputs = {"protocol": "protocol.json", "protocol_addendum": "protocol-addendum.json",
                  "short_transfer_plan": "short-transfer-plan.json", "generation_instructions": "generation-instructions.md",
                  "review_instructions": "review-instructions.md"}
        self.files.update({"protocol.json": encoded({"schema_version": 1,
                          "case_plan": {"total": 60, "development": 36, "validation": 12, "holdout": 12,
                                        "minimum_prompt_whitespace_words": 400}, "verdict_policy": {"maximum_score": 12}}),
                           "protocol-addendum.json": encoded({"schema_version": 1, "note": "SYNTHETIC"}),
                           "short-transfer-plan.json": encoded({"case_ids": sorted(checker.SHORT_IDS)}),
                           "generation-instructions.md": b"SYNTHETIC generation instructions.\n",
                           "review-instructions.md": b"SYNTHETIC review instructions.\n",
                           "original-gold-caveat.json": encoded({"note": "SYNTHETIC original gold is fallible; retain it."}),
                           "original-review-note.txt": b"SYNTHETIC preserved historical review note.\n"})
        gold_files = {phase: f"gold/{phase}.json" for phase in (*checker.SPLITS, "short")}
        for phase, path in gold_files.items():
            cases = self.short if phase == "short" else [case for case in self.hard if case["split"] == phase]
            self.files[path] = encoded({case["id"]: {"must_include": [f"SYNTHETIC essential {index}" for index in range(1, 3 if phase == "short" else 7)],
                                                    "must_not": [], "critical_errors": [], "source_expectations": "SYNTHETIC only",
                                                    "verification": "Synthetic harness fixture, no quality evidence."} for case in cases})
        versions = {}
        for variant, resources in self.resources.items():
            directory = f"versions/{variant}"
            for name, raw in resources.items():
                self.files[f"{directory}/{'INSTRUCTIONS.md' if name == 'SKILL.md' else name}"] = raw
            versions[variant] = {"directory": directory, "entry_file": "INSTRUCTIONS.md",
                                 "guidance_mode": "single_file" if variant == "old" else BUNDLE_MODE,
                                 "skill_sha256": sha(resources["SKILL.md"]), "bundle_sha256": None if variant == "old" else
                                 bundle_digest([{"resource_path": name, "sha256": sha(raw), "bytes": len(raw)} for name, raw in resources.items()])}
        self.evidence = {"schema_version": 1, "integrity_version": 2, "inputs": inputs, "gold_files": gold_files,
                         "gold_annotation_files": ["original-gold-caveat.json"], "provenance_files": ["original-review-note.txt"],
                         "variants": versions, "baseline_variant": "old", "release_variant": "new",
                         "variant_case_ids": {variant: list(self.cases) for variant in versions},
                         "record_files": ["records.jsonl"], "batches_file": "batches.json",
                         "review_files": [f"reviews/{phase}.json" for phase in (*checker.SPLITS, "short")]}
        self.records, self.batches = [], []
        ids = list(self.cases)
        for variant, resources in self.resources.items():
            hashes = {case_id: sha(format_packet(case, skill=resources["SKILL.md"]) if variant == "old"
                                   else format_packet(case, resources=list(resources.items()))) for case_id, case in self.cases.items()}
            for offset in range(0, len(ids), 6):
                order = ids[offset:offset + 6]
                batch = {"variant": variant, "batch_id": f"SYNTH-BATCH-{offset:03d}", "batch_order": order, "batch_size": len(order),
                         "ordered_batch_sha256": sha(canonical([{"case_id": case_id, "prompt_sha256": hashes[case_id]} for case_id in order])),
                         "generation_instructions_sha256": sha(self.files[inputs["generation_instructions"]]),
                         "runtime_prompt_file": None, "runtime_prompt_sha256": None}
                self.batches.append(batch)
                for case_id in order:
                    case, version = self.cases[case_id], versions[variant]
                    response = "SYNTHETIC café.\r\n"
                    if failure == "mechanical" and not self.records:
                        response = "SYNTHETIC " * 21
                    if failure == "heuristic" and not self.records:
                        response = "SYNTHETIC. Another sentence.\r\n"
                    digest = sha(response.encode("utf-8"))
                    criteria = 2 if case_id in checker.SHORT_IDS else 6
                    review = {"variant": variant, "case_id": case_id, "response_sha256": digest,
                              "verdict": "pass", "dimensions": {dimension: 2 for dimension in checker.DIMENSIONS},
                              "score": 12, "max_score": 12, "hard_constraints_satisfied": True, "critical_errors": [], "gold_flags": [],
                              "rationale": "SYNTHETIC judgment, not a model review.",
                              "criteria": [{"criterion": f"C{index}", "verdict": "pass", "notes": "SYNTHETIC"} for index in range(1, criteria + 1)]}
                    if failure == "semantic" and not self.records:
                        review.update(verdict="partial", hard_constraints_satisfied=False)
                    if failure == "critical" and not self.records:
                        review["dimensions"]["accuracy"], review["score"] = 0, 10
                    metadata = {"variant": variant, "case_id": case_id, "response_sha256": digest, "response_bytes": len(response.encode("utf-8")),
                                "case_sha256": sha(canonical(case)), "prompt_sha256": hashes[case_id],
                                "prompt_sha256_role": "canonical_replay_packet", "runtime_prompt_sha256": None,
                                "skill_sha256": version["skill_sha256"], "bundle_sha256": version["bundle_sha256"], "status": "completed",
                                "source_metadata": {key: deepcopy(batch[key]) for key in ("batch_id", "batch_order", "batch_size", "ordered_batch_sha256")}}
                    if variant == "new":
                        metadata["guidance_mode"] = BUNDLE_MODE
                    record = {"variant": variant, "case_id": case_id, "response": response, "response_sha256": digest,
                              "metadata": metadata, "review": review, "word_count": word_count(response), "character_count": len(response),
                              "errors": [], "review_state": "valid",
                              "deterministic_pass": not any(item["passed"] is False for item in constraint_checks(response, case["constraints"]))}
                    record["reporting_verdict"] = checker.resolved_verdict(record)
                    record["fully_reviewed_pass"] = record["reporting_verdict"] == "pass"
                    self.records.append(record)
        self.bind_reviews()
        self.save()

    def phase(self, case_id):
        return "short" if case_id in checker.SHORT_IDS else self.cases[case_id]["split"]

    def bind_reviews(self):
        for phase in (*checker.SPLITS, "short"):
            records = [record for record in self.records if self.phase(record["case_id"]) == phase]
            source = f"reviews/{phase}.json"
            self.files[source] = encoded({"schema_version": 1, "reviewer": "SYNTHETIC FIXTURE ONLY",
                                          "reviews": [deepcopy(record["review"]) for record in records]})
            gold_path = self.evidence["gold_files"][phase]
            parent = f"blind/{phase}"
            self.files[f"{parent}/rubric.json"] = self.files[gold_path]
            index = {"schema_version": 1, "kind": "blind-review-packets", "packets": [], "rubric_path": "rubric.json",
                     "rubric_sha256": sha(self.files[gold_path])}
            for number, record in enumerate(records, 1):
                case = self.cases[record["case_id"]]
                review_id = f"REVIEW-{number:04d}"
                packet_path = f"{parent}/packets/{review_id}.json"
                packet = {"schema_version": 1, "review_id": review_id, "case_id": case["id"], "case_sha256": sha(canonical(case)),
                          "prompt": case["prompt"], "constraints": case["constraints"], "response": record["response"],
                          "response_sha256": record["response_sha256"]}
                self.files[packet_path] = encoded(packet)
                index["packets"].append({"review_id": review_id, "case_id": case["id"],
                                         "packet_path": f"packets/{review_id}.json", "packet_sha256": sha(self.files[packet_path])})
                inputs = self.evidence["inputs"]
                record["review_provenance"] = {"review_file": source, "review_file_sha256": sha(self.files[source]),
                                                "review_packet_file": packet_path, "review_packet_sha256": sha(self.files[packet_path]),
                                                "review_index_file": f"{parent}/index.json", "review_id": review_id,
                                                "case_sha256": sha(canonical(case)), "user_prompt_sha256": sha(case["prompt"].encode("utf-8")),
                                                "response_sha256": record["response_sha256"],
                                                "input_files_sha256": {path: sha(self.files[path]) for path in
                                                 (inputs["protocol"], inputs["protocol_addendum"], inputs["review_instructions"], gold_path)}}
            self.files[f"{parent}/index.json"] = encoded(index)
            for record in records:
                record["review_provenance"]["review_index_sha256"] = sha(self.files[f"{parent}/index.json"])

    def summaries(self):
        hard = {variant: [record for record in self.records if record["variant"] == variant and record["case_id"] not in checker.SHORT_IDS]
                for variant in self.evidence["variants"]}
        short = {variant: [record for record in self.records if record["variant"] == variant and record["case_id"] in checker.SHORT_IDS]
                 for variant in self.evidence["variants"]}
        self.evidence["summaries"] = {variant: checker.stats(group) for variant, group in hard.items()}
        self.evidence["short_summaries"] = {variant: checker.stats(group) for variant, group in short.items()}
        self.evidence["split_summaries"] = {variant: {split: checker.stats([record for record in group if self.cases[record["case_id"]]["split"] == split])
                                                      for split in checker.SPLITS} for variant, group in hard.items()}
        self.evidence["paired_summary"] = {"hard": checker.paired_stats(hard["old"], hard["new"]),
                                            "short": checker.paired_stats(short["old"], short["new"]),
                                            "by_split": {split: checker.paired_stats(
                                                [record for record in hard["old"] if self.cases[record["case_id"]]["split"] == split],
                                                [record for record in hard["new"] if self.cases[record["case_id"]]["split"] == split]) for split in checker.SPLITS}}

    def save(self, summaries=True):
        self.files["cases.json"], self.files["short-cases.json"] = encoded(self.hard), encoded(self.short)
        self.files["batches.json"] = encoded({"schema_version": 1, "batches": self.batches})
        self.files["records.jsonl"] = b"".join(canonical(record) + b"\n" for record in self.records)
        self.evidence["actual_responses"] = len(self.records)
        if summaries:
            self.summaries()
        for name, raw in self.files.items():
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.evidence["recorded_files_sha256"] = {name: sha(raw) for name, raw in self.files.items()}
        self.save_evidence()

    def save_evidence(self):
        (self.root / "evidence.json").write_bytes(encoded(self.evidence))


class AdvancedArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-advanced-check-")
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.number = 0
        self.archive = self.build()
        self.patcher = patch.object(checker, "ROOT", self.archive.root)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def build(self, failure=None):
        self.number += 1
        archive = SyntheticArchive(self.directory / str(self.number) / "repo" / "evals" / "advanced", failure=failure)
        if hasattr(self, "patcher"):
            checker.ROOT = archive.root
            self.archive = archive
        return archive

    def verify(self):
        return checker.verify()

    def test_complete_archive_accepts_132_bound_records_without_quality_claim(self):
        evidence, records = self.verify()
        self.assertEqual(len(records), 132)
        self.assertEqual(evidence["summaries"]["old"]["responses"], 60)
        self.assertEqual(evidence["short_summaries"]["new"]["responses"], 6)
        self.assertEqual(evidence["paired_summary"]["hard"]["score_comparison"], {"wins": 0, "ties": 60, "regressions": 0})

    def test_mechanical_failure_is_counted_and_original_review_remains_intact(self):
        archive = self.build(failure="mechanical")
        before = deepcopy(archive.records[0]["review"])
        evidence, records = self.verify()
        self.assertEqual(records[0]["review"], before)
        self.assertEqual(records[0]["review"]["verdict"], "pass")
        self.assertEqual(records[0]["reporting_verdict"], "fail")
        summary = evidence["summaries"]["old"]
        self.assertEqual((summary["pass"], summary["partial"], summary["fail"], summary["critical_failures"], summary["hard_constraint_failures"]), (59, 0, 1, 1, 1))
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(checker.main([]), 0)
        self.assertIn("59/60 pass", output.getvalue())
        self.assertIn("integrity, not universal explanation quality", output.getvalue())

    def test_semantic_constraint_and_critical_failures_override_preserved_verdicts(self):
        for failure in ("semantic", "critical"):
            with self.subTest(failure=failure):
                self.build(failure=failure)
                evidence, records = self.verify()
                self.assertEqual(records[0]["reporting_verdict"], "fail")
                self.assertFalse(records[0]["fully_reviewed_pass"])
                self.assertEqual(evidence["summaries"]["old"]["critical_failures"], 1)

    def test_heuristic_sentence_estimate_does_not_become_a_hard_failure(self):
        self.build(failure="heuristic")
        _, records = self.verify()
        self.assertTrue(records[0]["deterministic_pass"])
        self.assertEqual(records[0]["reporting_verdict"], "pass")

    def test_hard_failure_cannot_disappear_from_reporting_flags(self):
        archive = self.build(failure="mechanical")
        archive.records[0]["reporting_verdict"] = "pass"
        archive.records[0]["fully_reviewed_pass"] = True
        archive.save()
        with self.assertRaisesRegex(ValueError, "reporting verdict"):
            self.verify()

    def test_nonempty_complete_summaries_and_exact_verified_fields_are_required(self):
        original = deepcopy(self.archive.evidence)
        for change in ("empty-hard", "missing-short", "missing-split", "wrong-dimension", "wrong-pair", "unchecked-field"):
            with self.subTest(change=change):
                evidence = deepcopy(original)
                if change == "empty-hard":
                    evidence["summaries"] = {}
                elif change == "missing-short":
                    del evidence["short_summaries"]["old"]
                elif change == "missing-split":
                    del evidence["split_summaries"]["new"]["holdout"]
                elif change == "wrong-dimension":
                    evidence["summaries"]["new"]["mean_dimensions"]["accuracy"] = 0
                elif change == "wrong-pair":
                    evidence["paired_summary"]["hard"]["score_comparison"]["wins"] = 60
                else:
                    evidence["summaries"]["new"]["unverified_claim"] = 100
                self.archive.evidence = evidence
                self.archive.save_evidence()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_both_compared_variants_require_all_hard_and_short_responses(self):
        original = deepcopy(self.archive.records)
        for variant in ("old", "new"):
            for case_id in ("SYNTH-001", "N06"):
                with self.subTest(variant=variant, case_id=case_id):
                    self.archive.records = [deepcopy(record) for record in original if (record["variant"], record["case_id"]) != (variant, case_id)]
                    self.archive.save(summaries=False)
                    with self.assertRaisesRegex(ValueError, "coverage"):
                        self.verify()

    def test_declared_coverage_cannot_exclude_short_cases_or_omit_a_variant(self):
        original = deepcopy(self.archive.evidence)
        for change in ("short", "variant", "duplicate"):
            with self.subTest(change=change):
                self.archive.evidence = deepcopy(original)
                coverage = self.archive.evidence["variant_case_ids"]
                if change == "short":
                    coverage["old"].remove("N01")
                elif change == "variant":
                    del coverage["new"]
                else:
                    coverage["new"].append(coverage["new"][0])
                self.archive.save_evidence()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_registered_short_identities_cannot_be_replaced(self):
        self.archive.short[0]["id"] = "SYNTH-SHORT-UNKNOWN"
        self.archive.save(summaries=False)
        with self.assertRaisesRegex(ValueError, "registered short"):
            self.verify()

    def test_every_consumed_file_class_requires_hash_inventory_coverage(self):
        original = deepcopy(self.archive.evidence)
        first = self.archive.records[0]["review_provenance"]
        names = ["cases.json", "short-cases.json", "protocol.json", "protocol-addendum.json", "short-transfer-plan.json",
                 "generation-instructions.md", "review-instructions.md", "records.jsonl", "batches.json",
                 "versions/old/INSTRUCTIONS.md", "versions/new/references/guide.md", "gold/development.json",
                 first["review_file"], first["review_packet_file"], first["review_index_file"], "blind/development/rubric.json",
                 "original-gold-caveat.json", "original-review-note.txt"]
        for name in [None, *names]:
            with self.subTest(name=name):
                self.archive.evidence = deepcopy(original)
                inventory = self.archive.evidence["recorded_files_sha256"]
                if name is None:
                    inventory.clear()
                else:
                    del inventory[name]
                self.archive.save_evidence()
                with self.assertRaisesRegex(ValueError, "inventory"):
                    self.verify()

    def test_containment_applies_to_inventory_records_and_frozen_directories(self):
        original = deepcopy(self.archive.evidence)
        for change in ("inventory", "record", "variant"):
            with self.subTest(change=change):
                self.archive.evidence = deepcopy(original)
                if change == "inventory":
                    self.archive.evidence["recorded_files_sha256"]["../outside.txt"] = "0" * 64
                elif change == "record":
                    self.archive.evidence["record_files"] = ["../outside.jsonl"]
                else:
                    self.archive.evidence["variants"]["new"]["directory"] = "../outside"
                self.archive.save_evidence()
                with self.assertRaises(ValueError):
                    self.verify()

    @unittest.skipUnless(os.name == "posix", "Symlink fixture requires POSIX")
    def test_symlinked_inventory_files_and_unlisted_frozen_references_are_rejected(self):
        path = self.archive.root / "versions/new/references/guide.md"
        raw = path.read_bytes()
        outside = self.directory / "same-bytes.md"
        outside.write_bytes(raw)
        path.unlink()
        path.symlink_to(outside)
        with self.assertRaises(ValueError):
            self.verify()
        path.unlink()
        path.write_bytes(raw)
        (path.parent / "extra.md").write_bytes(b"SYNTHETIC unlisted reference")
        with self.assertRaisesRegex(ValueError, "inventory"):
            self.verify()

    def test_archived_entry_alias_preserves_canonical_bytes_and_default_still_works(self):
        original_hash = self.archive.records[0]["metadata"]["prompt_sha256"]
        old = self.archive.evidence["variants"]["old"]
        raw = self.archive.files.pop("versions/old/INSTRUCTIONS.md")
        self.archive.files["versions/old/SKILL.md"] = raw
        del old["entry_file"]
        (self.archive.root / "versions/old/INSTRUCTIONS.md").unlink()
        self.archive.save()
        _, records = self.verify()
        self.assertEqual(records[0]["metadata"]["prompt_sha256"], original_hash)
        old["entry_file"] = "../INSTRUCTIONS.md"
        self.archive.save_evidence()
        with self.assertRaisesRegex(ValueError, "entry filename"):
            self.verify()

    def test_reconstructed_prompt_and_guidance_mode_cannot_be_forged(self):
        original = deepcopy(self.archive.records)
        for field, value in (("prompt_sha256", "0" * 64), ("prompt_sha256_role", "claimed_full_context"),
                             ("guidance_mode", BUNDLE_MODE), ("skill_sha256", "0" * 64)):
            with self.subTest(field=field):
                self.archive.records = deepcopy(original)
                self.archive.records[0]["metadata"][field] = value
                self.archive.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_failed_empty_or_stale_response_records_cannot_verify(self):
        original = deepcopy(self.archive.records)
        for change in ("status", "error", "empty", "changed", "byte-count", "unreviewed"):
            with self.subTest(change=change):
                self.archive.records = deepcopy(original)
                record = self.archive.records[0]
                if change == "status":
                    record["metadata"]["status"] = "command_error"
                elif change == "error":
                    record["errors"] = ["SYNTHETIC transport error"]
                elif change == "empty":
                    record["response"] = ""
                elif change == "changed":
                    record["response"] += "SYNTHETIC alteration"
                elif change == "byte-count":
                    record["metadata"]["response_bytes"] += 1
                else:
                    record["review_state"] = "unreviewed"
                self.archive.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_ordered_batch_requires_unique_members_consistent_metadata_and_hash(self):
        original_batches, original_records = deepcopy(self.archive.batches), deepcopy(self.archive.records)
        for change in ("duplicate-case", "duplicate-batch", "overlap", "hash", "record-order", "instructions"):
            with self.subTest(change=change):
                self.archive.batches, self.archive.records = deepcopy(original_batches), deepcopy(original_records)
                batch = self.archive.batches[0]
                if change == "duplicate-case":
                    batch["batch_order"][1] = batch["batch_order"][0]
                elif change == "duplicate-batch":
                    self.archive.batches.append(deepcopy(batch))
                elif change == "overlap":
                    extra = deepcopy(batch)
                    extra["batch_id"] = "SYNTHETIC-OVERLAP"
                    self.archive.batches.append(extra)
                elif change == "hash":
                    batch["ordered_batch_sha256"] = "0" * 64
                elif change == "record-order":
                    self.archive.records[0]["metadata"]["source_metadata"]["batch_order"].reverse()
                else:
                    batch["generation_instructions_sha256"] = "0" * 64
                self.archive.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_self_consistent_but_unmatched_candidate_batch_order_is_rejected(self):
        batch = next(batch for batch in self.archive.batches if batch["variant"] == "new")
        batch["batch_order"].reverse()
        metadata = {record["case_id"]: record["metadata"] for record in self.archive.records if record["variant"] == "new"}
        batch["ordered_batch_sha256"] = sha(canonical([{"case_id": case_id, "prompt_sha256": metadata[case_id]["prompt_sha256"]}
                                                      for case_id in batch["batch_order"]]))
        for case_id in batch["batch_order"]:
            metadata[case_id]["source_metadata"].update({key: deepcopy(batch[key]) for key in ("batch_order", "ordered_batch_sha256")})
        self.archive.save()
        with self.assertRaisesRegex(ValueError, "different batch"):
            self.verify()

    def test_batch_hash_is_never_a_substitute_for_unobserved_runtime_context(self):
        batch = self.archive.batches[0]
        batch["runtime_prompt_sha256"] = batch["ordered_batch_sha256"]
        self.archive.save()
        with self.assertRaisesRegex(ValueError, "full runtime prompt hash"):
            self.verify()
        batch["runtime_prompt_sha256"] = None
        self.archive.records[0]["metadata"]["runtime_prompt_sha256"] = batch["ordered_batch_sha256"]
        self.archive.save()
        with self.assertRaisesRegex(ValueError, "full runtime prompt hash"):
            self.verify()

    def test_claimed_runtime_hash_requires_its_exact_archived_bytes(self):
        batch = self.archive.batches[0]
        raw = b"SYNTHETIC exact runtime fixture, not an observed model invocation.\r\n"
        self.archive.files["runtime/SYNTHETIC.txt"] = raw
        batch.update(runtime_prompt_file="runtime/SYNTHETIC.txt", runtime_prompt_sha256=sha(raw))
        for record in self.archive.records:
            if record["variant"] == batch["variant"] and record["case_id"] in batch["batch_order"]:
                record["metadata"]["runtime_prompt_sha256"] = sha(raw)
        self.archive.save()
        self.verify()
        (self.archive.root / "runtime/SYNTHETIC.txt").write_bytes(raw + b"altered")
        with self.assertRaisesRegex(ValueError, "Recorded file changed"):
            self.verify()

    def test_final_review_requires_exact_source_prompt_response_gold_and_instruction_bindings(self):
        original = deepcopy(self.archive.records)
        fields = ("review_file_sha256", "review_packet_sha256", "review_index_sha256", "case_sha256", "user_prompt_sha256", "response_sha256")
        for field in (*fields, "input_files_sha256", "review_id", "no-provenance"):
            with self.subTest(field=field):
                self.archive.records = deepcopy(original)
                record = self.archive.records[0]
                if field == "no-provenance":
                    del record["review_provenance"]
                elif field == "input_files_sha256":
                    record["review_provenance"][field] = {}
                elif field == "review_id":
                    record["review_provenance"][field] = "UNKNOWN"
                else:
                    record["review_provenance"][field] = "0" * 64
                self.archive.save()
                with self.assertRaises((ValueError, KeyError)):
                    self.verify()

    def test_blind_packet_and_gold_copy_must_match_even_after_rehashing_inventory(self):
        original = deepcopy(self.archive.files)
        first = self.archive.records[0]["review_provenance"]
        for path in (first["review_packet_file"], first["review_index_file"], "blind/development/rubric.json"):
            with self.subTest(path=path):
                self.archive.files = deepcopy(original)
                self.archive.files[path] += b" "
                self.archive.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_final_review_cannot_change_while_preserved_source_is_stale(self):
        self.archive.records[0]["review"]["rationale"] = "SYNTHETIC changed judgment"
        self.archive.save()
        with self.assertRaisesRegex(ValueError, "preserved source"):
            self.verify()

    def test_essential_criterion_id_coverage_and_pass_threshold_are_required(self):
        original = deepcopy(self.archive.records)
        for change in ("missing", "duplicate", "unknown", "unmet", "score"):
            with self.subTest(change=change):
                self.archive.records = deepcopy(original)
                review = self.archive.records[0]["review"]
                if change == "missing":
                    review["criteria"].pop()
                elif change == "duplicate":
                    review["criteria"][-1]["criterion"] = "C1"
                elif change == "unknown":
                    review["criteria"][-1]["criterion"] = "UNNAMED"
                elif change == "unmet":
                    review["criteria"][0]["verdict"] = "partial"
                else:
                    review["dimensions"].update(clarity=1, structure=1)
                    review["score"] = 10
                self.archive.bind_reviews()
                self.archive.save()
                with self.assertRaises(ValueError):
                    self.verify()

    def test_original_gold_and_flag_are_preserved_with_separate_bound_annotation(self):
        before = self.archive.files["gold/development.json"]
        self.archive.records[0]["review"]["gold_flags"] = ["SYNTHETIC fallible gold flag"]
        self.archive.bind_reviews()
        provenance = self.archive.records[0]["review_provenance"]
        annotation = "original-gold-caveat.json"
        provenance["gold_annotation_files"] = [annotation]
        provenance["input_files_sha256"][annotation] = sha(self.archive.files[annotation])
        self.archive.save()
        _, records = self.verify()
        self.assertEqual(records[0]["review"]["gold_flags"], ["SYNTHETIC fallible gold flag"])
        self.assertEqual((self.archive.root / "gold/development.json").read_bytes(), before)

    def test_require_current_compares_canonical_resource_bytes_with_archived_entry_alias(self):
        repo = self.archive.root.parents[1]
        for name, raw in self.archive.resources["new"].items():
            path = repo / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        checker.verify(require_current=True)
        (repo / "references/guide.md").write_bytes(b"SYNTHETIC changed current reference")
        with self.assertRaisesRegex(ValueError, "Current runtime bundle"):
            checker.verify(require_current=True)

    def test_json_output_contains_only_fully_checked_summary_groups(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(checker.main(["--json"]), 0)
        self.assertEqual(set(json.loads(output.getvalue())), {"summaries", "short_summaries", "split_summaries", "paired_summary"})

    def test_formatter_keeps_the_pre_extraction_bundle_packet_hash(self):
        case = {"prompt": "SYNTHETIC: explain briefly. <script>alert('prompt')</script>"}
        resources = [("SKILL.md", b"SYNTHETIC root guidance.\r\nSee references/guide.md.\r\n"),
                     ("references/guide.md", "SYNTHETIC reference: café.\r\nExact trailing space.  \r\n".encode("utf-8")),
                     ("references/second.md", b"SYNTHETIC second reference without a final newline.")]
        self.assertEqual(sha(format_packet(case, resources=list(reversed(resources)))),
                         "6bd9895c9d6941ade9bb895deb282f2938ede30b71e8e0d0817dc2fd27e459cc")


if __name__ == "__main__":
    unittest.main()
