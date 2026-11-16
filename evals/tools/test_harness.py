"""Harness unit tests. Every response/review fixture is SYNTHETIC, not a model run."""
import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from core import (BUNDLE_MODE, collect, evaluate, evaluate_many, load_reviews, markdown_table,
                  packet_integrity, paths, read_index, sha, validate_cases, word_count, write_json)
from evaluate import main, make_packets, run_adapter
from report import render_report
from review_packets import import_blind_reviews, make_review_packets


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

    def bundle_source(self, name="bundle"):
        source = self.root / name
        (source / "references").mkdir(parents=True)
        (source / "SKILL.md").write_bytes(b"SYNTHETIC root guidance.\r\nSee references/guide.md.\r\n")
        (source / "references" / "guide.md").write_bytes("SYNTHETIC reference: café.\r\nExact trailing space.  \r\n".encode("utf-8"))
        (source / "references" / "second.md").write_bytes(b"SYNTHETIC second reference without a final newline.")
        return source

    def bundle_run(self, source=None, name="bundle-run", variant="bundled", cases=None):
        source = source or self.bundle_source()
        run = self.root / name
        args = argparse.Namespace(cases=str(cases or self.root / "cases.json"), out=str(run), skill=[],
                                  bundle=[f"{variant}={source}"], split="all", ids=None,
                                  name="SYNTHETIC BUNDLE TEST — NOT MODEL EVIDENCE")
        with contextlib.redirect_stdout(io.StringIO()):
            make_packets(args)
        index, cases_by_id = read_index(run)
        return run, index["packets"][0], cases_by_id

    def blind_packets(self, response=b"SYNTHETIC response.\r\n", paired=False, rubric=True):
        self.add_response(response)
        runs = [self.run]
        if paired:
            second_run = self.root / "paired-run"
            args = argparse.Namespace(cases=str(self.root / "cases.json"), out=str(second_run),
                                      skill=["synthetic_other=none"], split="all", ids=None, name="SYNTHETIC PAIR")
            with contextlib.redirect_stdout(io.StringIO()):
                make_packets(args)
            index, cases = read_index(second_run)
            packet = index["packets"][0]
            collect(second_run, packet, cases[packet["case_id"]], b"SYNTHETIC paired answer.\r\n", {})
            runs.append(second_run)
        rubric_path = self.root / "separate-rubric.json"
        write_json(rubric_path, {"SYNTH-01": {"expected": "SYNTHETIC PRIVATE RUBRIC MARKER"}})
        args = argparse.Namespace(run=runs, out=str(self.root / "reviewer"), key=str(self.root / "private-key.json"),
                                  rubric=str(rubric_path) if rubric else None)
        with contextlib.redirect_stdout(io.StringIO()):
            make_review_packets(args)
        return args

    def finish_blind_reviews(self, exported):
        document = json.loads((Path(exported.out) / "review-template.json").read_bytes())
        document["reviewer"] = "SYNTHETIC REVIEW FIXTURE — NOT A REAL REVIEW"
        for review in document["reviews"]:
            review.update(verdict="pass", score=11, max_score=12, rationale="SYNTHETIC judgment.")
        path = self.root / "completed-blind-reviews.json"
        write_json(path, document)
        return argparse.Namespace(run=exported.run, packets=exported.out, key=exported.key,
                                  reviews=str(path), out=str(self.root / "unblinded-reviews.json"))

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

    def test_optional_advanced_case_metadata_is_validated_without_changing_old_cases(self):
        original = json.loads(json.dumps(self.cases))
        self.assertEqual(validate_cases(self.cases), original)
        advanced = dict(self.cases[0], split="validation", source_ids=["SYNTHETIC-SOURCE"],
                        complexity_features=["SYNTHETIC hidden metadata"])
        self.assertEqual(validate_cases([advanced]), [advanced])
        for field in ("source_ids", "complexity_features"):
            for invalid in ("not an array", [""], ["  "], [1], [None]):
                with self.subTest(field=field, value=invalid), self.assertRaises(ValueError):
                    validate_cases([dict(advanced, **{field: invalid})])
        case_path = self.root / "advanced-cases.json"
        write_json(case_path, [advanced])
        run = self.root / "advanced-run"
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(["packets", "--cases", str(case_path), "--out", str(run),
                                   "--split", "validation", "--skill", "baseline=none"]), 0)
        index, _ = read_index(run)
        prompt = (run / index["packets"][0]["prompt_path"]).read_bytes()
        self.assertNotIn(b"SYNTHETIC-SOURCE", prompt)
        self.assertNotIn(b"SYNTHETIC hidden metadata", prompt)

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

    def test_legacy_single_file_packet_bytes_and_schema_are_unchanged(self):
        expected = ("Answer the single user request below. Return only your answer. "
                    "Do not access other evaluation cases, answer keys, reviewer rubrics, or previous responses. "
                    "If general style guidance conflicts with the user's explicit request, follow the user's request.\n\n"
                    "## General explanation guidance\n\nSYNTHETIC guidance only.\n\n\n"
                    "## User request\n\nSYNTHETIC: explain briefly. <script>alert('prompt')</script>\n").encode("utf-8")
        self.assertEqual((self.run / self.packet["prompt_path"]).read_bytes(), expected)
        self.assertEqual(self.index["schema_version"], 1)
        self.assertNotIn("runtime_resources", self.packet)
        self.assertNotIn("bundle_sha256", self.add_response())

    def test_bundle_freezes_exact_runtime_bytes_and_excludes_repository_material(self):
        source = self.bundle_source()
        (source / "README.md").write_text("SYNTHETIC LEAK README", encoding="utf-8")
        (source / "evals").mkdir()
        (source / "evals" / "rubric.md").write_text("SYNTHETIC LEAK RUBRIC", encoding="utf-8")
        (source / "references" / "unused.json").write_text("SYNTHETIC LEAK JSON", encoding="utf-8")
        (source / "references" / "nested").mkdir()
        (source / "references" / "nested" / "answers.md").write_text("SYNTHETIC LEAK ANSWERS", encoding="utf-8")
        run, packet, cases = self.bundle_run(source)
        resources = packet["runtime_resources"]
        self.assertEqual({resource["resource_path"] for resource in resources},
                         {"SKILL.md", "references/guide.md", "references/second.md"})
        prompt = (run / packet["prompt_path"]).read_bytes()
        self.assertNotIn(b"SYNTHETIC LEAK", prompt)
        for resource in resources:
            original = (source / resource["resource_path"]).read_bytes()
            self.assertEqual((run / resource["frozen_path"]).read_bytes(), original)
            self.assertEqual(resource["sha256"], sha(original))
            self.assertEqual(resource["bytes"], len(original))
            self.assertIn(original, prompt)
        (source / "references" / "guide.md").write_bytes(b"SYNTHETIC later source edit")
        self.assertEqual(packet_integrity(run, packet, cases[packet["case_id"]]), [])
        meta = collect(run, packet, cases[packet["case_id"]], b"SYNTHETIC bundle answer.\r\n", {})
        self.assertEqual(meta["bundle_sha256"], packet["bundle_sha256"])
        self.assertEqual(meta["guidance_mode"], BUNDLE_MODE)
        self.assertTrue(evaluate(run)["results"][0]["deterministic_pass"])

    def test_cli_accepts_bundle_only_and_mixed_variants_and_requires_a_source(self):
        source = self.bundle_source()
        base = ["packets", "--cases", str(self.root / "cases.json")]
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(base + ["--out", str(self.root / "only"), "--bundle", f"new={source}"]), 0)
            self.assertEqual(main(base + ["--out", str(self.root / "mixed"), "--skill", "baseline=none",
                                         "--skill", f"old={self.root / 'skill.md'}", "--bundle", f"new={source}"]), 0)
            self.assertEqual(main(base + ["--out", str(self.root / "empty")]), 2)
        index, _ = read_index(self.root / "mixed")
        self.assertEqual({packet["variant"] for packet in index["packets"]}, {"baseline", "old", "new"})
        self.assertFalse((self.root / "empty").exists())

    def test_bundle_help_and_index_state_injection_scope(self):
        run, _, _ = self.bundle_run()
        self.assertIn("not on-demand resource selection", json.loads((run / "index.json").read_bytes())["bundle_note"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["packets", "--help"])
        self.assertEqual(raised.exception.code, 0)
        self.assertIn("not on-demand", output.getvalue())

    def test_bundle_reference_tampering_missing_and_added_files_cannot_pass(self):
        source = self.bundle_source()
        for mutation in ("changed", "missing", "added"):
            with self.subTest(mutation=mutation):
                run, packet, cases = self.bundle_run(source, name=f"run-{mutation}")
                collect(run, packet, cases[packet["case_id"]], b"SYNTHETIC unchanged response.", {})
                reference = run / "skills" / "bundled" / "references" / "guide.md"
                if mutation == "changed":
                    reference.write_bytes(b"SYNTHETIC altered runtime guidance")
                elif mutation == "missing":
                    reference.unlink()
                else:
                    reference.with_name("extra.md").write_bytes(b"SYNTHETIC untracked guide")
                self.assertTrue(packet_integrity(run, packet, cases[packet["case_id"]]))
                with self.assertRaises(ValueError):
                    collect(run, packet, cases[packet["case_id"]], b"SYNTHETIC another response", {})
                record = evaluate(run)["results"][0]
                self.assertFalse(record["deterministic_pass"])
                self.assertFalse(record["fully_reviewed_pass"])

    @unittest.skipUnless(os.name == "posix", "Symlink fixture requires POSIX symlink support")
    def test_bundle_rejects_source_and_frozen_symlinks(self):
        for target in ("root", "ancestor", "skill", "references", "reference"):
            with self.subTest(target=target):
                source = self.bundle_source(f"source-{target}")
                if target == "root":
                    alias = self.root / "root-alias"
                    alias.symlink_to(source, target_is_directory=True)
                    source = alias
                elif target == "ancestor":
                    alias = self.root / "parent-alias"
                    alias.symlink_to(self.root, target_is_directory=True)
                    source = alias / source.name
                else:
                    path = {"skill": source / "SKILL.md", "references": source / "references",
                            "reference": source / "references" / "guide.md"}[target]
                    moved = path.with_name(path.name + ".real")
                    path.rename(moved)
                    path.symlink_to(moved, target_is_directory=moved.is_dir())
                with self.assertRaises(ValueError):
                    self.bundle_run(source, name=f"rejected-{target}")
        run, packet, cases = self.bundle_run(self.bundle_source("plain"))
        reference = run / "skills" / "bundled" / "references" / "guide.md"
        original = self.root / "unchanged-guide.md"
        original.write_bytes(reference.read_bytes())
        reference.unlink()
        reference.symlink_to(original)
        self.assertTrue(packet_integrity(run, packet, cases[packet["case_id"]]))

    def test_bundle_rejects_filename_and_variant_collisions(self):
        source = self.bundle_source()
        (source / "references" / "Guide.md").write_bytes(b"SYNTHETIC case-fold collision")
        with self.assertRaises(ValueError):
            self.bundle_run(source)
        (source / "references" / "Guide.md").unlink()
        args = argparse.Namespace(cases=str(self.root / "cases.json"), out=str(self.root / "collided"),
                                  skill=["same=none"], bundle=[f"SAME={source}"], split="all", ids=None, name=None)
        with self.assertRaises(ValueError):
            make_packets(args)
        self.assertFalse((self.root / "collided").exists())

    def test_bundle_rejects_nonruntime_reference_names_and_special_files(self):
        source = self.bundle_source()
        for name in ("README.md", "rubric.md", "answers.md", ".hidden.md", "unsafe name.md"):
            with self.subTest(name=name):
                path = source / "references" / name
                path.write_bytes(b"SYNTHETIC prohibited reference")
                with self.assertRaises(ValueError):
                    self.bundle_run(source)
                path.unlink()
        directory = source / "references" / "directory.md"
        directory.mkdir()
        with self.assertRaises(ValueError):
            self.bundle_run(source)

    def test_bundle_manifest_rejects_unsafe_paths_duplicates_and_incomplete_metadata(self):
        run, _, _ = self.bundle_run()
        original = (run / "index.json").read_bytes()
        for mutation in ("path", "duplicate", "missing-field", "hash", "no-root"):
            with self.subTest(mutation=mutation):
                index = json.loads(original)
                packet = index["packets"][0]
                if mutation == "path":
                    packet["runtime_resources"][0]["frozen_path"] = "../../outside.md"
                elif mutation == "duplicate":
                    packet["runtime_resources"].append(packet["runtime_resources"][0])
                elif mutation == "missing-field":
                    del packet["bundle_sha256"]
                elif mutation == "hash":
                    packet["bundle_sha256"] = "0" * 64
                else:
                    packet["runtime_resources"] = packet["runtime_resources"][1:]
                write_json(run / "index.json", index)
                with self.assertRaises(ValueError):
                    read_index(run)
        (run / "index.json").write_bytes(original)

    def test_bundle_metadata_hash_is_required_after_collection(self):
        run, packet, cases = self.bundle_run()
        collect(run, packet, cases[packet["case_id"]], b"SYNTHETIC bundle response.", {})
        _, meta_path = paths(run, packet)
        meta = json.loads(meta_path.read_bytes())
        del meta["bundle_sha256"]
        write_json(meta_path, meta)
        record = evaluate(run)["results"][0]
        self.assertIn("metadata bundle_sha256 mismatch", record["errors"])
        self.assertFalse(record["deterministic_pass"])

    def test_external_text_adapter_receives_exact_bundle_references(self):
        source = self.bundle_source()
        run, packet, _ = self.bundle_run(source)
        reference = (source / "references" / "guide.md").read_bytes()
        code = (f"import sys; prompt=sys.stdin.buffer.read(); assert {reference!r} in prompt; "
                "sys.stdout.buffer.write(b'SYNTHETIC exact bundle adapter response.\\r\\n')")
        args = argparse.Namespace(command_json=json.dumps([sys.executable, "-c", code]), timeout=5,
                                  run=str(run), variant=None, ids=None, skip_existing=False, model=None, cwd=None)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_adapter(args), 0)
        output, _ = paths(run, packet)
        self.assertEqual(output.read_bytes(), b"SYNTHETIC exact bundle adapter response.\r\n")
        self.assertTrue(evaluate(run)["results"][0]["deterministic_pass"])

    def test_multi_run_variant_cannot_mix_changed_bundles(self):
        source = self.bundle_source()
        first, first_packet, _ = self.bundle_run(source)
        second_cases = self.root / "disjoint-cases.json"
        write_json(second_cases, [dict(self.cases[0], id="SYNTH-02")])
        (source / "references" / "guide.md").write_bytes(b"SYNTHETIC changed reference with same root skill")
        second, second_packet, _ = self.bundle_run(source, name="other-bundle", cases=second_cases)
        self.assertEqual(first_packet["skill_sha256"], second_packet["skill_sha256"])
        self.assertNotEqual(first_packet["bundle_sha256"], second_packet["bundle_sha256"])
        with self.assertRaisesRegex(ValueError, "Different guidance"):
            evaluate_many([first, second])

    def test_blind_packets_keep_mapping_separate_and_preserve_exact_paired_responses(self):
        response = "SYNTHETIC café.\r\n\r\nExact trailing space.  \r\n".encode("utf-8")
        args = self.blind_packets(response=response, paired=True)
        index = json.loads((Path(args.out) / "index.json").read_bytes())
        key = json.loads(Path(args.key).read_bytes())
        self.assertEqual(len(index["packets"]), 2)
        self.assertEqual({entry["variant"] for entry in key["entries"]}, {"synthetic", "synthetic_other"})
        sources = {entry["review_id"]: entry for entry in key["entries"]}
        case_hashes = set()
        for descriptor in index["packets"]:
            packet = json.loads((Path(args.out) / descriptor["packet_path"]).read_bytes())
            self.assertNotIn("variant", packet)
            self.assertNotIn("metadata", packet)
            self.assertNotIn("skill_sha256", packet)
            self.assertEqual(sha(packet["response"].encode("utf-8")), sources[packet["review_id"]]["response_sha256"])
            case_hashes.add(packet["case_sha256"])
            if sources[packet["review_id"]]["variant"] == "synthetic":
                self.assertEqual(packet["response"].encode("utf-8"), response)
        self.assertEqual(len(case_hashes), 1)
        self.assertEqual((Path(args.out) / "rubric.json").read_bytes(), Path(args.rubric).read_bytes())
        self.assertNotIn(b"SYNTHETIC PRIVATE RUBRIC MARKER", (self.run / self.packet["prompt_path"]).read_bytes())

    def test_blind_review_roundtrip_supports_twelve_point_scores(self):
        args = self.finish_blind_reviews(self.blind_packets(paired=True))
        document = json.loads(Path(args.reviews).read_bytes())
        for review in document["reviews"]:
            review["evidence_grade"] = "SYNTHETIC SEPARATE EVIDENCE FIELD"
        write_json(args.reviews, document)
        with contextlib.redirect_stdout(io.StringIO()):
            import_blind_reviews(args)
        result = evaluate_many(args.run, args.out)
        self.assertTrue(all(record["fully_reviewed_pass"] for record in result["results"]))
        self.assertEqual({record["review"]["max_score"] for record in result["results"]}, {12})
        self.assertEqual({record["review"]["evidence_grade"] for record in result["results"]},
                         {"SYNTHETIC SEPARATE EVIDENCE FIELD"})
        self.assertIn("91.7%", render_report(result))

    def test_blind_review_export_rejects_missing_failed_and_stale_responses(self):
        args = argparse.Namespace(run=[self.run], out=str(self.root / "reviewer"),
                                  key=str(self.root / "private-key.json"), rubric=None)
        with self.assertRaises(ValueError):
            make_review_packets(args)
        self.assertFalse(Path(args.out).exists())
        self.add_response(status="command_error")
        with self.assertRaises(ValueError):
            make_review_packets(args)
        output, _ = paths(self.run, self.packet)
        output.write_bytes(b"SYNTHETIC stale output")
        with self.assertRaises(ValueError):
            make_review_packets(args)

    def test_blind_review_key_cannot_be_written_in_reviewer_directory(self):
        self.add_response()
        directory = self.root / "reviewer"
        args = argparse.Namespace(run=[self.run], out=str(directory), key=str(directory / "private.json"), rubric=None)
        with self.assertRaisesRegex(ValueError, "outside"):
            make_review_packets(args)
        self.assertFalse(directory.exists())

    def test_blind_review_import_rejects_unreviewed_unknown_duplicate_and_stale_reviews(self):
        args = self.finish_blind_reviews(self.blind_packets())
        original = Path(args.reviews).read_bytes()
        for mutation in ("unreviewed", "unknown", "duplicate", "stale"):
            with self.subTest(mutation=mutation):
                document = json.loads(original)
                if mutation == "unreviewed":
                    document["reviews"][0]["verdict"] = "UNREVIEWED"
                elif mutation == "unknown":
                    document["reviews"][0]["review_id"] = "UNKNOWN"
                elif mutation == "duplicate":
                    document["reviews"].append(document["reviews"][0])
                else:
                    document["reviews"][0]["response_sha256"] = "0" * 64
                write_json(args.reviews, document)
                with self.assertRaises(ValueError):
                    import_blind_reviews(args)
                self.assertFalse(Path(args.out).exists())

    def test_blind_review_import_rejects_altered_packet_rubric_index_or_key(self):
        exported = self.blind_packets()
        args = self.finish_blind_reviews(exported)
        directory = Path(args.packets)
        index = json.loads((directory / "index.json").read_bytes())
        for path in (directory / index["packets"][0]["packet_path"], directory / "rubric.json", directory / "index.json"):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b" ")
                with self.assertRaises(ValueError):
                    import_blind_reviews(args)
                path.write_bytes(original)
        key = json.loads(Path(args.key).read_bytes())
        key["entries"][0]["response_sha256"] = "0" * 64
        write_json(args.key, key)
        with self.assertRaises(ValueError):
            import_blind_reviews(args)
        self.assertFalse(Path(args.out).exists())

    def test_blind_review_import_rejects_changed_source_response(self):
        args = self.finish_blind_reviews(self.blind_packets())
        output, _ = paths(self.run, self.packet)
        output.write_bytes(b"SYNTHETIC changed after export")
        with self.assertRaises(ValueError):
            import_blind_reviews(args)
        self.assertFalse(Path(args.out).exists())

    def test_partial_blind_reviews_keep_unreviewed_coverage_visible(self):
        args = self.finish_blind_reviews(self.blind_packets(paired=True, rubric=False))
        document = json.loads(Path(args.reviews).read_bytes())
        document["reviews"] = document["reviews"][:1]
        write_json(args.reviews, document)
        with contextlib.redirect_stdout(io.StringIO()):
            import_blind_reviews(args)
        result = evaluate_many(args.run, args.out)
        self.assertEqual(sum(record["fully_reviewed_pass"] for record in result["results"]), 1)
        self.assertEqual(sum(record["review_state"] == "unreviewed" for record in result["results"]), 1)
        self.assertEqual(result["review_provenance"]["blind_review_provenance"]["reviewed"], 1)
        self.assertEqual(result["review_provenance"]["blind_review_provenance"]["scheduled"], 2)

    def test_blind_reviewer_score_does_not_override_mechanical_failure(self):
        args = self.finish_blind_reviews(self.blind_packets(response=b"SYNTHETIC " * 31))
        with contextlib.redirect_stdout(io.StringIO()):
            import_blind_reviews(args)
        record = evaluate(self.run, args.out)["results"][0]
        self.assertEqual(record["review_state"], "valid")
        self.assertEqual(record["review"]["score"], 11)
        self.assertFalse(record["deterministic_pass"])
        self.assertFalse(record["fully_reviewed_pass"])


if __name__ == "__main__":
    unittest.main()
