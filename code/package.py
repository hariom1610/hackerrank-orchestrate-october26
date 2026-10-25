"""Build and inspect a reproducible source-only submission archive."""
import hashlib
import json
import zipfile
from pathlib import Path
from main import source_digest, dataset_digest

ROOT = Path(__file__).resolve().parents[1]
FILES = ["README.md", "code/main.py", "code/core.py", "code/evidence.py", "code/ocr_windows.ps1", "code/requirements.txt", "code/test_audit.py", "code/package.py", "code/TRACE_EXPORT.md", "code/INTERVIEW.md", "code/evaluation/main.py", "code/evaluation/diagnostics.py", "code/evaluation/baseline_metrics.md", "code/evaluation/evaluation_report.md", "code/evaluation/usage_report.md", "code/evaluation/failure_analysis.md"]


def preflight():
    run = json.loads((ROOT / ".cache/run_summary.json").read_text(encoding="utf-8"))
    output_hash = hashlib.sha256((ROOT / "output.csv").read_bytes()).hexdigest()
    if run.get("source_sha256") != source_digest() or run.get("output_sha256") != output_hash:
        raise ValueError("Source/output changed after the full run; rerun audit and evaluation before packaging")
    requests_hash = hashlib.sha256((ROOT / "dataset/deletion_requests.csv").read_bytes()).hexdigest()
    if run.get("requests_sha256") != requests_hash:
        raise ValueError("Request inputs changed after the full run")
    if run.get("dataset_sha256") != dataset_digest(ROOT / "dataset"):
        raise ValueError("Prediction evidence, rules, or identities changed after the full run")
    evaluation = json.loads((ROOT / ".cache/evaluation_summary.json").read_text(encoding="utf-8"))
    if evaluation.get("tests_passed") is not True:
        raise ValueError("Regression tests did not pass; rerun evaluation before packaging")
    if any(evaluation.get(key) != run.get(key) for key in ("source_sha256", "dataset_sha256", "output_sha256")):
        raise ValueError("Evaluation is not for the current source, dataset, and output")
    for name, expected in evaluation["sample_inputs"].items():
        if hashlib.sha256((ROOT / "dataset" / name).read_bytes()).hexdigest() != expected:
            raise ValueError("Public evaluation inputs changed; rerun evaluation")
    for name in ("evaluation_report.md", "usage_report.md", "failure_analysis.md"):
        text = (ROOT / "code/evaluation" / name).read_text(encoding="utf-8")
        if run["source_sha256"] not in text or (name != "failure_analysis.md" and output_hash not in text):
            raise ValueError("Evaluation/usage reports are stale; rerun evaluation before packaging")
        if hashlib.sha256((ROOT / "code/evaluation" / name).read_bytes()).hexdigest() != evaluation["report_hashes"][name]:
            raise ValueError("Evaluation/usage report changed after evaluation")


def main():
    preflight()
    archive = ROOT / "code.zip"
    entries = {name: ROOT / name for name in FILES}
    for report in ("evaluation_report.md", "usage_report.md"):
        entries[f"evaluation/{report}"] = ROOT / "code/evaluation" / report
    for name, source in entries.items():
        if not source.is_file():
            raise FileNotFoundError(f"Missing submission artifact: {name}")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, source in sorted(entries.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, source.read_bytes())
    with zipfile.ZipFile(archive) as output:
        if set(output.namelist()) != set(entries) or output.testzip() is not None:
            raise ValueError("Archive validation failed")
        if any(p.endswith((".zip", ".env", ".pyc")) or "dataset/" in p or "__pycache__" in p for p in output.namelist()):
            raise ValueError("Forbidden archive content")
    print(f"Verified {len(entries)} source/report entries: {archive}")
    print(f"SHA-256: {hashlib.sha256(archive.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
