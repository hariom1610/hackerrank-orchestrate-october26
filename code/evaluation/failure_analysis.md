# Forensic public-sample failure analysis

Production source SHA-256: `eae4344312e149cac5e7a62ac51ff15cd9f3912fe8f8d5797465d1f0cf20c0ad`. Prediction-input SHA-256: `e2c5c44458c2daafc0b5b64529b4dfdc0f10bd7139aadbd5dc75a5c4a08d4799`.

All 32 samples were executed through production predict() and validate_output(). 101 participant prediction/request sources were scanned, including production PDF/OCR text. Published answers and the blank output template were excluded from the source-occurrence scan. Labels are used only for comparison, never to populate an inference edge.

## Before/after comparison

The baseline is the independently saved metrics snapshot; values and percentage-point changes below are computed, not hand-edited. A diagnostic-only change can legitimately produce no public accuracy gain.

| Metric | Before | After | Change |
|---|---|---|---|
| Case deletion-status accuracy | 29/32 (90.62%) | 29/32 (90.62%) | +0.00 pp |
| Exact row accuracy | 9/32 (28.12%) | 9/32 (28.12%) | +0.00 pp |
| Exact ordered sequence accuracy | 9/32 (28.12%) | 9/32 (28.12%) | +0.00 pp |
| Exact step precision | 114/164 (69.51%) | 114/164 (69.51%) | +0.00 pp |
| Exact step recall | 114/193 (59.07%) | 114/193 (59.07%) | +0.00 pp |
| Positional field accuracy | 957/1379 (69.40%) | 957/1379 (69.40%) | +0.00 pp |

## Classification method

A = a reproducible code defect requiring review; B = admissible source evidence not normalized/connected; C = unavailable or missing input. A reference-inventory disagreement is kept separate: an extra grounded resource must not be discarded merely because the published answer omits it. Late-only facts do not become admissible through an earlier embedded timestamp.

A missing verification is a symptom. Each diagnosis below records raw occurrences, observed state, subject-link availability, responsible consumers, and the smallest defensible remedy. Numbering shifts caused by an inventory difference are separated from an actual ordering bug. Proposed classifications with a review qualifier are hypotheses to verify, not permission to change output to match labels.

| Diagnosis | Count |
|---|---:|
| INPUT_UNDERDETERMINATION_ABSENT_ID | 3 |
| INPUT_UNDERDETERMINATION_LATE_LINEAGE | 8 |
| INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK | 13 |
| INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE | 10 |
| REFERENCE_INVENTORY_CONFLICT | 5 |

## Semantic phase diagnostics

Only step_no is ignored; all other fields, including evidence, must match.

| Phase | Matched | Predicted | Expected |
|---|---:|---:|---:|
| FINDING | 41 | 42 | 41 |
| REMEDIATION | 41 | 42 | 41 |
| VERIFICATION | 77 | 80 | 111 |

## case_01

Status: expected **COMPLETE**, production **UNRESOLVED**. Exact row: **False**. Audit cutoff: `2026-09-03T11:30:00Z`. Missing semantic steps: 1; extra semantic steps: 0.
Production diagnostic: case_01: no attributable observations or safe verification targets at audit cutoff

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_001 / ABSENT** (reference/predicted step 1; citation `evidence_54`).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3342 (system_activity.csv:3343; available 2026-08-20T16:41:43Z).

## case_02

Status: expected **COMPLETE**, production **UNRESOLVED**. Exact row: **False**. Audit cutoff: `2026-09-04T15:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.
Production diagnostic: case_02: no attributable observations or safe verification targets at audit cutoff

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_002 / ABSENT** (reference/predicted step 1; citation `evidence_54`).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3376 (system_activity.csv:3377; available 2026-08-22T07:30:03Z).

## case_03

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-26T11:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_9406 / ANONYMIZED** (reference/predicted step 3; citation `evidence_94`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3852 (system_activity.csv:3853; available 2026-09-15T10:31:16Z); evidence_94 (evidence/logs/resource_lookup_trace_20260926_103856.log:42; available 2026-09-26T10:38:56Z); evidence_94 (evidence/logs/resource_lookup_trace_20260926_103856.log:43; available 2026-09-26T10:38:56Z).
  Readback: evidence_94, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-26T09:54:09+00:00, available 2026-09-26T10:38:56+00:00, admissible=True, subject-in-record=False.

## case_04

Status: expected **COMPLETE**, production **UNRESOLVED**. Exact row: **False**. Audit cutoff: `2026-09-07T10:20:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
Production diagnostic: case_04: no attributable observations or safe verification targets at audit cutoff

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_004 / ABSENT** (reference/predicted step 1; citation `evidence_54`).
  Diagnosis: `INPUT_UNDERDETERMINATION_ABSENT_ID`; class `C_MISSING_INPUT`. The arbitrary expected resource identifier has no occurrence in any scanned prediction input or extracted artifact.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply participant-visible resource/subject lineage; do not synthesize the identifier from labels or numbering.
  Source proof: no exact identifier occurrence in the scanned prediction inputs.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_901 / ANONYMIZED** (reference/predicted step 2; citation `evidence_56`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3463 (system_activity.csv:3464; available 2026-08-27T08:47:41Z); evidence_56 (evidence/records/customer_analytics_report_20260907.json:7; available 2026-09-07T09:45:00Z).
  Readback: evidence_56, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-07T09:45:00+00:00, available 2026-09-07T09:45:00+00:00, admissible=True, subject-in-record=False.

## case_05

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-08T13:40:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_06

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-10T09:15:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_07

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-12T08:00:00Z`. Missing semantic steps: 1; extra semantic steps: 3.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_007 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3590 (system_activity.csv:3591; available 2026-09-01T19:28:39Z).

- **Extra predicted: FINDING / REPORT_REMAINING_RECORD / object_storage / object_19 / PRESENT** (reference/predicted step 1; citation `evidence_46`).
  Diagnosis: `REFERENCE_INVENTORY_CONFLICT`; class `REFERENCE_DISAGREEMENT_REQUIRING_REVIEW`. An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.
  Responsible consumers: EvidenceStore.current, Policy.plan. Smallest defensible remedy: Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.
  Source occurrences: activity_4007 (system_activity.csv:4008; available 2026-02-13T08:07:01Z).
  Readback: evidence_46, SUPPORT_ATTACHMENT=PRESENT, observed 2026-02-13T08:00:00+00:00, available 2026-02-13T08:07:01+00:00, admissible=True, subject-in-record=False.
  Subject-link availability: 2026-02-13T08:07:01+00:00 (admissible=True).

- **Extra predicted: REMEDIATION / DELETE_RECORD / object_storage / object_19 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `REFERENCE_INVENTORY_CONFLICT`; class `REFERENCE_DISAGREEMENT_REQUIRING_REVIEW`. An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.
  Responsible consumers: EvidenceStore.current, Policy.plan. Smallest defensible remedy: Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.
  Source occurrences: activity_4007 (system_activity.csv:4008; available 2026-02-13T08:07:01Z).
  Readback: evidence_46, SUPPORT_ATTACHMENT=PRESENT, observed 2026-02-13T08:00:00+00:00, available 2026-02-13T08:07:01+00:00, admissible=True, subject-in-record=False.
  Subject-link availability: 2026-02-13T08:07:01+00:00 (admissible=True).

- **Extra predicted: VERIFICATION / VERIFY_RECORD_ABSENT / object_storage / object_19 / ABSENT** (reference/predicted step 5; citation ``).
  Diagnosis: `REFERENCE_INVENTORY_CONFLICT`; class `REFERENCE_DISAGREEMENT_REQUIRING_REVIEW`. An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.
  Responsible consumers: EvidenceStore.current, Policy.plan. Smallest defensible remedy: Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.
  Source occurrences: activity_4007 (system_activity.csv:4008; available 2026-02-13T08:07:01Z).
  Readback: evidence_46, SUPPORT_ATTACHMENT=PRESENT, observed 2026-02-13T08:00:00+00:00, available 2026-02-13T08:07:01+00:00, admissible=True, subject-in-record=False.
  Subject-link availability: 2026-02-13T08:07:01+00:00 (admissible=True).
Numbering shifts on otherwise identical steps: FINDING/support_001: expected #1, predicted #2; REMEDIATION/support_001: expected #2, predicted #4; VERIFICATION/support_001: expected #4, predicted #6.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_08

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-14T16:10:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_008 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3554 (system_activity.csv:3555; available 2026-08-31T13:48:58Z).
Numbering shifts on otherwise identical steps: VERIFICATION/export_001: expected #4, predicted #3.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_09

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-16T09:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_3960 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: activity_3703 (system_activity.csv:3704; available 2026-09-07T07:55:18Z); evidence_06 (evidence/logs/structured_service_events_eu_west_20260918.log:86; available 2026-09-18T11:55:24Z).
  Readback: evidence_06, USER_PROFILE=ABSENT, observed 2026-09-16T08:57:34+00:00, available 2026-09-18T11:55:24+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-18T11:55:24+00:00 (admissible=False).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_4902 / PRESENT** (reference/predicted step 4; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: evidence_06 (evidence/logs/structured_service_events_eu_west_20260918.log:28; available 2026-09-18T11:55:24Z).
  Readback: evidence_06, SECURITY_AUDIT_LOG=PRESENT, observed 2026-09-16T08:52:59+00:00, available 2026-09-18T11:55:24+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-18T11:55:24+00:00 (admissible=False).
Numbering shifts on otherwise identical steps: VERIFICATION/backup_4978: expected #5, predicted #3.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_10

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-18T12:25:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_010 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3595 (system_activity.csv:3596; available 2026-09-02T10:08:37Z).
Numbering shifts on otherwise identical steps: VERIFICATION/support_002: expected #4, predicted #3.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_11

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-10-01T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_12

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_13

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-10-01T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_14

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-10-01T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_15

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_16

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-21T10:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_17

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 2.

- **Extra predicted: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_6523 / ABSENT** (reference/predicted step 4; citation ``).
  Diagnosis: `REFERENCE_INVENTORY_CONFLICT`; class `REFERENCE_DISAGREEMENT_REQUIRING_REVIEW`. An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.
  Responsible consumers: EvidenceStore.current, Policy.plan. Smallest defensible remedy: Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.
  Source occurrences: activity_3850 (system_activity.csv:3851; available 2026-09-15T09:56:51Z); evidence_67 (evidence/logs/resource_lookup_trace_20260310_061801.log:2; available 2026-03-10T06:18:01Z); evidence_67 (evidence/logs/resource_lookup_trace_20260310_061801.log:3; available 2026-03-10T06:18:01Z).
  Readback: evidence_67, USER_PROFILE=ABSENT, observed 2026-03-10T06:18:01+00:00, available 2026-03-10T06:18:01+00:00, admissible=True, subject-in-record=True.
  Subject-link availability: 2026-03-10T06:18:01+00:00 (admissible=True).

- **Extra predicted: VERIFICATION / VERIFY_RECORD_REDACTED / identity_service / tombstone_17 / REDACTED** (reference/predicted step 6; citation ``).
  Diagnosis: `REFERENCE_INVENTORY_CONFLICT`; class `REFERENCE_DISAGREEMENT_REQUIRING_REVIEW`. An admissible attributed resource supports this extra step, but the published inventory omits it. An earlier artifact is not invalid solely because it precedes the request; no arbitrary freshness window is applied.
  Responsible consumers: EvidenceStore.current, Policy.plan. Smallest defensible remedy: Inspect later absence/deletion evidence and any explicit inventory scope. Do not drop a grounded resource merely to improve agreement with the reference.
  Source occurrences: activity_4011 (system_activity.csv:4012; available 2026-03-10T06:07:01Z).
  Readback: evidence_42, ACCOUNT_TOMBSTONE=REDACTED, observed 2026-03-10T06:00:00+00:00, available 2026-03-10T06:07:01+00:00, admissible=True, subject-in-record=True.
  Subject-link availability: 2026-03-10T06:07:01+00:00 (admissible=True); 2026-03-10T06:07:01+00:00 (admissible=True).
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_1797: expected #4, predicted #5; VERIFICATION/backup_3245: expected #5, predicted #7.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_18

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-26T11:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_5521 / ABSENT** (reference/predicted step 9; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3732 (system_activity.csv:3733; available 2026-09-09T09:52:26Z).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_6645 / PRESENT** (reference/predicted step 11; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_ABSENT_ID`; class `C_MISSING_INPUT`. The arbitrary expected resource identifier has no occurrence in any scanned prediction input or extracted artifact.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply participant-visible resource/subject lineage; do not synthesize the identifier from labels or numbering.
  Source proof: no exact identifier occurrence in the scanned prediction inputs.
Numbering shifts on otherwise identical steps: VERIFICATION/search_4013: expected #10, predicted #9; VERIFICATION/support_5569: expected #12, predicted #10; VERIFICATION/analytics_037: expected #13, predicted #11; VERIFICATION/data_flow_4890: expected #14, predicted #12.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_19

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **True**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 0; extra semantic steps: 0.
No semantic discrepancy against the public reference was found.

## case_20

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-26T11:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_5037 / ABSENT** (reference/predicted step 5; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3734 (system_activity.csv:3735; available 2026-09-09T10:14:55Z).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_5569 / PRESENT** (reference/predicted step 7; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_ABSENT_ID`; class `C_MISSING_INPUT`. The arbitrary expected resource identifier has no occurrence in any scanned prediction input or extracted artifact.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply participant-visible resource/subject lineage; do not synthesize the identifier from labels or numbering.
  Source proof: no exact identifier occurrence in the scanned prediction inputs.
Numbering shifts on otherwise identical steps: VERIFICATION/search_4262: expected #6, predicted #5; VERIFICATION/data_flow_1770: expected #8, predicted #6.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_21

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_6440 / ABSENT** (reference/predicted step 1; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3661 (system_activity.csv:3662; available 2026-09-05T11:01:53Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:46; available 2026-09-15T11:44:55Z).
  Readback: evidence_92, USER_PROFILE=ABSENT, observed 2026-09-15T09:31:19+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_5335 / ANONYMIZED** (reference/predicted step 3; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3665 (system_activity.csv:3666; available 2026-09-05T11:31:34Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:59; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:105; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=False.
  Readback: evidence_92, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T09:34:42+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_3737: expected #2, predicted #1.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_22

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-21T10:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_4990 / ABSENT** (reference/predicted step 5; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3573 (system_activity.csv:3574; available 2026-09-01T09:12:11Z).
Numbering shifts on otherwise identical steps: VERIFICATION/search_8911: expected #6, predicted #5; VERIFICATION/audit_record_3482: expected #7, predicted #6; VERIFICATION/analytics_4440: expected #8, predicted #7.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_23

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_410 / ABSENT** (reference/predicted step 5; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3662 (system_activity.csv:3663; available 2026-09-05T11:10:55Z).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_4128 / PRESENT** (reference/predicted step 8; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:412; available 2026-09-17T12:00:00Z).
  Readback: evidence_02, SECURITY_AUDIT_LOG=PRESENT, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).
Numbering shifts on otherwise identical steps: VERIFICATION/export_7364: expected #6, predicted #5; VERIFICATION/search_898: expected #7, predicted #6.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_24

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_7095 / PRESENT** (reference/predicted step 7; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:419; available 2026-09-17T12:00:00Z).
  Readback: evidence_02, SECURITY_AUDIT_LOG=PRESENT, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).

## case_25

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_3136 / ABSENT** (reference/predicted step 1; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3597 (system_activity.csv:3598; available 2026-09-02T10:48:27Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:10; available 2026-09-15T11:44:55Z).
  Readback: evidence_92, USER_PROFILE=ABSENT, observed 2026-09-15T09:31:40+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_1895 / ANONYMIZED** (reference/predicted step 3; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3602 (system_activity.csv:3603; available 2026-09-02T11:31:08Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:83; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:60; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=False.
  Readback: evidence_92, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T09:58:44+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_451: expected #2, predicted #1.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_26

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_5684 / ABSENT** (reference/predicted step 1; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: activity_3600 (system_activity.csv:3601; available 2026-09-02T11:08:43Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:11; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:40; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, USER_PROFILE=PRESENT, observed 2026-09-09T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Readback: evidence_92, USER_PROFILE=ABSENT, observed 2026-09-15T09:01:48+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_4566 / ANONYMIZED** (reference/predicted step 4; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3603 (system_activity.csv:3604; available 2026-09-02T11:31:24Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:107; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:78; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=False.
  Readback: evidence_92, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T11:29:16+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_5416: expected #2, predicted #1; VERIFICATION/support_4715: expected #3, predicted #2; VERIFICATION/data_flow_6244: expected #5, predicted #3; VERIFICATION/backup_3120: expected #6, predicted #4.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_27

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_3866 / ABSENT** (reference/predicted step 1; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: activity_3530 (system_activity.csv:3531; available 2026-08-30T10:57:28Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:524; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:16; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, USER_PROFILE=PRESENT, observed 2026-09-17T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Readback: evidence_92, USER_PROFILE=ABSENT, observed 2026-09-15T09:59:48+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_4574 / ANONYMIZED** (reference/predicted step 4; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3533 (system_activity.csv:3534; available 2026-08-30T11:31:09Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:132; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:87; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=False.
  Readback: evidence_92, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T10:07:38+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_3830: expected #2, predicted #1; VERIFICATION/support_4707: expected #3, predicted #2; VERIFICATION/data_flow_2295: expected #5, predicted #3; VERIFICATION/backup_5970: expected #6, predicted #4.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_28

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_5482 / ABSENT** (reference/predicted step 1; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3529 (system_activity.csv:3530; available 2026-08-30T10:46:13Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:34; available 2026-09-15T11:44:55Z).
  Readback: evidence_92, USER_PROFILE=ABSENT, observed 2026-09-15T11:07:16+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ANONYMIZED / analytics_platform / analytics_6077 / ANONYMIZED** (reference/predicted step 4; citation `evidence_92`).
  Diagnosis: `INPUT_UNDERDETERMINATION_SUBJECT_LINEAGE`; class `C_MISSING_INPUT`. The state is observable, but the supplied admissible facts do not link the resource to this subject.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Retain pre-deletion query keys or historical subject lineage; state alone is not an ownership edge.
  Source occurrences: activity_3534 (system_activity.csv:3535; available 2026-08-30T11:31:53Z); evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:161; available 2026-09-17T12:00:00Z); evidence_92 (evidence/records/service_resource_export_20260915_114455.json:114; available 2026-09-15T11:44:55Z).
  Readback: evidence_02, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=False.
  Readback: evidence_92, ANALYTICS_PROFILE=ANONYMIZED, observed 2026-09-15T11:44:55+00:00, available 2026-09-15T11:44:55+00:00, admissible=True, subject-in-record=False.
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_9265: expected #2, predicted #1; VERIFICATION/support_2351: expected #3, predicted #2; VERIFICATION/data_flow_2337: expected #5, predicted #3; VERIFICATION/backup_838: expected #6, predicted #4.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_29

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_7012 / ABSENT** (reference/predicted step 9; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3532 (system_activity.csv:3533; available 2026-08-30T11:06:57Z).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_3954 / PRESENT** (reference/predicted step 11; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:454; available 2026-09-17T12:00:00Z).
  Readback: evidence_02, SECURITY_AUDIT_LOG=PRESENT, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).
Numbering shifts on otherwise identical steps: VERIFICATION/search_1993: expected #10, predicted #9; VERIFICATION/support_5281: expected #12, predicted #10; VERIFICATION/analytics_5208: expected #13, predicted #11; VERIFICATION/data_flow_3827: expected #14, predicted #12.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_30

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 2; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_4163 / ABSENT** (reference/predicted step 9; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3465 (system_activity.csv:3466; available 2026-08-27T10:55:42Z).

- **Missing expected: VERIFICATION / VERIFY_RECORD_PRESENT / security_service / audit_record_1707 / PRESENT** (reference/predicted step 11; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_LATE_LINEAGE`; class `C_MISSING_INPUT`. Subject/resource links exist only after the audit cutoff; they cannot attribute this resource historically.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply an admissible historical lineage edge; preserve the cutoff rather than admitting the later artifact.
  Source occurrences: evidence_02 (evidence/records/customer_data_snapshot_bundle_20260917.json:461; available 2026-09-17T12:00:00Z).
  Readback: evidence_02, SECURITY_AUDIT_LOG=PRESENT, observed 2026-09-15T12:00:00+00:00, available 2026-09-17T12:00:00+00:00, admissible=False, subject-in-record=True.
  Subject-link availability: 2026-09-17T12:00:00+00:00 (admissible=False).
Numbering shifts on otherwise identical steps: VERIFICATION/search_9359: expected #10, predicted #9; VERIFICATION/support_6477: expected #12, predicted #10; VERIFICATION/analytics_3697: expected #13, predicted #11; VERIFICATION/data_flow_8524: expected #14, predicted #12.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_31

Status: expected **COMPLETE**, production **COMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.
The candidate COMPLETE status has coverage warnings and is not an enterprise deletion certificate.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_4857 / ABSENT** (reference/predicted step 1; citation `evidence_51`).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3682 (system_activity.csv:3683; available 2026-09-06T10:45:58Z).
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_6909: expected #2, predicted #1; VERIFICATION/tombstone_440: expected #3, predicted #2.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## case_32

Status: expected **INCOMPLETE**, production **INCOMPLETE**. Exact row: **False**. Audit cutoff: `2026-09-15T12:00:00Z`. Missing semantic steps: 1; extra semantic steps: 0.

- **Missing expected: VERIFICATION / VERIFY_RECORD_ABSENT / account_service / account_8858 / ABSENT** (reference/predicted step 3; citation ``).
  Diagnosis: `INPUT_UNDERDETERMINATION_NO_SUBJECT_READBACK`; class `C_MISSING_INPUT`. The identifier appears in source claims, but neither an attributable state nor admissible ownership edge establishes the expected check.
  Responsible consumers: EvidenceStore.link/claimed_resources/current, Policy.plan. Smallest defensible remedy: Supply subject-linked readback or inventory lineage; event proximity and operation SUCCESS cannot repair it.
  Source occurrences: activity_3685 (system_activity.csv:3686; available 2026-09-06T11:05:15Z).
Numbering shifts on otherwise identical steps: VERIFICATION/audit_record_7068: expected #4, predicted #3; VERIFICATION/tombstone_9178: expected #5, predicted #4.
These shifts follow missing/extra inventory; they are not classified as an independent sort-order defect.

## Machine-readable companion

`.cache/failure_analysis.json` retains all expected and actual step fields, source locations, normalized observations, cutoff decisions, diagnoses, and numbering shifts. It is evaluation-only and is never imported by production inference. Hidden-case correctness remains unmeasured.
