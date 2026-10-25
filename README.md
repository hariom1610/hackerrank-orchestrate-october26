# HackerRank Orchestrate - October 2026

## Implemented auditor: setup, validation, and current limits

The implementation is in `code/`. It produces a **candidate** `output.csv` using
only participant-facing evidence. It has not achieved perfect public-sample
sequence accuracy and must not be represented as a guaranteed full-score or
production-certified solution. See `code/evaluation/evaluation_report.md` for
measured accuracy and case-level failures.

The generated review in `code/evaluation/failure_analysis.md` identifies resource
IDs required by public answers that do not occur in the prediction inputs.
The implementation uses the supplied dataset only and does not fill these gaps
from answer labels. General correctness fixes cover explicit source lineage,
per-replica state, identity cutoffs, tombstone references, and attachment policy.

Requires Python 3.11+ and the PDF dependency:

```text
python -m venv .venv
```

Activate the environment (`.venv\Scripts\Activate.ps1` on Windows, or
`source .venv/bin/activate` on macOS/Linux), then run:

```text
python -m pip install -r code/requirements.txt
python code/main.py
python -m unittest discover -s code -p test_audit.py -v
python code/evaluation/main.py
python code/package.py
```

Windows screenshot extraction uses the installed Windows OCR language model
through `Windows.Media.Ocr`. It requires an OCR language pack and access to the
OS OCR service. On macOS/Linux, install Tesseract and ensure `tesseract` is on
PATH. To select a different executable, set `AUDIT_TESSERACT_CMD` in the process
environment. No credentials or network model calls are needed. Do not commit
`.env` files. No machine-specific paths are embedded in source.

Input and output paths are relative to the repository, regardless of the shell's
working directory. CLI overrides: `--dataset`, `--requests`, `--output`, `--cache`.
PDF/OCR text is cached by source SHA-256 in `.cache/extracted/`; the cache is
excluded from submission packaging. A cold run re-extracts all 94 manifest
artifacts; it never needs cached predictions or public answer files.

For safety-critical use, run `python code/main.py --strict-coverage`. This fails
before replacing the output when account coverage or resource state is uncertain.
An attributed resource with no admissible state readback fails in either mode.
The default challenge command emits candidate answers for discovered resources
and records coverage/state warnings in `.cache/run_summary.json` and the
evaluation report. A COMPLETE candidate with a coverage warning is **not** a
deletion certificate. An observed backup without a restore-permission readback
receives a conservative block-and-verify plan without an invented risk finding.

The pipeline separates exact current/historical identity matching, evidence
adapters, temporal state reconstruction, policy planning, output validation, and
evaluation. Activity results never establish successful deletion. SQL runs only
in an isolated in-memory SQLite database with file attachment and file functions
denied. Output is validated before an atomic replacement. Steps use the exact
operation/system/resource order required by the problem statement.

Artifacts are read once and indexed in memory; the supplied dataset runs in a
few seconds with a warm extraction cache. This is an extensible audit engine,
not an enterprise deployment. Larger deployments need persistent temporal
indexes, inventory completeness attestations, authoritative subject lineage,
policy-condition adapters, stronger OCR/layout interpretation, and review of
unresolved evidence. Runtime inference is deterministic; AI-assisted screenshot
extraction uses local OCR. No generative language model is used in the current
runtime. Development model usage is separate from runtime usage.

`code/package.py` checks that source, all prediction inputs, public evaluation
inputs, output, and report fingerprints
match the recorded full run before creating `code.zip` from an explicit
allowlist and verifying its contents. Failed or unrecorded regression tests block packaging.
The evaluator regenerates the forensic failure analysis and before/after comparison;
`baseline_metrics.md` preserves the original measured aggregates. It includes reports in both `code/evaluation/` (README layout) and
`evaluation/` (problem-statement layout). It excludes datasets, generated
predictions, caches, credentials, transcripts, and nested archives. Upload root
`log.txt` separately as the chat transcript. The additional raw agent trace
requested by `agent_trace_instructions.md` must be finalized after this session
has ended and the app has flushed its trace; see `code/TRACE_EXPORT.md`.

## Ghost Data Still Exists

Build an AI agent that audits whether a user's personal data was actually deleted.

A deletion workflow may report **Complete** while data still exists in databases, logs, support attachments, exports, search indexes, archives, or backups. Sync and restore processes may also bring deleted data back.

For each request, the agent must first determine whether deletion was actually requested. It then returns `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`, reports any remaining data or recreation risk, and produces the ordered remediation and verification steps required to finish an authorized deletion safely.

Read [`problem_statement.md`](./problem_statement.md) for the complete challenge contract.

---

## Quick Start

Clone the repository and move into the project directory:

```bash
git clone https://github.com/interviewstreet/hackerrank-orchestrate-october26.git
cd hackerrank-orchestrate-october26
```

Start your AI coding tool from the **repository root** so it automatically reads [`AGENTS.md`](./AGENTS.md) and logs your session turns to `log.txt` in the root directory.

Build your solution in `code/main.py`, or use another language and document its setup and run command clearly in your README.

Your solution must:

- Read the input files from `dataset/`
- Generate one prediction row for every request in `dataset/deletion_requests.csv`
- Write the final predictions to `output.csv` in the repository root

Run the starter Python entry point with:

```bash
python3 code/main.py
```

The blank template at `dataset/output.csv` is provided as a reference. Your final generated file for submission must be the root-level `output.csv`.


## Dataset

All participant-facing files are in `dataset/`:

| File | Contents |
| --- | --- |
| `deletion_requests.csv` | 518 requests |
| `sample_deletion_requests.csv` | 32 sample requests |
| `sample_output.csv` | Correct sample answers |
| `user_identities.csv` | Current user identities |
| `user_audit_log.csv` | Historical identity changes |
| `system_activity.csv` | Activity across services and data processes |
| `deletion_rules.csv` | Required treatment for each data category |
| `evidence_files.csv` | Manifest of supplied evidence files |
| `output.csv` | Blank output template |

Evidence is stored under `dataset/evidence/` and may include PDFs, images, logs, JSON, plain text, or SQL snapshot exports. SQL captures may contain a primary database, regional replicas, a reporting replica, or a failover replica so replication drift can be investigated directly. The `.sql` files are readable as text and executable with SQLite.

Only `deletion_requests.csv` requires answers. The other files provide evidence and context.

---

## Output

Create `output.csv` with these columns in this exact order:

```text
case_id,deletion_status,steps_json
```

Produce exactly one row per request. `deletion_status` is `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`. `steps_json` is an ordered JSON array containing findings, remediation actions, and verification checks. Use an empty array (`[]`) for `NOT_APPLICABLE`. Evidence references may be a `file_id`, `activity_id`, or `audit_id`. Determine the resource state at `audit_at` from the available evidence; reported workflow statuses and operation results are claims. Use `dataset/sample_output.csv` as the format reference.

The final file must contain 518 data rows sorted by `case_id` (plus the header row). The grader parses `steps_json` as JSON, so object-key order and whitespace do not matter; array order does. Order findings, remediation, and verification in that phase order. Within a phase, follow the operation order in the problem statement, then sort by `system_id` and `resource_id`.

---

## Evaluation

`output.csv` will be compared with hidden canonical answers. Scoring considers:

- deletion assessment accuracy;
- current and historical identity resolution;
- discovery of remaining data and recreation risks;
- correct policy application and evidence references; and
- completeness and ordering of remediation and verification steps.

Your `code.zip` must include:

```text
code/evaluation/evaluation_report.md
code/evaluation/usage_report.md
```

- `evaluation_report.md` must cover case, row, field, and sequence accuracy, at least three additional evaluation cases created by you, failures found, and improvements made.
- `usage_report.md` must cover the final full-dataset run, including model providers and names, model calls, input and output tokens, total and average tokens per request, and estimated total and per-request cost. Include per-model and overall totals when using multiple models.

**Important:** Place `evaluation_report.md` and `usage_report.md` inside `code/evaluation/` (matching `code/evaluation/main.py` in this starter layout), write your complete evaluation metrics, custom evaluation test cases, and token/cost breakdowns directly inside those Markdown files, and keep prompts in source code or Markdown files. Automated code evaluation ignores raw data files (`.csv`, `.tsv`, `.json`, `.jsonl`, `.sql`, `.log`), so content stored only in those formats will not be visible to the code judge or AI interviewer.

---

## Chat Transcript

This repository includes [`AGENTS.md`](./AGENTS.md), which instructs compatible AI coding tools to append conversation summaries to `log.txt` in the repository root:

| Platform | Path |
| --- | --- |
| macOS / Linux | `<repo root>/log.txt` |
| Windows | `<repo root>\log.txt` |

- Always launch your AI coding agent from the repository root (or explicitly ask it to read `./AGENTS.md` first) so every turn is logged to `log.txt` with the required `User Prompt`, `Agent Response Summary`, `Actions`, and `Context` sections.
- Upload `log.txt` directly as your `chat_transcript` submission on HackerRank.
- Do not include API keys, tokens, credentials, or secrets in prompts, code, configuration, or `log.txt`.

---

## Packaging `code.zip` and Submission

| Item | Description |
| --- | --- |
| `code.zip` | Runnable solution, prompts, configuration, `README.md`, and `evaluation/` reports |
| `output.csv` | One answer row for each of the 518 requests in `dataset/deletion_requests.csv` |
| `chat_transcript` | The root `log.txt` file generated by your coding agent |
| AI interview | Live explanation of your architecture, approach, and evaluation |

You may use any programming language, model, framework, or retrieval approach. Include clear setup and execution instructions in `README.md` inside `code.zip`.

To package `code.zip` from the repository root without bundling the dataset:

**macOS / Linux:**

```bash
zip -r code.zip README.md code -x "*/__pycache__/*" "*/.venv/*" "*/venv/*" "*/node_modules/*" "*/.git/*" "*/.DS_Store"
```

**Windows (PowerShell):**

```powershell
Compress-Archive -Path README.md, code -DestinationPath code.zip -Force
```

When packaging `code.zip`:

- Keep your evaluation reports in `code/evaluation/` so they are bundled automatically with `code` (or add `evaluation` to the archive command above if you placed them in a top-level `evaluation/` directory).
- Do **not** include `dataset/`, virtual environments (`.venv`, `venv`, `node_modules`), or build caches (`__pycache__`). On Windows, keep `.venv` at the repository root (outside `code/`) and remove any `code/__pycache__` folders before running `Compress-Archive`.
- Do **not** include nested archives (`.zip`, `.tar`, `.gz`, `.tgz`, `.7z`, `.rar`) inside `code.zip` — submissions containing nested archive files will be rejected.

Before submitting, confirm that:

- `output.csv` has the exact header `case_id,deletion_status,steps_json` and contains all 518 data rows sorted by `case_id`;
- every `steps_json` value is a valid JSON array with consecutive step numbers starting at `1`;
- findings cite valid evidence IDs, and `COMPLETE` verification steps cite evidence proving the current state;
- proposed remediation and future verification steps use an empty `evidence_id` (`""`);
- `code.zip` includes your runnable code, `README.md`, `code/evaluation/evaluation_report.md`, and `code/evaluation/usage_report.md`;
- `log.txt` follows the `AGENTS.md` turn format and is uploaded to the `chat_transcript` slot; and
- no API keys, credentials, real personal data, or sensitive configuration values are included.
