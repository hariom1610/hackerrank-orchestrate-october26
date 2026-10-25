# Architecture and interview preparation

The problem is a point-in-time evidence audit. Workflow SUCCESS and COMPLETE
are claims; direct readbacks and stored contents establish state. The code
resolves exact current and historical emails, phones, user references, and
hashes, avoiding fuzzy email matches that would capture another customer.

Evidence adapters normalize JSON, SQLite-compatible SQL, multiple log formats,
text handovers, PDF text, and local OCR. Interleaved logs join through trace IDs.
Each observation retains resource, system, category, state, observation time,
manifest availability, and participant-visible evidence ID. Both timestamps
are checked at the case cutoff. An exposed replica defeats a clean primary
observed at the same time. A cache miss is not evidence of database absence.

Replica state is tracked independently: a later clean primary read cannot clear
an exposed failover copy. Explicit source_resource_id lineage can connect a
derived search entry to an absent profile without guessing from identifiers.
Future identity snapshots/history are excluded, and a generic ticket wrapper
cannot override an explicitly established attachment category.

The policy planner distinguishes deletion, redaction, anonymization, retention,
connector shutdown, and restore blocking. A stable internal tombstone reference
is permitted while direct identifiers and hashes are removed. Analytics must
lose both direct identifiers and attributable stable references. The output
uses the mandated deterministic phase and operation ordering, with empty
citations for proposed work and future checks.

Validation checks request uniqueness, timestamp syntax, manifest path boundaries,
output coverage and schema, operation/state pairs, ordering, and citation cutoff.
SQL executes in memory with disk attachment and file functions denied. CSV
publication is atomic. Dependencies and configuration are documented without
embedding credentials or local installation paths.

The public evaluation reports status, exact-step precision/recall, positional
field accuracy, and exact ordered sequence accuracy. It includes independent
custom cases and explicitly counts unresolved sample cases as failures.
Hidden accuracy is not measurable. Runtime generative-model calls/tokens/cost
are zero; OCR is local machine-learning extraction. The coding assistant's
development tokens are not runtime audit tokens.

Independent agents reviewed evidence attribution, core correctness, and
evaluation/packaging. See evaluation/failure_analysis.md for participant-input
limitations. Full marks cannot be claimed while the exact public sequences
remain unmatched. Packaging checks source/input/output/report fingerprints so
stale artifacts are not represented as a verified final run.

The main weakness is evidence attribution and inventory completeness. Some
lookups are absent and some records are anonymized without retaining a
subject/resource link. The code refuses to invent links from resource suffixes,
case order, shared timestamps, or public answers. Default challenge output is
therefore a candidate with coverage warnings. Strict mode refuses publication
when account coverage is missing or resource state is uncertain. Missing state
for a known attributed resource fails in both modes. Production needs authoritative lineage and
inventory coverage, conditional policy evaluation, stronger document models,
an explicit uncertainty/review state, and persistent temporal indexes. No
perfect score or enterprise certification is claimed.
