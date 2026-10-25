# Evaluation report

Only the 32 public samples are labeled. Hidden evaluation accuracy is unknown; no hidden truth or generator internals are used. Expected sample answers are loaded exclusively by this evaluator. Each sample runs the production predict() entry point and its output validator; an AuditError counts as an UNRESOLVED failure.

## Measured public-sample results

| Metric | Result |
|---|---|
| Case deletion-status accuracy | 29/32 (90.62%) |
| Exact row accuracy (status and ordered steps) | 9/32 (28.12%) |
| Exact ordered sequence accuracy | 9/32 (28.12%) |
| Exact step precision | 114/164 (69.51%) |
| Exact step recall | 114/193 (59.07%) |
| Positional field accuracy | 957/1379 (69.40%) |
| Custom regression tests | 37/37 passed; 0 failed; 0 skipped |

Exact steps include all seven fields, including step number and evidence. Step precision/recall use multiset intersection. Positional field accuracy counts missing/extra steps as seven errors. Sequence accuracy requires ordered-step equality; exact row accuracy also requires the status to match. UNRESOLVED receives no credit for a guessed COMPLETE status.

## Semantic phase diagnostics

These supplementary diagnostics ignore only step_no, preserving every other field including the citation. They distinguish missing resources from the renumbering errors those omissions cause; they do not replace exact submission metrics.

| Phase | Matched | Predicted | Expected | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| FINDING | 41 | 42 | 41 | 97.62% | 100.00% |
| REMEDIATION | 41 | 42 | 41 | 97.62% | 100.00% |
| VERIFICATION | 77 | 80 | 111 | 96.25% | 69.37% |

## Measured before/after comparison

Baseline aggregates were saved before the focused fixes; current values are computed through the production predictor. No hidden accuracy is inferred from these results.

| Metric | Before | After | Change |
|---|---|---|---|
| Case deletion-status accuracy | 29/32 (90.62%) | 29/32 (90.62%) | +0.00 pp |
| Exact row accuracy | 9/32 (28.12%) | 9/32 (28.12%) | +0.00 pp |
| Exact ordered sequence accuracy | 9/32 (28.12%) | 9/32 (28.12%) | +0.00 pp |
| Exact step precision | 114/164 (69.51%) | 114/164 (69.51%) | +0.00 pp |
| Exact step recall | 114/193 (59.07%) | 114/193 (59.07%) | +0.00 pp |
| Positional field accuracy | 957/1379 (69.40%) | 957/1379 (69.40%) | +0.00 pp |

## Per-case results

| Case | Expected | Predicted | Exact row | Exact sequence | Matched/expected steps |
|---|---|---|---|---|---|
| case_01 | COMPLETE | UNRESOLVED | False | False | 0/1 |
| case_02 | COMPLETE | UNRESOLVED | False | False | 0/1 |
| case_03 | COMPLETE | COMPLETE | False | False | 2/3 |
| case_04 | COMPLETE | UNRESOLVED | False | False | 0/2 |
| case_05 | INCOMPLETE | INCOMPLETE | True | True | 3/3 |
| case_06 | INCOMPLETE | INCOMPLETE | True | True | 4/4 |
| case_07 | INCOMPLETE | INCOMPLETE | False | False | 0/4 |
| case_08 | INCOMPLETE | INCOMPLETE | False | False | 2/4 |
| case_09 | INCOMPLETE | INCOMPLETE | False | False | 2/5 |
| case_10 | INCOMPLETE | INCOMPLETE | False | False | 2/4 |
| case_11 | INCOMPLETE | INCOMPLETE | True | True | 14/14 |
| case_12 | INCOMPLETE | INCOMPLETE | True | True | 5/5 |
| case_13 | INCOMPLETE | INCOMPLETE | True | True | 8/8 |
| case_14 | INCOMPLETE | INCOMPLETE | True | True | 5/5 |
| case_15 | INCOMPLETE | INCOMPLETE | True | True | 5/5 |
| case_16 | INCOMPLETE | INCOMPLETE | True | True | 7/7 |
| case_17 | INCOMPLETE | INCOMPLETE | False | False | 3/5 |
| case_18 | INCOMPLETE | INCOMPLETE | False | False | 8/14 |
| case_19 | INCOMPLETE | INCOMPLETE | True | True | 8/8 |
| case_20 | INCOMPLETE | INCOMPLETE | False | False | 4/8 |
| case_21 | COMPLETE | COMPLETE | False | False | 0/3 |
| case_22 | INCOMPLETE | INCOMPLETE | False | False | 4/8 |
| case_23 | INCOMPLETE | INCOMPLETE | False | False | 4/8 |
| case_24 | INCOMPLETE | INCOMPLETE | False | False | 6/7 |
| case_25 | COMPLETE | COMPLETE | False | False | 0/3 |
| case_26 | COMPLETE | COMPLETE | False | False | 0/6 |
| case_27 | COMPLETE | COMPLETE | False | False | 0/6 |
| case_28 | COMPLETE | COMPLETE | False | False | 0/6 |
| case_29 | INCOMPLETE | INCOMPLETE | False | False | 8/14 |
| case_30 | INCOMPLETE | INCOMPLETE | False | False | 8/14 |
| case_31 | COMPLETE | COMPLETE | False | False | 0/3 |
| case_32 | INCOMPLETE | INCOMPLETE | False | False | 2/5 |

Unresolved production errors:

- case_01: case_01: no attributable observations or safe verification targets at audit cutoff
- case_02: case_02: no attributable observations or safe verification targets at audit cutoff
- case_04: case_04: no attributable observations or safe verification targets at audit cutoff

## Participant-created evaluation cases

1. Active connector + unsafe backup + present profile: expect INCOMPLETE; disable the connector, block restore, then delete the profile. Future actions/checks have empty citations.
2. A tombstone retaining its permitted stable subject reference with direct identifiers removed, plus a retained security event: verify redaction and retention. A surviving email hash prevents compliance.
3. Marketing-only opt-out and explicit request not to delete: no deletion authorization. Spanish, Japanese and Korean deletion requests authorize deletion.
4. A clean primary and exposed replica: replica exposure must prevent a false COMPLETE decision.
5. Evidence captured after audit_at cannot alter an earlier state or provide a historical citation.
6. SQL ATTACH is denied; atomic CSV output must preserve JSON and not publish a partial file.

## Failures found and improvements made

- The evaluator now runs the production predictor and validator rather than a separate approximation of inference.
- Exact row and sequence accuracy are distinct; semantic phase diagnostics expose coverage failures without hiding exact numbering errors.
- Output-hash, full request coverage, output-contract, and status-total checks prevent stale/subset run summaries from becoming final usage claims.
- Evidence adapters distinguish record content from lookup context, keep observation/availability times, reconstruct trace links, and compare replicas. Regression tests exercise the implemented safeguards; passing tests do not prove hidden accuracy.

- Conflicting explicit resource categories fail visibly instead of depending on evidence order. Known retention conditions survive later metadata-only readbacks.
- Attributed resources without admissible state cannot silently disappear into a COMPLETE decision. UNKNOWN states produce explicit uncertainty diagnostics.
- Shared identifiers alone cannot attribute a resource to either user; a unique admissible identifier is required before planning changes.
- Evaluation records the regression-suite outcome, counts failed test methods rather than failed subcases, refreshes forensic comparisons, and prevents packaging after failed tests.

## Remaining limitations

This is not a guaranteed full-score or enterprise-certified solution. Remaining public-sample errors above must be resolved or explained before claiming readiness. Missing subject/resource lineage, uncertainty about complete inventory coverage, temporal conflicts, OCR layouts, and conditional policy interpretation require explicit treatment; no links may be invented from numeric resource suffixes, case order, shared report timestamps, case families, or sample labels.
The mandated phase/operation/system/resource ordering is checked deterministically. For production, use strict coverage controls and authoritative lineage/inventory attestations rather than treating a discovered-resource-only answer as a deletion certificate. In-memory indexing is suitable for this dataset; larger deployments need persistent temporal storage and controlled ingestion.

Artifact/catalog contradictions:

- evidence_60: marketing_001 artifact owner contradicts catalog claim

## Verified full-dataset run

Rows: 518. Status distribution: {'INCOMPLETE': 355, 'COMPLETE': 153, 'NOT_APPLICABLE': 10}. Normalized observations: 2905. Parse/predict duration: 2.785 seconds. Root output SHA-256: `dc87451b3dc72908a60e7852c6429a5d643931aeb884560bf9a5447ff7731769`.

Coverage diagnostics: 344 messages across 342 unique requests. Strict coverage criterion: FAIL (342 affected requests), computed from the final run's diagnostics.

Source SHA-256: `eae4344312e149cac5e7a62ac51ff15cd9f3912fe8f8d5797465d1f0cf20c0ad`. Request CSV SHA-256: `7505a4d31e6fb35d77280c55b224290c5ebb2dd1ce21019222a5f190454bbb2d`.

See failure_analysis.md for every public mismatch, missing arbitrary resource IDs, unavailable subject lineage, responsible functions, and admissibility decisions. Such missing source facts cannot be reconstructed by copying sample answers or guessing identifier patterns.

First ten coverage diagnostics:

- case_100: no attributable account readback; completeness covers discovered resources only
- case_101: no attributable account readback; completeness covers discovered resources only
- case_102: no attributable account readback; completeness covers discovered resources only
- case_103: no attributable account readback; completeness covers discovered resources only
- case_104: no attributable account readback; completeness covers discovered resources only
- case_106: no attributable account readback; completeness covers discovered resources only
- case_107: no attributable account readback; completeness covers discovered resources only
- case_108: no attributable account readback; completeness covers discovered resources only
- case_109: no attributable account readback; completeness covers discovered resources only
- case_110: no attributable account readback; completeness covers discovered resources only
