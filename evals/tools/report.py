"""Render plain response text safely; no external resources or Markdown execution."""
from __future__ import annotations

from collections import defaultdict
from html import escape
from itertools import combinations
import json


def e(value):
    return escape(str(value), quote=True)


def table(headers, rows):
    return ("<table><thead><tr>" + "".join(f"<th>{e(h)}</th>" for h in headers) + "</tr></thead><tbody>"
            + "".join("<tr>" + "".join(f"<td>{e(v)}</td>" for v in row) + "</tr>" for row in rows)
            + "</tbody></table>")


def score(record):
    review = record["review"]
    if record["review_state"] != "valid" or "score" not in review:
        return None
    return review["score"] / review["max_score"] * 100


def render_report(result):
    records = result["results"]
    by_variant, by_case = defaultdict(list), defaultdict(dict)
    for record in records:
        by_variant[record["variant"]].append(record)
        by_case[record["case_id"]][record["variant"]] = record
    summaries = []
    splits = sorted({r["case"]["split"] for r in records})
    for variant, all_entries in by_variant.items():
        for split in splits:
            entries = [r for r in all_entries if r["case"]["split"] == split]
            if not entries:
                continue
            reviewed = [r for r in entries if r["review_state"] == "valid"]
            scored = [score(r) for r in entries if score(r) is not None]
            summaries.append([variant, split, len(entries), sum(bool(r["response_sha256"]) for r in entries),
                              f"{sum(r['deterministic_pass'] for r in entries)}/{len(entries)}",
                              f"{len(reviewed)}/{len(entries)}",
                              f"{sum(r['fully_reviewed_pass'] for r in entries)}/{len(entries)}" if reviewed else "Unreviewed",
                              f"{sum(scored) / len(scored):.1f}% ({len(scored)} scored)" if scored else "No review score"])
    pair_rows = []
    for left, right in combinations(by_variant, 2):
        for split in splits:
            pairs = [(v[left], v[right]) for v in by_case.values() if left in v and right in v and v[left]["case"]["split"] == split]
            scored = [(score(a), score(b)) for a, b in pairs if score(a) is not None and score(b) is not None and a["review"]["max_score"] == b["review"]["max_score"]]
            deltas = [b - a for a, b in scored]
            verdict_pairs = [(a, b) for a, b in pairs if a["review_state"] == b["review_state"] == "valid"]
            both_pass = sum(a["fully_reviewed_pass"] and b["fully_reviewed_pass"] for a, b in verdict_pairs)
            pair_rows.append([f"{right} vs {left}", split, len(pairs), len(verdict_pairs), both_pass,
                              f"{sum(deltas) / len(deltas):+.1f} percentage points ({len(deltas)} pairs)" if deltas else "No comparable paired review scores"])
    sections = []
    for case_id, variants in by_case.items():
        case = next(iter(variants.values()))["case"]
        content = [f"<section id='{e(case_id)}'><h2>{e(case_id)} · {e(case['category'])}</h2>",
                   f"<p class='label'>{e(case['split'])}</p><h3>User request</h3><pre>{e(case['prompt'])}</pre>"]
        for variant, record in variants.items():
            deterministic = "PASS" if record["deterministic_pass"] else "FAIL"
            review = record["review"]
            semantic = review["verdict"].upper() if record["review_state"] == "valid" else record["review_state"].upper()
            content.append(f"<details><summary>{e(variant)} · deterministic {deterministic} · review {e(semantic)} · {record['word_count']} words</summary>")
            if record["errors"]:
                content.append("<div class='errors'><strong>Record problems</strong><ul>" + "".join(f"<li>{e(v)}</li>" for v in record["errors"]) + "</ul></div>")
            if record["checks"]:
                rows = []
                for check in record["checks"]:
                    outcome = "Pass" if check["passed"] is True else "Fail" if check["passed"] is False else "Review required"
                    rows.append([check["constraint"], check["expected"], check.get("observed", "—"), outcome, check["kind"]])
                content.append(table(["Constraint", "Expected", "Observed", "Result", "Method"], rows))
            content.append(f"<h3>Raw response</h3><pre class='response'>{e(record['response']) if record['response'] else '[No response]'}</pre>")
            content.append(f"<p class='hash'>Response SHA-256: {e(record['response_sha256'] or 'missing')}</p>")
            if review:
                content.append(f"<h3>Separate semantic review</h3><p>{e(review['rationale'])}</p>")
                if "score" in review:
                    label = "Reviewer score" if record["review_state"] == "valid" else "INVALID REVIEW — excluded score"
                    content.append(f"<p><strong>{label}: {e(review['score'])}/{e(review['max_score'])}</strong></p>")
                criteria = review.get("criteria", [])
                if criteria:
                    content.append(table(["Criterion", "Verdict", "Notes"], [[c.get("criterion", ""), c.get("verdict", ""), c.get("notes", "")] for c in criteria]))
            else:
                content.append("<p class='muted'>No semantic review exists for this response. Format compliance is not a quality score.</p>")
            content.append(f"<details><summary>Response provenance</summary><pre>{e(json.dumps(record['metadata'], ensure_ascii=False, indent=2))}</pre></details></details>")
        content.append("</section>")
        sections.append("".join(content))
    css = """
    :root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#162431;background:#f2f5f7;line-height:1.5}
    body{max-width:1280px;margin:0 auto;padding:34px 24px 80px}h1{font-size:2.2rem;line-height:1.1}h2{margin-top:0}h3{font-size:1rem}
    header,section,.overview{background:white;border:1px solid #d6dfe5;border-radius:12px;padding:24px;margin:0 0 24px}
    .label{font-size:.8rem;text-transform:uppercase;letter-spacing:.08em;color:#536b7c}.muted,.hash{color:#536b7c}
    .hash{font-family:ui-monospace,monospace;font-size:.75rem;overflow-wrap:anywhere}table{border-collapse:collapse;width:100%;font-size:.9rem;display:block;overflow-x:auto;margin:16px 0}
    th,td{border:1px solid #d6dfe5;padding:9px 12px;text-align:left;vertical-align:top}th{background:#ecf2f6}
    pre{white-space:pre-wrap;overflow-wrap:anywhere;font:14px/1.65 ui-monospace,SFMono-Regular,monospace;background:#f5f7f9;border-radius:7px;padding:16px}
    .response{border-left:4px solid #4c7693;background:#fbfcfd}details{border:1px solid #dae3e9;border-radius:8px;padding:16px;margin:14px 0}
    summary{cursor:pointer;font-weight:650}details>details{background:#f8fafb}.errors{color:#8c2121;background:#fff2f0;padding:12px;margin-top:14px}
    nav{display:flex;flex-wrap:wrap;gap:8px}nav a{color:#275773;background:#edf3f7;border-radius:4px;padding:4px 9px;text-decoration:none}
    @media print{body{padding:0;background:white}details{break-inside:avoid}.overview,header,section{border:none}nav{display:none}}
    """
    header = (f"<header><p class='label'>Explanation evaluation</p><h1>{e(result.get('run_name') or 'Evaluation report')}</h1>"
              f"<p>Generated {e(result['generated_at'])}. Every response below is preserved as plain text.</p>"
              "<p>Deterministic checks cover record integrity, word limits, and detected Markdown tables. Sentence counts are heuristic; language, correctness, usefulness, and other semantic requirements need a separate review. Missing or invalid responses cannot pass.</p>"
              "<nav>" + "".join(f"<a href='#{e(cid)}'>{e(cid)}</a>" for cid in by_case) + "</nav></header>")
    overview = ("<div class='overview'><h2>Version comparison</h2>"
                + table(["Variant", "Split", "Cases", "Present", "Deterministic pass", "Valid reviews", "Fully reviewed pass", "Reviewer score mean"], summaries)
                + "<p>Scores are supplied by reviewers and normalized per case to a percentage. Means include only valid, scored reviews; coverage is shown. Variants evaluated on different case sets cannot be ranked by these means; use the matched-case comparisons below. No quality score is inferred from format checks.</p>"
                + table(["Comparison", "Split", "Common cases", "Reviewed pairs", "Both fully pass", "Mean paired score difference"], pair_rows)
                + "<h3>Review provenance</h3><pre>" + e(json.dumps(result["review_provenance"], ensure_ascii=False, indent=2)) + "</pre></div>")
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'\">"
            f"<title>{e(result.get('run_name') or 'Evaluation report')}</title><style>{css}</style></head><body>"
            + header + overview + "".join(sections) + "</body></html>\n")
