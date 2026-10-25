"""Run a provenance-preserving deletion audit from participant-visible inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

from core import AuditError, IdentityIndex, Policy, deletion_authorized, read_csv, timestamp, validate_output
from evidence import EvidenceStore, prefix_kind

ROOT = Path(__file__).resolve().parents[1]
REQUEST_FIELDS = ("case_id", "email", "requested_at", "reported_status", "reported_at", "audit_at", "request_text")


def source_digest():
    digest = hashlib.sha256()
    for path in sorted((ROOT / "code").rglob("*")):
        if path.is_file() and path.suffix in {".py", ".ps1", ".txt"}:
            digest.update(path.relative_to(ROOT).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def dataset_digest(dataset):
    """Fingerprint prediction inputs only; public answers never enter inference."""
    dataset = dataset.resolve()
    names = {"deletion_requests.csv", "user_identities.csv", "user_audit_log.csv", "system_activity.csv", "deletion_rules.csv", "evidence_files.csv"}
    manifest = read_csv(dataset / "evidence_files.csv", ("file_path",))
    for item in manifest:
        path = (dataset / item["file_path"]).resolve()
        if not path.is_relative_to(dataset / "evidence"):
            raise AuditError("Evidence path escapes participant evidence directory")
        names.add(path.relative_to(dataset).as_posix())
    digest = hashlib.sha256()
    for name in sorted(names):
        digest.update(name.encode() + b"\0")
        digest.update(hashlib.sha256((dataset / name).read_bytes()).digest())
    return digest.hexdigest()


def load_requests(path):
    rows = read_csv(path, REQUEST_FIELDS, "case_id")
    for row in rows:
        if "@" not in row["email"] or not row["request_text"].strip():
            raise AuditError("Request is missing email or text")
        requested, reported, audit = (timestamp(row[k]) for k in ("requested_at", "reported_at", "audit_at"))
        if requested > audit or reported < requested:
            raise AuditError("Inconsistent request chronology")
        if row["reported_status"] not in {"COMPLETE", "PARTIALLY_COMPLETE", "NOT_STARTED"}:
            raise AuditError("Invalid reported workflow status")
    return rows


def predict(requests, identities, store, policy):
    results, diagnostics = [], []
    for request in sorted(requests, key=lambda r: r["case_id"]):
        if not deletion_authorized(request["request_text"]):
            status, steps = "NOT_APPLICABLE", []
        else:
            cutoff = timestamp(request["audit_at"])
            user = identities.resolve(request["email"], cutoff)
            observations = store.current(user, cutoff)
            if not observations:
                # A catalog claim contradicted by an artifact is not permission
                # to delete another person's record. Request a future check only.
                claimed = store.claimed_resources(user, cutoff)
                steps = []
                for resource in sorted(claimed):
                    system, category = prefix_kind(resource)
                    if policy.actions.get(category) == "DELETE":
                        steps.append(dict(step_no=len(steps) + 1, phase="VERIFICATION", system_id=system, resource_id=resource, operation="VERIFY_RECORD_ABSENT", state="ABSENT", evidence_id=""))
                if not steps:
                    raise AuditError(f"{request['case_id']}: no attributable observations or safe verification targets at audit cutoff")
                status = "INCOMPLETE"
                diagnostics.append(f"{request['case_id']}: catalog attribution contradicted by artifact; verification-only plan, no record mutation authorized")
            else:
                status, steps = policy.plan(observations, cutoff)
            for obs in observations:
                if obs.state == "UNKNOWN":
                    diagnostics.append(f"{request['case_id']}: {obs.resource} state is unknown; proposed treatment requires verification")
            if not any(o.category == "USER_PROFILE" for o in observations):
                diagnostics.append(f"{request['case_id']}: no attributable account readback; completeness covers discovered resources only")
        results.append(dict(case_id=request["case_id"], deletion_status=status, steps_json=json.dumps(steps, ensure_ascii=False, separators=(",", ":"))))
    validate_output(results, requests, store.times)
    return results, diagnostics


def write_output(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Validate first; atomically replace to avoid publishing a partial submission.
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            writer = csv.DictWriter(stream, fieldnames=("case_id", "deletion_status", "steps_json"), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=ROOT / "dataset")
    parser.add_argument("--requests", type=Path, help="Request CSV; defaults to dataset/deletion_requests.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "output.csv")
    parser.add_argument("--cache", type=Path, default=ROOT / ".cache")
    parser.add_argument("--strict-coverage", action="store_true", help="Refuse output on missing account coverage or uncertain resource state")
    args = parser.parse_args()
    started = time.perf_counter()
    requests = load_requests(args.requests or args.dataset / "deletion_requests.csv")
    identities = IdentityIndex(args.dataset)
    store = EvidenceStore(args.dataset, identities, args.cache)
    rows, diagnostics = predict(requests, identities, store, Policy(args.dataset))
    if args.strict_coverage and diagnostics:
        affected = len({line.split(":", 1)[0] for line in diagnostics})
        raise AuditError(f"Strict coverage failed for {affected} requests; inspect evidence attribution")
    write_output(args.output, rows)
    stats = dict(requests=len(rows), statuses=dict(Counter(r["deletion_status"] for r in rows)), seconds=round(time.perf_counter() - started, 3), observations=len(store.observations), evidence_files=dict(store.counts), extraction=dict(store.extraction_stats), extraction_backends=dict(store.extraction_backends), coverage_warnings=diagnostics, identity_conflicts=store.identity_conflicts, output_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest(), source_sha256=source_digest(), requests_sha256=hashlib.sha256((args.requests or args.dataset / "deletion_requests.csv").read_bytes()).hexdigest(), model_calls=0, input_tokens=0, output_tokens=0, cost_usd=0)
    stats["dataset_sha256"] = dataset_digest(args.dataset)
    args.cache.mkdir(parents=True, exist_ok=True)
    (args.cache / "run_summary.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in stats.items() if k != "coverage_warnings"}, indent=2))
    print(f"Coverage/state warnings: {len(diagnostics)}. Output: {args.output.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except (AuditError, OSError, csv.Error, json.JSONDecodeError) as exc:
        print(f"Audit failed: {exc}", file=sys.stderr)
        sys.exit(1)
