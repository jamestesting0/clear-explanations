"""Harness unit tests. Every response/review fixture is SYNTHETIC, not a model run."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

from core import (collect, evaluate, evaluate_many, load_reviews, markdown_table, paths, read_index,
                  sha, validate_cases, word_count, write_json)
from evaluate import make_packets, run_adapter
from report import render_report


class SyntheticHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-explanation-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "run"
        self.cases = [{"id": "SYNTH-01", "split": "development", "category": "SYNTHETIC FIXTURE",
                       "prompt": "SYNTHETIC: explain briefly. <script>alert('prompt')</script>",
                       "constraints": {"max_words": 30}}]
        write_json(self.root / "cases.json", self.cases)
        (self.root / "skill.md").write_text("SYNTHETIC guidance only.\n", encoding="utf-8")
        arguments = argparse.Namespace(cases=str(self.root / "cases.json"), out=str(self.run),
                                       skill=[f"synthetic={self.root / 'skill.md'}"], split="all", ids=None,
                                       name="SYNTHETIC TEST — NOT MODEL EVIDENCE")
        with contextlib.redirect_stdout(io.StringIO()):
            make_packets(arguments)
        self.index, self.by_id = read_index(self.run)
        self.packet = self.index["packets"][0]

    def add_response(self, response=b"SYNTHETIC response.\r\n", status="completed"):
        return collect(self.run, self.packet, self.cases[0], response,
                       {"transport": "synthetic-test-only", "status": status,
                        "notes": "NOT A REAL MODEL RUN"})

    def review_file(self, response=b"SYNTHETIC response.\r\n"):
        path = self.root / "synthetic-review.json"
        write_json(path, {"schema_version": 1, "reviewer": "SYNTHETIC TEST FIXTURE — NOT A REAL REVIEW",
                          "reviews": [{"variant": "synthetic", "case_id": "SYNTH-01", "response_sha256": sha(response),
                                       "verdict": "pass", "score": 1, "max_score": 1,
                                       "rationale": "SYNTHETIC <script>alert('review')</script>", "criteria": []}]})
        return path

    def test_word_count_is_documented_unicode_convention(self):
        self.assertEqual(word_count("“Don’t over-engineer.” Café 42. ** ###"), 4)
        self.assertEqual(word_count(""), 0)

    def test_strict_case_schema_blocks_answer_leak_and_bad_constraints(self):
        for change in ({"expected": "answer key"}, {"constraints": {"max_words": True}},
                       {"constraints": {"unknown": 1}}):
            case = dict(self.cases[0], **change)
            with self.assertRaises(ValueError):
                validate_cases([case])
        with self.assertRaises(ValueError):
            validate_cases(self.cases + self.cases)

    def test_collection_preserves_exact_bytes_and_refuses_overwrite(self):
        response = b"SYNTHETIC line one.\r\n\r\nLine two.  \r\n"
        meta = self.add_response(response)
        output, _ = paths(self.run, self.packet)
        self.assertEqual(output.read_bytes(), response)
        self.assertEqual(meta["response_sha256"], sha(response))
        with self.assertRaises(FileExistsError):
            self.add_response(response)
        self.assertTrue(evaluate(self.run)["results"][0]["deterministic_pass"])

    def test_missing_response_cannot_pass_even_with_passing_review(self):
        result = evaluate(self.run, self.review_file(b""))["results"][0]
        self.assertFalse(result["deterministic_pass"])
        self.assertFalse(result["fully_reviewed_pass"])
        self.assertEqual(result["review_state"], "invalid")

    def test_changed_response_invalidates_review(self):
        self.add_response()
        review = self.review_file()
        output, _ = paths(self.run, self.packet)
        output.write_bytes(b"SYNTHETIC changed response")
        result = evaluate(self.run, review)["results"][0]
        self.assertIn("response hash mismatch", result["errors"])
        self.assertEqual(result["review_state"], "invalid")

    def test_changed_packet_cannot_be_collected(self):
        (self.run / self.packet["prompt_path"]).write_text("SYNTHETIC tampering", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.add_response()

    def test_missing_manifest_cannot_pass(self):
        self.add_response()
        (self.run / "manifest.jsonl").unlink()
        self.assertFalse(evaluate(self.run)["results"][0]["deterministic_pass"])

    def test_markdown_table_detection_excludes_fenced_examples(self):
        table = "Name | Meaning\n--- | ---\nA | B\n"
        self.assertTrue(markdown_table(table))
        self.assertFalse(markdown_table("```text\n" + table + "```\n"))

    def test_html_escapes_prompt_response_and_review(self):
        response = b"SYNTHETIC <script>alert('response')</script> & </pre><img src=x>"
        self.add_response(response)
        report = render_report(evaluate(self.run, self.review_file(response)))
        self.assertNotIn("<script>", report)
        self.assertNotIn("<img src=x>", report)
        self.assertIn("&lt;script&gt;", report)
        self.assertIn("Content-Security-Policy", report)

    def test_unreviewed_outputs_have_no_quality_score(self):
        self.add_response()
        result = evaluate(self.run)
        self.assertEqual(result["results"][0]["review_state"], "unreviewed")
        self.assertFalse(result["results"][0]["fully_reviewed_pass"])
        self.assertIn("No review score", render_report(result))

    def test_score_schema_rejects_nonfinite_and_invalid_criteria(self):
        path = self.review_file()
        document = json.loads(path.read_text(encoding="utf-8"))
        document["reviews"][0]["max_score"] = float("inf")
        write_json(path, document)
        with self.assertRaises(ValueError):
            load_reviews(path)

    def test_external_adapter_synthetic_stdout_is_exact(self):
        code = "import sys; sys.stdin.buffer.read(); sys.stdout.buffer.write(b'SYNTHETIC adapter response.\\r\\n')"
        args = argparse.Namespace(command_json=json.dumps([sys.executable, "-c", code]), timeout=5,
                                  run=str(self.run), variant=None, ids=None, skip_existing=False,
                                  model=None, cwd=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_adapter(args), 0)
        output, _ = paths(self.run, self.packet)
        self.assertEqual(output.read_bytes(), b"SYNTHETIC adapter response.\r\n")

    def test_failed_transport_cannot_pass(self):
        self.add_response(status="command_error")
        result = evaluate(self.run, self.review_file())["results"][0]
        self.assertFalse(result["deterministic_pass"])
        self.assertEqual(result["review_state"], "invalid")

    def test_timeout_preserves_partial_synthetic_output_and_cannot_pass(self):
        code = "import sys,time; print('SYNTHETIC partial output.',flush=True); time.sleep(2)"
        args = argparse.Namespace(command_json=json.dumps([sys.executable, "-c", code]), timeout=0.2,
                                  run=str(self.run), variant=None, ids=None, skip_existing=False,
                                  model=None, cwd=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_adapter(args), 1)
        result = evaluate(self.run)["results"][0]
        self.assertIn("SYNTHETIC partial output.", result["response"])
        self.assertEqual(result["metadata"]["status"], "timeout")
        self.assertFalse(result["deterministic_pass"])

    def test_multi_run_aggregation_rejects_duplicate_scheduled_records(self):
        self.add_response()
        self.assertEqual(len(evaluate_many([self.run])["results"]), 1)
        with self.assertRaises(ValueError):
            evaluate_many([self.run, self.run])

    def test_different_variant_subsets_do_not_invent_missing_cases(self):
        second = dict(self.cases[0], id="SYNTH-02", split="holdout")
        write_json(self.root / "second-cases.json", self.cases + [second])
        other_run = self.root / "second-run"
        args = argparse.Namespace(cases=str(self.root / "second-cases.json"), out=str(other_run),
                                  skill=["synthetic_other=none"], split="all", ids=None, name="SYNTHETIC SECOND RUN")
        with contextlib.redirect_stdout(io.StringIO()):
            make_packets(args)
        result = evaluate_many([self.run, other_run])
        self.assertEqual(len(result["results"]), 3)
        self.assertNotIn(("synthetic", "SYNTH-02"), {(r["variant"], r["case_id"]) for r in result["results"]})


if __name__ == "__main__":
    unittest.main()
