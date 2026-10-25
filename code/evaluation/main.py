"""Evaluate the production predictor against public samples without label leakage."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import AuditError, FIELDS, OPERATIONS, IdentityIndex, Policy, read_csv, validate_output
from evidence import EvidenceStore
from main import ROOT, load_requests, predict, source_digest, dataset_digest
from evaluation.diagnostics import write_failure_analysis


def canonical(step, *, ignore_step_no=False):
    fields = {key: value for key, value in step.items() if not (ignore_step_no and key == "step_no")}
    return json.dumps(fields, sort_keys=True, ensure_ascii=False)


def evaluate(dataset, cache):
    identities = IdentityIndex(dataset)
    store = EvidenceStore(dataset, identities, cache)
    policy = Policy(dataset)
    requests = load_requests(dataset / "sample_deletion_requests.csv")
    expected = {row["case_id"]: row for row in read_csv(dataset / "sample_output.csv", ("case_id", "deletion_status", "steps_json"), "case_id")}
    if set(expected) != {request["case_id"] for request in requests}:
        raise AuditError("Public sample requests and answers have different case coverage")
    results = []
    totals = Counter()
    phase_totals = {phase: Counter() for phase in OPERATIONS}
    for request in requests:
        gold = expected[request["case_id"]]
        target = json.loads(gold["steps_json"])
        error, diagnostics = "", []
        try:
            # Exercise the same entry point and validator used for output.csv.
            rows, diagnostics = predict([request], identities, store, policy)
            validate_output(rows, [request], store.times)
            status = rows[0]["deletion_status"]
            steps = json.loads(rows[0]["steps_json"])
        except AuditError as exc:
            status, steps, error = "UNRESOLVED", [], str(exc)
        matches = sum((Counter(map(canonical, target)) & Counter(map(canonical, steps))).values())
        totals.update(exact_steps=matches, expected_steps=len(target), predicted_steps=len(steps))
        for phase in OPERATIONS:
            expected_phase = Counter(canonical(step, ignore_step_no=True) for step in target if step["phase"] == phase)
            predicted_phase = Counter(canonical(step, ignore_step_no=True) for step in steps if step["phase"] == phase)
            phase_totals[phase].update(expected=sum(expected_phase.values()), predicted=sum(predicted_phase.values()), matched=sum((expected_phase & predicted_phase).values()))
        for index in range(max(len(target), len(steps))):
            a = target[index] if index < len(target) else {}
            b = steps[index] if index < len(steps) else {}
            totals["field_correct"] += sum(key in a and key in b and a[key] == b[key] for key in FIELDS)
            totals["field_total"] += len(FIELDS)
        status_correct = status == gold["deletion_status"]
        sequence_correct = not error and target == steps
        results.append(dict(case_id=request["case_id"], expected=gold["deletion_status"], actual=status, status_correct=status_correct, sequence_correct=sequence_correct, row_correct=status_correct and sequence_correct, expected_steps=len(target), actual_steps=len(steps), matching_steps=matches, error=error, coverage_warnings=diagnostics))
    return results, {**dict(totals), "phases": {phase: dict(counts) for phase, counts in phase_totals.items()}}, store


def percent(numerator, denominator):
    return f"{100 * numerator / denominator:.2f}%" if denominator else "N/A"


def verified_run_summary(dataset, cache, store):
    """A cached subset or stale output must not become the final-run usage report."""
    summary_path = cache / "run_summary.json"
    output_path = ROOT / "output.csv"
    if not summary_path.is_file() or not output_path.is_file():
        raise AuditError("A full-dataset run and root output.csv are required before reporting final-run usage")
    run = json.loads(summary_path.read_text(encoding="utf-8"))
    output_hash = hashlib.sha256(output_path.read_bytes()).hexdigest()
    if run.get("output_sha256") != output_hash:
        raise AuditError("Cached run summary does not match the SHA-256 of root output.csv; rerun the full audit")
    if run.get("source_sha256") != source_digest():
        raise AuditError("Source changed after the recorded full run; rerun the full audit")
    if run.get("requests_sha256") != hashlib.sha256((dataset / "deletion_requests.csv").read_bytes()).hexdigest():
        raise AuditError("Request inputs changed after the recorded full run")
    if run.get("dataset_sha256") != dataset_digest(dataset):
        raise AuditError("Prediction evidence, rules, or identities changed after the recorded full run")
    requests = load_requests(dataset / "deletion_requests.csv")
    rows = read_csv(output_path, ("case_id", "deletion_status", "steps_json"), "case_id")
    if run.get("requests") != len(requests) or len(rows) != len(requests):
        raise AuditError("Cached run summary is not for the complete evaluation request set")
    validate_output(rows, requests, store.times)
    if dict(Counter(row["deletion_status"] for row in rows)) != run.get("statuses"):
        raise AuditError("Cached run status totals do not match root output.csv")
    return run


def usage_report(run):
    count = run["requests"]
    input_tokens = run.get("input_tokens", 0)
    output_tokens = run.get("output_tokens", 0)
    total_tokens = input_tokens + output_tokens
    cost = run.get("cost_usd", 0)
    lines = [
        "# Final-run usage and cost report", "",
        f"Source SHA-256: `{run['source_sha256']}`. Request CSV SHA-256: `{run['requests_sha256']}`.", "",
        f"Verified full-dataset run: {count} requests; {run['observations']} normalized observations; {sum(run['evidence_files'].values())} evidence files. The summary's output SHA-256 matches root output.csv: `{run['output_sha256']}`. Elapsed extraction/index/prediction time: {run['seconds']} seconds. Extraction counters: {run.get('extraction', {})}.", "",
        "## Model/provider totals", "",
        "| Provider / component | Model or recorded backend | Calls in final run | Input tokens | Output tokens | Total tokens | Estimated API cost (USD) |",
        "|---|---|---:|---:|---:|---:|---:|",
        f"| Generative model provider | None (local pipeline selected by participant) | {run.get('model_calls', 0)} | {input_tokens} | {output_tokens} | {total_tokens} | {cost:.6f} |",
    ]
    backends = run.get("extraction_backends", {})
    for backend, metadata in sorted(backends.items()):
        calls = metadata.get("calls", 0) if isinstance(metadata, dict) else metadata
        model = metadata.get("model", backend) if isinstance(metadata, dict) else backend
        lines.append(f"| Local extraction: {backend} | {model} | {calls} | N/A | N/A | N/A | 0.000000 |")
    if not backends:
        lines.append("| Local extraction | No extraction backend recorded for this run; cached text may have been reused | 0 | N/A | N/A | N/A | 0.000000 |")
    lines += [
        f"| Overall token-based inference | None | {run.get('model_calls', 0)} | {input_tokens} | {output_tokens} | {total_tokens} | {cost:.6f} |", "",
        f"Average per request: {input_tokens / count:.6f} input tokens, {output_tokens / count:.6f} output tokens, {total_tokens / count:.6f} total tokens, and estimated API cost ${cost / count:.6f}. Overall estimated API cost is ${cost:.6f}. Local compute, electricity, development time, and operating-system licensing are excluded from API cost.", "",
        "PDF/OCR extraction is local and has no input/output token accounting. Cache hits are reported separately from new extraction calls; a warm run does not imply that OCR executed again. Cached text derives from supplied artifacts, never cached predictions or public answer labels. The backend table reports only the backend metadata recorded by the run; it does not assume Microsoft OCR when Tesseract or another adapter was used.", "",
        "Development harnesses and exact session model identifiers are recorded in root log.txt. Development token/cost totals are not measured by this audit pipeline and are not represented as zero. They are separate from runtime audit usage. No remote-model credentials are required or embedded in this local submission.",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    results, metrics, store = evaluate(args.dataset, args.cache)
    analysis = write_failure_analysis(args.dataset, args.cache, store=store)
    suite = unittest.defaultTestLoader.discover(str(ROOT / "code"), pattern="test_audit.py")
    tests = unittest.TextTestRunner(verbosity=1).run(suite)
    failed_methods = {getattr(test, "test_case", test).id() for test, _ in tests.failures + tests.errors}
    passed_methods = tests.testsRun - len(failed_methods) - len(tests.skipped)
    n = len(results)
    status_correct = sum(row["status_correct"] for row in results)
    sequence_correct = sum(row["sequence_correct"] for row in results)
    row_correct = sum(row["row_correct"] for row in results)
    report = [
        "# Evaluation report", "",
        f"Only the {n} public samples are labeled. Hidden evaluation accuracy is unknown; no hidden truth or generator internals are used. Expected sample answers are loaded exclusively by this evaluator. Each sample runs the production predict() entry point and its output validator; an AuditError counts as an UNRESOLVED failure.", "",
        "## Measured public-sample results", "",
        "| Metric | Result |", "|---|---|",
        f"| Case deletion-status accuracy | {status_correct}/{n} ({percent(status_correct,n)}) |",
        f"| Exact row accuracy (status and ordered steps) | {row_correct}/{n} ({percent(row_correct,n)}) |",
        f"| Exact ordered sequence accuracy | {sequence_correct}/{n} ({percent(sequence_correct,n)}) |",
        f"| Exact step precision | {metrics.get('exact_steps', 0)}/{metrics.get('predicted_steps', 0)} ({percent(metrics.get('exact_steps', 0),metrics.get('predicted_steps', 0))}) |",
        f"| Exact step recall | {metrics.get('exact_steps', 0)}/{metrics.get('expected_steps', 0)} ({percent(metrics.get('exact_steps', 0),metrics.get('expected_steps', 0))}) |",
        f"| Positional field accuracy | {metrics.get('field_correct', 0)}/{metrics.get('field_total', 0)} ({percent(metrics.get('field_correct', 0),metrics.get('field_total', 0))}) |",
        f"| Custom regression tests | {passed_methods}/{tests.testsRun} passed; {len(failed_methods)} failed; {len(tests.skipped)} skipped |", "",
        "Exact steps include all seven fields, including step number and evidence. Step precision/recall use multiset intersection. Positional field accuracy counts missing/extra steps as seven errors. Sequence accuracy requires ordered-step equality; exact row accuracy also requires the status to match. UNRESOLVED receives no credit for a guessed COMPLETE status.", "",
        "## Semantic phase diagnostics", "",
        "These supplementary diagnostics ignore only step_no, preserving every other field including the citation. They distinguish missing resources from the renumbering errors those omissions cause; they do not replace exact submission metrics.", "",
        "| Phase | Matched | Predicted | Expected | Precision | Recall |", "|---|---:|---:|---:|---:|---:|",
    ]
    for phase, counts in metrics["phases"].items():
        matched, predicted, expected = (counts.get(key, 0) for key in ("matched", "predicted", "expected"))
        report.append(f"| {phase} | {matched} | {predicted} | {expected} | {percent(matched,predicted)} | {percent(matched,expected)} |")
    report += ["", "## Measured before/after comparison", "", "Baseline aggregates were saved before the focused fixes; current values are computed through the production predictor. No hidden accuracy is inferred from these results.", "", "| Metric | Before | After | Change |", "|---|---|---|---|"]
    for comparison in analysis["comparison"]:
        before, after = comparison["before"], comparison["after"]
        a, b = before["numerator"], before["denominator"]
        c, d = after["numerator"], after["denominator"]
        change = comparison["change_percentage_points"]
        delta = f"{change:+.2f} pp" if change is not None else "N/A"
        report.append(f"| {comparison['metric']} | {a}/{b} ({percent(a,b)}) | {c}/{d} ({percent(c,d)}) | {delta} |")
    report += ["", "## Per-case results", "", "| Case | Expected | Predicted | Exact row | Exact sequence | Matched/expected steps |", "|---|---|---|---|---|---|"]
    report += [f"| {row['case_id']} | {row['expected']} | {row['actual']} | {row['row_correct']} | {row['sequence_correct']} | {row['matching_steps']}/{row['expected_steps']} |" for row in results]
    unresolved = [row for row in results if row["error"]]
    if unresolved:
        report += ["", "Unresolved production errors:", ""] + [f"- {row['case_id']}: {row['error']}" for row in unresolved]
    report += [
        "", "## Participant-created evaluation cases", "",
        "1. Active connector + unsafe backup + present profile: expect INCOMPLETE; disable the connector, block restore, then delete the profile. Future actions/checks have empty citations.",
        "2. A tombstone retaining its permitted stable subject reference with direct identifiers removed, plus a retained security event: verify redaction and retention. A surviving email hash prevents compliance.",
        "3. Marketing-only opt-out and explicit request not to delete: no deletion authorization. Spanish, Japanese and Korean deletion requests authorize deletion.",
        "4. A clean primary and exposed replica: replica exposure must prevent a false COMPLETE decision.",
        "5. Evidence captured after audit_at cannot alter an earlier state or provide a historical citation.",
        "6. SQL ATTACH is denied; atomic CSV output must preserve JSON and not publish a partial file.", "",
        "## Failures found and improvements made", "",
        "- The evaluator now runs the production predictor and validator rather than a separate approximation of inference.",
        "- Exact row and sequence accuracy are distinct; semantic phase diagnostics expose coverage failures without hiding exact numbering errors.",
        "- Output-hash, full request coverage, output-contract, and status-total checks prevent stale/subset run summaries from becoming final usage claims.",
        "- Evidence adapters distinguish record content from lookup context, keep observation/availability times, reconstruct trace links, and compare replicas. Regression tests exercise the implemented safeguards; passing tests do not prove hidden accuracy.", "",
        "- Conflicting explicit resource categories fail visibly instead of depending on evidence order. Known retention conditions survive later metadata-only readbacks.",
        "- Attributed resources without admissible state cannot silently disappear into a COMPLETE decision. UNKNOWN states produce explicit uncertainty diagnostics.",
        "- Shared identifiers alone cannot attribute a resource to either user; a unique admissible identifier is required before planning changes.",
        "- Evaluation records the regression-suite outcome, counts failed test methods rather than failed subcases, refreshes forensic comparisons, and prevents packaging after failed tests.", "",
        "## Remaining limitations", "",
        "This is not a guaranteed full-score or enterprise-certified solution. Remaining public-sample errors above must be resolved or explained before claiming readiness. Missing subject/resource lineage, uncertainty about complete inventory coverage, temporal conflicts, OCR layouts, and conditional policy interpretation require explicit treatment; no links may be invented from numeric resource suffixes, case order, shared report timestamps, case families, or sample labels.",
        "The mandated phase/operation/system/resource ordering is checked deterministically. For production, use strict coverage controls and authoritative lineage/inventory attestations rather than treating a discovered-resource-only answer as a deletion certificate. In-memory indexing is suitable for this dataset; larger deployments need persistent temporal storage and controlled ingestion.",
    ]
    if store.identity_conflicts:
        report += ["", "Artifact/catalog contradictions:", ""] + [f"- {line}" for line in store.identity_conflicts[:10]]
    run, run_error = None, ""
    try:
        run = verified_run_summary(args.dataset, args.cache, store)
    except AuditError as exc:
        run_error = str(exc)
    if run is not None:
        warnings = run.get("coverage_warnings", [])
        cases = {line.split(":", 1)[0] for line in warnings}
        strict_result = "PASS" if not warnings else f"FAIL ({len(cases)} affected requests)"
        report += ["", "## Verified full-dataset run", "", f"Rows: {run['requests']}. Status distribution: {run['statuses']}. Normalized observations: {run['observations']}. Parse/predict duration: {run['seconds']} seconds. Root output SHA-256: `{run['output_sha256']}`.", "", f"Coverage diagnostics: {len(warnings)} messages across {len(cases)} unique requests. Strict coverage criterion: {strict_result}, computed from the final run's diagnostics."]
        report += ["", f"Source SHA-256: `{run['source_sha256']}`. Request CSV SHA-256: `{run['requests_sha256']}`.", "", "See failure_analysis.md for every public mismatch, missing arbitrary resource IDs, unavailable subject lineage, responsible functions, and admissibility decisions. Such missing source facts cannot be reconstructed by copying sample answers or guessing identifier patterns."]
        if warnings:
            report += ["", "First ten coverage diagnostics:", ""] + [f"- {line}" for line in warnings[:10]]
    else:
        report += ["", "## Final-run verification failed", "", run_error]
    report_path = ROOT / "code/evaluation/evaluation_report.md"
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    args.cache.mkdir(parents=True, exist_ok=True)
    (args.cache / "sample_metrics.json").write_text(json.dumps(dict(cases=results, metrics=metrics), indent=2), encoding="utf-8")
    usage_path = ROOT / "code/evaluation/usage_report.md"
    usage_path.write_text(usage_report(run) if run is not None else f"# Usage report unavailable\n\n{run_error}\n\nRun the full audit to root output.csv, then rerun this evaluator. No unverified token/cost totals are asserted.\n", encoding="utf-8")
    if run is not None:
        failure_path = ROOT / "code/evaluation/failure_analysis.md"
        evaluation_summary = dict(source_sha256=run["source_sha256"], dataset_sha256=run["dataset_sha256"], output_sha256=run["output_sha256"], tests_passed=tests.wasSuccessful(), tests_run=tests.testsRun, tests_failed=len(failed_methods), tests_skipped=len(tests.skipped), sample_inputs={name: hashlib.sha256((args.dataset / name).read_bytes()).hexdigest() for name in ("sample_deletion_requests.csv", "sample_output.csv")}, report_hashes={path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in (report_path, usage_path, failure_path)})
        (args.cache / "evaluation_summary.json").write_text(json.dumps(evaluation_summary, indent=2), encoding="utf-8")
    print(f"Public status: {status_correct}/{n}; exact rows: {row_correct}/{n}; exact sequences: {sequence_correct}/{n}; report: {report_path}")
    if run_error:
        print(f"Final-run verification failed: {run_error}", file=sys.stderr)
    if not tests.wasSuccessful() or run_error:
        sys.exit(1)


if __name__ == "__main__":
    main()
