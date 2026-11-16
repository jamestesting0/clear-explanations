# Replay helper audit

## Conclusion

**No blocking defect found.** All **12 focused synthetic checks passed**. The replay helper preserves runtime bytes, restores the archived entry filename to `SKILL.md`, refuses existing destinations, and rejects the tested source and destination symlinks before writing output. No repository source files were edited.

**Confidence: 0.96** for the bounded, single-process helper behavior reviewed here.

## Scope and evidence

Reviewed these implementation interfaces only:

- `evals/advanced/materialize.py`: `materialize()` and `main()`.
- `evals/advanced/check.py`: `Archive`, `read_json`, `read_archive_bundle`, and `frozen_versions`.
- `evals/tools/core.py`: runtime filename validation and byte/hash/bundle helpers used by those interfaces. There is no `evals/advanced/core.py`; `check.py` imports the shared implementation from `evals/tools`.

No benchmark cases, model outputs, gold files, reviewer judgments, or actual skill text were inspected. The in-progress advanced archive was not read or validated. Missing `evidence.json` or `REPORT.md` was not treated as a defect.

The executed check used Python's `unittest` with a fresh `tempfile.TemporaryDirectory` per test. It imported the real replay helper and temporarily changed only its in-memory `ROOT` to a synthetic archive. Fixtures included an independently hashed UTF-8 entry with a BOM, CRLF line endings, and a non-ASCII character, plus a reference with no final newline. Every temporary fixture was removed by test teardown. The real archive was never passed to `Archive` or `frozen_versions`.

Execution result: `Ran 12 tests in 0.017s`, `OK`, process exit status `0`.

## Actual executed checks

| # | Check | Observed result |
|---|---|---|
| 1 | Materialize a bundled variant from archived `INSTRUCTIONS.md` into a new nested destination. | Returned exactly the expected runtime names; created canonical `SKILL.md` and the reference; every output byte matched the fixture; no `INSTRUCTIONS.md` output remained. |
| 2 | Materialize a single-file variant whose archived entry already uses `SKILL.md`. | Returned only `SKILL.md` and preserved its bytes. |
| 3 | Use an existing regular file as the destination. | Raised `ValueError`; the existing content remained byte-for-byte unchanged. |
| 4 | Use an existing directory containing a sentinel file as the destination. | Raised `ValueError`; no files were added and the sentinel remained unchanged. |
| 5 | Use either an existing-target or dangling symlink as the destination. | Rejected both links; links remained intact; no target content was created or changed. |
| 6 | Put the requested new destination beneath either an existing-target or dangling parent symlink. | Rejected both paths; no destination or missing target was created. |
| 7 | Request an unknown variant. | Raised the specific unknown-variant `ValueError`; no output directory was created. |
| 8 | Alter a recorded archived file after computing its inventory digest. | Rejected the changed file before creating any output. |
| 9 | Replace a recorded entry with a symlink to an in-archive file containing identical bytes. | Rejected the source symlink before creating any output. |
| 10 | Replace the source references directory with a symlink to another in-archive directory. | Rejected the intermediate source symlink before creating any output. |
| 11 | Add a direct Markdown runtime reference that is absent from the hash inventory. | Rejected the unrecorded reference before creating any output. |
| 12 | Call the real `main()` for a valid variant and an unknown variant. | Success returned `0`, reported two copied files, and emitted no stderr. Failure returned `1`, emitted the unknown-variant diagnostic on stderr, emitted no success text, and created no output. |

## Why the tested behavior is sound

All archive files declared in the hash inventory are read and checked before materialization starts. `frozen_versions` validates archived entry and bundle hashes and yields exact raw bytes. Resource names are restricted to canonical `SKILL.md` and direct allowed Markdown references, so a validated bundle cannot supply traversal paths to the output writer. The writer uses binary exclusive creation (`xb`), which preserves bytes and refuses an existing final file. Its destination and parent checks reject the static symlink cases exercised above.

## Key caveats

- This is a helper audit, not a validation of the completed advanced archive, its evidence, or benchmark results. No broad harness test run was performed.
- The filesystem checks assume paths are not changed concurrently by another process. The implementation performs preflight symlink checks and subsequent path-based writes; this audit does not certify resistance to an adversarial process replacing directories during materialization.
- Output creation is not transactional. An operating-system write error after destination creation can leave a partial new directory; a subsequent attempt will refuse that existing directory. This is an operational limitation, not a demonstrated violation of the current helper contract.

No code changes are requested on the evidence from this bounded audit.

## Reproducibility follow-up

At the parent task's request, the exact executed 12-test program was recovered from the retained command and saved as `clear-explanations/evals/advanced/test_materialize.py`. Only the machine-specific import path was replaced with `Path(__file__).resolve().parent`, and the existing `unittest.main(verbosity=2)` entry was placed under the standard `__main__` guard. All fixtures, test cases, and assertions remain semantically unchanged. The earlier statement that no repository source files were edited describes the initial audit; this follow-up added only that test file. No runtime, benchmark, or other harness files were changed.

Executed the retained file once from the repository root with:

```sh
python -B evals/advanced/test_materialize.py
```

Result: `Ran 12 tests in 0.015s`, `OK`, process exit status `0`. No additional test scope was introduced.
