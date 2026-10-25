"""Evaluator-only forensic comparison; public labels never create inference edges."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import AuditError, FIELDS, OPERATIONS, TOKEN, IdentityIndex, Policy, normalize, read_csv, timestamp, validate_output
from evidence import EvidenceStore
from main import ROOT, dataset_digest, load_requests, predict, source_digest


def semantic_key(step):
    return json.dumps({key: value for key, value in step.items() if key != "step_no"}, sort_keys=True, ensure_ascii=False)


def _difference(left, right):
    remaining = Counter(semantic_key(step) for step in right)
    result = []
    for step in left:
        key = semantic_key(step)
        if remaining[key]:
            remaining[key] -= 1
        else:
            result.append(step)
    return result


def _redacted_preview(text):
    return TOKEN.sub(lambda match: match[0] if match[0].startswith("user_") else "[identifier]", text.strip())[:240]


def source_occurrences(dataset, store, targets):
    """Search actual prediction inputs and checked extraction text, never labels."""
    manifest = read_csv(dataset / "evidence_files.csv", ("file_id", "file_path", "captured_at"))
    sources = []
    names = ("deletion_requests.csv", "sample_deletion_requests.csv", "user_identities.csv", "user_audit_log.csv", "system_activity.csv", "deletion_rules.csv", "evidence_files.csv")
    for name in names:
        path = dataset / name
        text = path.read_text(encoding="utf-8-sig")
        csv_rows = list(__import__("csv").DictReader(text.splitlines()))
        sources.append((name, text, None, None, csv_rows))
    for item in manifest:
        path = (dataset / item["file_path"]).resolve()
        if not path.is_relative_to(dataset.resolve() / "evidence"):
            raise AuditError("Diagnostic evidence path escapes dataset/evidence")
        if path.suffix in {".pdf", ".png"}:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            extracted = store.cache / "extracted" / f"{digest}.txt"
            if not extracted.is_file():
                raise AuditError("Evidence must be extracted by the production adapter before forensic scanning")
            text = extracted.read_text(encoding="utf-8")
            representation = "PDF text" if path.suffix == ".pdf" else "OCR text"
        else:
            text = path.read_text(encoding="utf-8-sig")
            representation = "source text"
        sources.append((item["file_path"], text, item, representation, None))
    index = defaultdict(list)
    if not targets:
        return index, len(sources)
    pattern = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(target) for target in sorted(targets, key=lambda value: (-len(value), value))) + r")(?!\w)")
    for name, text, item, representation, csv_rows in sources:
        for line_number, line in enumerate(text.splitlines(), 1):
            identifiers = {match[0] for match in pattern.finditer(line)}
            if not identifiers:
                continue
            # CSV line numbers are informational; multiline request fields do
            # not establish a resource edge without an explicit parsed record.
            row = csv_rows[line_number - 2] if csv_rows is not None and 2 <= line_number <= len(csv_rows) + 1 else {}
            available = item["captured_at"] if item else row.get("event_time", row.get("requested_at", ""))
            evidence_id = item["file_id"] if item else row.get("activity_id", row.get("audit_id", ""))
            ref = dict(source=name, line=line_number, evidence_id=evidence_id, available_at=available, representation=representation or "CSV", preview=_redacted_preview(line))
            # These are diagnostic source facts, not edges inserted into store.
            ref["matched_users"] = sorted(store.identities.match(line))
            ref["matched_tokens"] = sorted(normalize(value) for value in TOKEN.findall(line))
            for resource in identifiers:
                index[resource].append(ref)
    return index, len(sources)


def _resource_facts(resource, user, cutoff, store, occurrences):
    observations = store.by_resource.get(resource, [])
    normalized = [dict(evidence_id=obs.evidence, category=obs.category, state=obs.state, system_id=obs.system, observed_at=obs.observed.isoformat(), available_at=obs.available.isoformat(), admissible=obs.observed <= cutoff and obs.available <= cutoff, replica=obs.replica, subject_in_record=user in store.identities.match(obs.payload)) for obs in observations]
    allowed = store.identities.available_values(user, cutoff)
    links = [dict(user_id=owner, available_at=available.isoformat(), admissible=available <= cutoff and bool(tokens & allowed)) for owner, available, tokens in store.links.get(resource, []) if owner == user]
    raw = []
    for occurrence in occurrences.get(resource, []):
        available = occurrence["available_at"]
        raw.append({key: value for key, value in occurrence.items() if key not in {"matched_tokens", "matched_users"}} | dict(subject_on_same_source_line=user in occurrence["matched_users"] and bool(set(occurrence["matched_tokens"]) & allowed), admissible_time=bool(available and timestamp(available) <= cutoff)))
    return dict(resource_id=resource, source_occurrences=raw, observations=normalized, subject_links=links, attributed_at_cutoff=resource in store.subject_resources(user, cutoff))


def _diagnose_missing(step, facts):
    raw, observations, links = (facts[key] for key in ("source_occurrences", "observations", "subject_links"))
    admissible = [obs for obs in observations if obs["admissible"]]
    valid_links = [link for link in links if link["admissible"]]
    owner_on_line = any(ref["subject_on_same_source_line"] and ref["admissible_time"] for ref in raw)
    if not raw:
        category, kind = "INPUT_UNDERDETERMINATION_ABSENT_ID", "C_MISSING_INPUT"
        reason = "The arbitrary expected resource identifier has no occurrence in any scanned prediction input or extracted artifact."
        fix = "Supply participant-visible resource/subject lineage; do not synthesize the identifier from labels or numbering."
    elif links and not valid_links:
        category, kind = "INPUT_UNDERDETERMINATION_LATE_LINEAGE", "C_MISSING_INPUT"
        reason = "Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically."
        fix = "Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact."
    elif observations and not admissible:
        category, kind = "INPUT_UNDERDETERMINATION_LATE_STATE", "C_MISSING_INPUT"
        reason = "Normalized state observations exist only after the observation/availability cutoff."
        fix = "Supply a state readback available by audit_at; do not backdate an artifact from its embedded event time."
    elif admissible and not facts["attributed_at_cutoff"]:
        if owner_on_line:
            category, kind = "BROKEN_RESOURCE_LINEAGE", "B_PRESENT_EVIDENCE_NOT_CONNECTED"
            reason = "An admissible source line contains both this identifier and subject identifiers, but graph attribution does not recover it."
            fix = "Inspect the cited adapter/identity filtering and preserve the explicit edge; add a regression before accepting a parser fix."
        else:
            category, kind = "INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE", "C_MISSING_INPUT"
            reason = "The state is observable, but the supplied admissible facts do not link the resource to this subject."
            fix = "Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge."
    elif facts["attributed_at_cutoff"] and admissible:
        category, kind = "ATTRIBUTED_STATE_OMITTED", "A_CODE_DEFECT_REQUIRING_REVIEW"
        reason = "Admissible state and subject attribution exist; the target was omitted from the emitted semantic plan."
        fix = "Trace current() selection, category resolution and Policy.plan(); emit only the final state supported by the cited source."
    elif facts["attributed_at_cutoff"]:
        category, kind = "KNOWN_RESOURCE_UNKNOWN_STATE", "A_CODE_DEFECT_REQUIRING_REVIEW"
        reason = "The inventory attributes the resource, but has no admissible state readback; the planner must retain that uncertainty."
        fix = "Prevent a subset-only COMPLETE result; preserve an explicit unknown-state diagnostic or a supported future check."
    elif owner_on_line:
        category, kind = "EXPLICIT_SOURCE_NOT_NORMALIZED", "B_PRESENT_EVIDENCE_NOT_CONNECTED"
        reason = "An admissible raw source associates resource and subject, but no state/attribution is normalized."
        fix = "Inspect the raw source's adapter; do not treat an operation-result claim as a resulting state readback."
    else:
        category, kind = "INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK", "C_MISSING_INPUT"
        reason = "The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check."
        fix = "Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it."
    return dict(category=category, root_cause_class=kind, reason=reason, responsible_functions=["EvidenceStore.link/claimed_resources/current", "Policy.plan"], smallest_defensible_fix=fix, expected_step=step, facts=facts)


def _diagnose_extra(step, facts):
    admissible = [obs for obs in facts["observations"] if obs["admissible"]]
    if facts["attributed_at_cutoff"] and admissible:
        return dict(category="REFERENCE_INVENTORY_CONFLICT", root_cause_class="REFERENCE_DISAGREEMENT_REQUIRING_REVIEW", reason="An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.", responsible_functions=["EvidenceStore.current", "Policy.plan"], smallest_defensible_fix="Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.", predicted_step=step, facts=facts)
    return dict(category="UNSUPPORTED_EXTRA_RESOURCE", root_cause_class="A_CODE_DEFECT_REQUIRING_REVIEW", reason="The predicted extra target lacks an admissible attributed state in the inspected inventory.", responsible_functions=["EvidenceStore.current", "Policy.plan"], smallest_defensible_fix="Trace the emitted provenance and remove an unsupported target or retain explicit uncertainty, with a regression test.", predicted_step=step, facts=facts)


def _metric_summary(cases, metrics):
    return dict(requests=len(cases), status_correct=sum(row["status_correct"] for row in cases), row_correct=sum(row["row_correct"] for row in cases), sequence_correct=sum(row["sequence_correct"] for row in cases), **metrics)


def comparison_rows(baseline, current):
    before = _metric_summary(baseline["cases"], baseline["metrics"]) if "cases" in baseline else baseline["metrics"]
    specifications = [("Case deletion-status accuracy", "status_correct", "requests"), ("Exact row accuracy", "row_correct", "requests"), ("Exact ordered sequence accuracy", "sequence_correct", "requests"), ("Exact step precision", "exact_steps", "predicted_steps"), ("Exact step recall", "exact_steps", "expected_steps"), ("Positional field accuracy", "field_correct", "field_total")]
    rows = []
    for label, numerator, denominator in specifications:
        a, b = (before.get(numerator, 0), before.get(denominator, 0)), (current.get(numerator, 0), current.get(denominator, 0))
        change = 100 * (b[0] / b[1] - a[0] / a[1]) if a[1] and b[1] else None
        rows.append(dict(metric=label, before=dict(numerator=a[0], denominator=a[1]), after=dict(numerator=b[0], denominator=b[1]), change_percentage_points=change))
    return rows


def write_baseline_metrics(baseline_path=None, output_path=None):
    """Freeze measured aggregates, never public case answers, for clean packages."""
    baseline_path = Path(baseline_path or ROOT / ".cache/master_baseline/metrics.json")
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    portable = dict(kind="independently_measured_public_baseline", source_sha256=baseline["source_sha256"], dataset_sha256=baseline.get("dataset_sha256"), output_sha256=baseline["output_sha256"], metrics=_metric_summary(baseline["cases"], baseline["metrics"]))
    lines = ["# Independently measured public baseline", "", "These aggregates were reproduced through the production predictor before the master-prompt fixes. They are evaluation metadata, not inference labels. No case answers or identity/resource mappings are stored here.", "", f"Baseline source SHA-256: `{portable['source_sha256']}`.", f"Baseline root output SHA-256: `{portable['output_sha256']}`.", f"Baseline prediction-input SHA-256: `{portable['dataset_sha256']}`.", "", "## Aggregate measurements", "", "```json", json.dumps(portable, indent=2), "```", "", "The evaluator-only diagnostic utility uses this aggregate block if the original disposable baseline cache is absent. Baseline figures are not replaced by the final run's measurements."]
    path = Path(output_path or ROOT / "code/evaluation/baseline_metrics.md")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return portable


def load_baseline(baseline_path=None):
    path = Path(baseline_path or ROOT / ".cache/master_baseline/metrics.json")
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    portable = ROOT / "code/evaluation/baseline_metrics.md"
    if portable.is_file():
        block = re.search(r"```json\s*\n(.*?)\n```", portable.read_text(encoding="utf-8"), re.S)
        if not block:
            raise AuditError("Portable baseline aggregate JSON block is missing")
        baseline = json.loads(block[1])
        if baseline.get("kind") != "independently_measured_public_baseline":
            raise AuditError("Invalid portable baseline metadata")
        return baseline
    return None


def build_failure_analysis(dataset, cache, *, store=None, baseline_path=None):
    dataset, cache = Path(dataset), Path(cache)
    identities = store.identities if store else IdentityIndex(dataset)
    store = store or EvidenceStore(dataset, identities, cache)
    policy = Policy(dataset)
    requests = load_requests(dataset / "sample_deletion_requests.csv")
    expected = {row["case_id"]: row for row in read_csv(dataset / "sample_output.csv", ("case_id", "deletion_status", "steps_json"), "case_id")}
    if set(expected) != {row["case_id"] for row in requests}:
        raise AuditError("Sample request/reference coverage mismatch in forensic analysis")
    cases, totals = [], Counter()
    phases = {phase: Counter() for phase in OPERATIONS}
    for request in requests:
        gold = expected[request["case_id"]]
        target, error, warnings = json.loads(gold["steps_json"]), "", []
        try:
            rows, warnings = predict([request], identities, store, policy)
            validate_output(rows, [request], store.times)
            status, actual = rows[0]["deletion_status"], json.loads(rows[0]["steps_json"])
        except AuditError as exc:
            status, actual, error = "UNRESOLVED", [], str(exc)
        exact_matches = sum((Counter(json.dumps(step, sort_keys=True) for step in target) & Counter(json.dumps(step, sort_keys=True) for step in actual)).values())
        totals.update(exact_steps=exact_matches, expected_steps=len(target), predicted_steps=len(actual))
        for index in range(max(len(target), len(actual))):
            a, b = target[index] if index < len(target) else {}, actual[index] if index < len(actual) else {}
            totals["field_total"] += len(FIELDS)
            totals["field_correct"] += sum(key in a and key in b and a[key] == b[key] for key in FIELDS)
        for phase in OPERATIONS:
            a = Counter(semantic_key(step) for step in target if step["phase"] == phase)
            b = Counter(semantic_key(step) for step in actual if step["phase"] == phase)
            phases[phase].update(expected=sum(a.values()), predicted=sum(b.values()), matched=sum((a & b).values()))
        status_correct, sequence_correct = status == gold["deletion_status"], not error and target == actual
        cases.append(dict(case_id=request["case_id"], request=request, expected_status=gold["deletion_status"], predicted_status=status, status_correct=status_correct, row_correct=status_correct and sequence_correct, sequence_correct=sequence_correct, expected_steps=target, predicted_steps=actual, error=error, coverage_warnings=warnings))
    targets = {step["resource_id"] for case in cases for step in case["expected_steps"] + case["predicted_steps"]}
    occurrences, source_count = source_occurrences(dataset, store, targets)
    for case in cases:
        cutoff = timestamp(case["request"]["audit_at"])
        try:
            user = identities.resolve(case["request"]["email"], cutoff)
        except AuditError:
            user = ""
        target, actual = case["expected_steps"], case["predicted_steps"]
        missing, extra = _difference(target, actual), _difference(actual, target)
        facts = {resource: _resource_facts(resource, user, cutoff, store, occurrences) for resource in {step["resource_id"] for step in missing + extra}} if user else {}
        diagnoses = [_diagnose_missing(step, facts[step["resource_id"]]) for step in missing] + [_diagnose_extra(step, facts[step["resource_id"]]) for step in extra] if user else []
        actual_by_key = {semantic_key(step): step for step in actual}
        shifts = [dict(resource_id=step["resource_id"], phase=step["phase"], operation=step["operation"], expected_step_no=step["step_no"], predicted_step_no=actual_by_key[semantic_key(step)]["step_no"]) for step in target if semantic_key(step) in actual_by_key and step["step_no"] != actual_by_key[semantic_key(step)]["step_no"]]
        same_inventory = Counter(map(semantic_key, target)) == Counter(map(semantic_key, actual))
        order_bug = same_inventory and [semantic_key(step) for step in target] != [semantic_key(step) for step in actual]
        # A shared resource/phase can differ in operation, state or citation.
        conflicts = []
        for a in missing:
            for b in extra:
                if (a["phase"], a["system_id"], a["resource_id"]) == (b["phase"], b["system_id"], b["resource_id"]):
                    changed = [key for key in FIELDS - {"step_no"} if a[key] != b[key]]
                    category = "INCORRECT_EVIDENCE_CITATION" if changed == ["evidence_id"] else "POLICY_OPERATION_OR_STATE_CONFLICT"
                    conflicts.append(dict(category=category, expected_step=a, predicted_step=b, changed_fields=sorted(changed), facts=facts[a["resource_id"]], responsible_functions=["EvidenceStore.current", "Policy.plan"], smallest_defensible_fix="Compare the cited admissible record/category and applicable rule before changing policy or citation selection; reference disagreement alone does not prove an engine defect."))
        case.update(semantic_missing_steps=missing, semantic_extra_steps=extra, diagnoses=diagnoses, field_conflicts=conflicts, numbering_shifts=shifts, incorrect_step_order=order_bug, completeness_coverage_risk=case["predicted_status"] == "COMPLETE" and bool(case["coverage_warnings"]))
        # Machine diagnostics retain full expected/predicted fields, but do not
        # duplicate the person's supplied email/text in exported reports.
        case["audit_at"] = case["request"]["audit_at"]
        case["subject_reference"] = user
        del case["request"]
    metrics = {**dict(totals), "phases": {phase: dict(counts) for phase, counts in phases.items()}}
    summary = _metric_summary(cases, metrics)
    baseline = load_baseline(baseline_path)
    result = dict(source_sha256=source_digest(), dataset_sha256=dataset_digest(dataset), sample_input_hashes={name: hashlib.sha256((dataset / name).read_bytes()).hexdigest() for name in ("sample_deletion_requests.csv", "sample_output.csv")}, scanned_prediction_sources=source_count, metrics=summary, cases=cases, diagnostic_categories=dict(Counter(diagnosis["category"] for case in cases for diagnosis in case["diagnoses"])), baseline_source_sha256=baseline.get("source_sha256") if baseline else None, comparison=comparison_rows(baseline, summary) if baseline else [])
    return result


def _ratio(value):
    a, b = value["numerator"], value["denominator"]
    return f"{a}/{b} ({100*a/b:.2f}%)" if b else f"{a}/{b} (N/A)"


def render_failure_analysis(data):
    lines = ["# Forensic public-sample failure analysis", "", f"Production source SHA-256: `{data['source_sha256']}`. Prediction-input SHA-256: `{data['dataset_sha256']}`.", "", f"All {len(data['cases'])} samples were executed through production predict() and validate_output(). {data['scanned_prediction_sources']} participant prediction/request sources were scanned, including production PDF/OCR text. Published answers and the blank output template were excluded from the source-occurrence scan. Labels are used only for comparison, never to populate an inference edge.", "", "## Before/after comparison", "", "The baseline is the independently saved metrics snapshot; values and percentage-point changes below are computed, not hand-edited. A diagnostic-only change can legitimately produce no public accuracy gain.", "", "| Metric | Before | After | Change |", "|---|---|---|---|"]
    for row in data["comparison"]:
        change = row["change_percentage_points"]
        lines.append(f"| {row['metric']} | {_ratio(row['before'])} | {_ratio(row['after'])} | {change:+.2f} pp |" if change is not None else f"| {row['metric']} | {_ratio(row['before'])} | {_ratio(row['after'])} | N/A |")
    lines += ["", "## Classification method", "", "A = a reproducible code defect requiring review; B = admissible source evidence not normalized/connected; C = unavailable or missing input. A reference-inventory disagreement is kept separate: an extra grounded resource must not be discarded merely because the published answer omits it. Late-only facts do not become admissible through an earlier embedded timestamp.", "", "A missing verification is a symptom. Each diagnosis below records raw occurrences, observed state, subject-link availability, responsible consumers, and the smallest defensible remedy. Numbering shifts caused by an inventory difference are separated from an actual ordering bug. Proposed classifications with a review qualifier are hypotheses to verify, not permission to change output to match labels.", "", "| Diagnosis | Count |", "|---|---:|"]
    lines += [f"| {category} | {count} |" for category, count in sorted(data["diagnostic_categories"].items())]
    lines += ["", "## Semantic phase diagnostics", "", "Only step_no is ignored; all other fields, including evidence, must match.", "", "| Phase | Matched | Predicted | Expected |", "|---|---:|---:|---:|"]
    lines += [f"| {phase} | {counts['matched']} | {counts['predicted']} | {counts['expected']} |" for phase, counts in data["metrics"]["phases"].items()]
    for case in data["cases"]:
        lines += ["", f"## {case['case_id']}", "", f"Status: expected **{case['expected_status']}**, production **{case['predicted_status']}**. Exact row: **{case['row_correct']}**. Audit cutoff: `{case['audit_at']}`. Missing semantic steps: {len(case['semantic_missing_steps'])}; extra semantic steps: {len(case['semantic_extra_steps'])}."]
        if case["error"]:
            lines.append(f"Production diagnostic: {case['error']}")
        if case["completeness_coverage_risk"]:
            lines.append("The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.")
        if not case["diagnoses"] and not case["field_conflicts"]:
            lines.append("No semantic discrepancy against the public reference was found.")
        for diagnosis in case["diagnoses"]:
            step = diagnosis.get("expected_step", diagnosis.get("predicted_step"))
            direction = "Missing expected" if "expected_step" in diagnosis else "Extra predicted"
            lines += ["", f"- **{direction}: {step['phase']} / {step['operation']} / {step['system_id']} / {step['resource_id']} / {step['state']}** (reference/predicted step {step['step_no']}; citation `{step['evidence_id']}`).", f"  Diagnosis: `{diagnosis['category']}`; class `{diagnosis['root_cause_class']}`. {diagnosis['reason']}", f"  Responsible consumers: {', '.join(diagnosis['responsible_functions'])}. Smallest defensible remedy: {diagnosis['smallest_defensible_fix']}"]
            facts = diagnosis["facts"]
            if facts["source_occurrences"]:
                refs = [f"{ref['evidence_id'] or ref['source']} ({ref['source']}:{ref['line']}; available {ref['available_at'] or 'not timestamped'})" for ref in facts["source_occurrences"][:4]]
                lines.append("  Source occurrences: " + "; ".join(refs) + (f"; {len(facts['source_occurrences'])-4} more recorded in machine diagnostics." if len(facts["source_occurrences"]) > 4 else "."))
            else:
                lines.append("  Source proof: no exact identifier occurrence in the scanned prediction inputs.")
            for obs in facts["observations"][:3]:
                lines.append(f"  Readback: {obs['evidence_id']}, {obs['category']}={obs['state']}, observed {obs['observed_at']}, available {obs['available_at']}, admissible={obs['admissible']}, subject-in-record={obs['subject_in_record']}.")
            if facts["subject_links"]:
                lines.append("  Subject-link availability: " + "; ".join(f"{link['available_at']} (admissible={link['admissible']})" for link in facts["subject_links"]) + ".")
        for conflict in case["field_conflicts"]:
            lines.append(f"Field conflict `{conflict['category']}` on {conflict['expected_step']['resource_id']}: {', '.join(conflict['changed_fields'])}. Inspect cited record and policy before treating the reference as authoritative evidence.")
        if case["numbering_shifts"]:
            shifts = "; ".join(f"{row['phase']}/{row['resource_id']}: expected #{row['expected_step_no']}, predicted #{row['predicted_step_no']}" for row in case["numbering_shifts"])
            lines.append("Numbering shifts on otherwise identical steps: " + shifts + ".")
        if case["incorrect_step_order"]:
            lines.append("INCORRECT_STEP_ORDER: semantic inventory matches but its sequence differs; inspect Policy.plan() sorting.")
        elif case["numbering_shifts"]:
            lines.append("These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.")
    lines += ["", "## Machine-readable companion", "", "`.cache/failure_analysis.json` retains all expected and actual step fields, source locations, normalized observations, cutoff decisions, diagnoses, and numbering shifts. It is evaluation-only and is never imported by production inference. Hidden-case correctness remains unmeasured."]
    return "\n".join(lines) + "\n"


def write_failure_analysis(dataset, cache, *, store=None, baseline_path=None, markdown_path=None, json_path=None):
    data = build_failure_analysis(dataset, cache, store=store, baseline_path=baseline_path)
    markdown_path = Path(markdown_path or ROOT / "code/evaluation/failure_analysis.md")
    json_path = Path(json_path or Path(cache) / "failure_analysis.json")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(render_failure_analysis(data), encoding="utf-8")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    args = parser.parse_args()
    result = write_failure_analysis(args.dataset, args.cache)
    print(json.dumps(dict(cases=len(result["cases"]), categories=result["diagnostic_categories"], metrics=result["metrics"]), indent=2))
