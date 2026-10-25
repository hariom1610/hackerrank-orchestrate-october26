"""Behavioral regression tests independent of the supplied sample labels."""
import json
import tempfile
import unittest
from pathlib import Path

from core import AuditError, Observation, Policy, deletion_authorized, timestamp, validate_output
from evidence import EvidenceStore, identifiable, record_state
from main import write_output


WHEN = timestamp("2026-09-15T12:00:00Z")


def observation(resource, category, state, evidence="proof", system="account_service", when=WHEN):
    return Observation(system, resource, category, state, when, when, evidence, "")


class AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (Path(__file__).resolve().parents[1] / ".cache").mkdir(exist_ok=True)

    def setUp(self):
        self.policy = Policy.__new__(Policy)
        self.policy.actions = dict(USER_PROFILE="DELETE", ACCOUNT_TOMBSTONE="REDACT", SUPPORT_MESSAGE="REDACT", ANALYTICS_PROFILE="ANONYMIZE", SECURITY_AUDIT_LOG="RETAIN")

    def test_custom_active_connector_before_record_mutations(self):
        status, steps = self.policy.plan([
            observation("profile", "USER_PROFILE", "PRESENT"),
            observation("connector", "DATA_FLOW", "ACTIVE", system="integration_service"),
            observation("backup", "BACKUP_ARCHIVE", "ACTIVE", system="backup_service"),
        ])
        self.assertEqual(status, "INCOMPLETE")
        self.assertEqual([s["operation"] for s in steps if s["phase"] == "REMEDIATION"], ["DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD"])
        self.assertTrue(all(s["evidence_id"] == "" for s in steps if s["phase"] != "FINDING"))

    def test_custom_clean_tombstone_preserves_stable_reference(self):
        record = dict(subject_reference="user_900", name=None, email=None, phone=None, email_hash=None)
        self.assertEqual(record_state("ACCOUNT_TOMBSTONE", record), "REDACTED")
        status, steps = self.policy.plan([observation("tombstone", "ACCOUNT_TOMBSTONE", "REDACTED"), observation("security", "SECURITY_AUDIT_LOG", "PRESENT")])
        self.assertEqual(status, "COMPLETE")
        self.assertEqual({s["operation"] for s in steps}, {"VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED"})
        record["email_hash"] = "a" * 64
        self.assertEqual(record_state("ACCOUNT_TOMBSTONE", record), "PRESENT")

    def test_custom_non_deletion_and_multilingual_authorization(self):
        for text in ["Please remove me from marketing lists only.", "Please don't delete my account; send me a copy.", "Can you tell me what personal information you hold? This is not a request to erase it."]:
            self.assertFalse(deletion_authorized(text))
        for text in ["Please delete my account.", "Solicito la eliminación de mi cuenta", "アカウントの削除を依頼します", "계정 삭제를 요청합니다"]:
            self.assertTrue(deletion_authorized(text))

    def test_nested_pii_and_stable_analytics_identifier(self):
        self.assertTrue(identifiable({"document": {"email": "test@example.invalid"}}))
        self.assertEqual(record_state("ANALYTICS_PROFILE", {"customer_reference": "user_900"}), "PRESENT")
        self.assertEqual(record_state("ANALYTICS_PROFILE", {"customer_reference": None, "metrics": {"sessions": 7}}), "ANONYMIZED")

    def test_later_evidence_rejected(self):
        request = dict(case_id="test", audit_at="2026-09-15T12:00:00Z")
        status, steps = self.policy.plan([observation("profile", "USER_PROFILE", "ABSENT")])
        rows = [dict(case_id="test", deletion_status=status, steps_json=json.dumps(steps))]
        with self.assertRaises(AuditError):
            validate_output(rows, [request], {"proof": timestamp("2026-09-16T00:00:00Z")})

    def test_replica_exposure_defeats_clean_primary(self):
        store = EvidenceStore.__new__(EvidenceStore)
        store.subject_resources = lambda u, c: {"account"}
        store.scopes = []
        store.by_resource = {"account": [observation("account", "USER_PROFILE", "ABSENT", "evidence_1"), observation("account", "USER_PROFILE", "PRESENT", "evidence_1")]}
        self.assertEqual(store.current("user", WHEN)[0].state, "PRESENT")

    def test_future_observation_does_not_change_present(self):
        store = EvidenceStore.__new__(EvidenceStore)
        store.subject_resources = lambda u, c: {"account"}
        store.scopes = []
        store.by_resource = {"account": [observation("account", "USER_PROFILE", "ABSENT", "evidence_1"), observation("account", "USER_PROFILE", "PRESENT", "evidence_2", when=timestamp("2026-09-16T12:00:00Z"))]}
        self.assertEqual(store.current("user", WHEN)[0].state, "ABSENT")

    def test_sql_cannot_attach_files(self):
        store = EvidenceStore.__new__(EvidenceStore)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".cache") as directory:
            path = Path(directory) / "bad.sql"
            path.write_text("ATTACH DATABASE 'forbidden.db' AS outside;")
            import sqlite3
            with self.assertRaises(sqlite3.DatabaseError):
                store.load_sql(path, {"captured_at": "2026-09-15T12:00:00Z"})

    def test_atomic_output_and_json_round_trip(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".cache") as directory:
            path = Path(directory) / "output.csv"
            write_output(path, [dict(case_id="test", deletion_status="NOT_APPLICABLE", steps_json="[]")])
            import csv
            with path.open() as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(json.loads(rows[0]["steps_json"]), [])
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_naive_timestamp_and_unknown_intent_fail(self):
        with self.assertRaises(AuditError):
            timestamp("2026-09-15T12:00:00")
        with self.assertRaises(AuditError):
            deletion_authorized("Hello there")

    def test_unknown_restore_permission_never_fabricates_a_finding(self):
        status, steps = self.policy.plan([observation("backup", "BACKUP_ARCHIVE", "UNKNOWN", system="backup_service")])
        self.assertEqual(status, "INCOMPLETE")
        self.assertEqual([s["operation"] for s in steps], ["BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"])
        self.assertTrue(all(s["evidence_id"] == "" for s in steps))

    def test_exact_identity_matching_excludes_similar_email(self):
        from core import IdentityIndex
        from collections import defaultdict
        index = IdentityIndex.__new__(IdentityIndex)
        index.owners, index.values = defaultdict(set), defaultdict(set)
        index.add("user_900", "person@example.invalid")
        index.add("user_901", "person.jr@example.invalid")
        self.assertEqual(index.match("PERSON@EXAMPLE.INVALID"), {"user_900"})
        self.assertEqual(index.match("person.jr@example.invalid"), {"user_901"})

    def test_ocr_domain_glyph_error_is_not_an_owner_contradiction(self):
        from evidence import same_ocr_email
        self.assertTrue(same_ocr_email("person@gmaii.com", "person@gmail.com"))
        self.assertFalse(same_ocr_email("person.jr@gmail.com", "person@gmail.com"))

    def test_later_clean_primary_does_not_clear_older_exposed_replica(self):
        from dataclasses import replace
        store = EvidenceStore.__new__(EvidenceStore)
        store.subject_resources = lambda user, cutoff: {"account"}
        store.scopes = []
        older = timestamp("2026-09-14T12:00:00Z")
        store.by_resource = {"account": [
            replace(observation("account", "USER_PROFILE", "PRESENT", "evidence_1", when=older), replica="failover"),
            replace(observation("account", "USER_PROFILE", "ABSENT", "evidence_2"), replica="primary"),
        ]}
        current = store.current("user", WHEN)
        self.assertTrue(any(obs.state == "PRESENT" for obs in current))
        self.assertEqual(self.policy.plan(current)[0], "INCOMPLETE")

    def test_future_identity_snapshot_without_history_is_not_available(self):
        from collections import defaultdict
        from core import IdentityIndex
        index = IdentityIndex.__new__(IdentityIndex)
        index.snapshot = {"user_900": dict(
            updated_at="2026-09-16T12:00:00Z", email="future@example.invalid",
            phone="+12345678901", email_hash="a" * 64,
        )}
        index.history = defaultdict(list)
        self.assertEqual(index.available_values("user_900", WHEN), {"user_900"})
        index.history["user_900"].append(dict(field_name="email", event_time="2026-09-16T12:00:00Z", old_value="earlier@example.invalid", new_value="future@example.invalid"))
        self.assertEqual(index.available_values("user_900", WHEN), {"user_900"})

    def test_tombstone_without_stable_reference_cannot_be_certified(self):
        for record in [dict(name=None, email=None, phone=None, email_hash=None), dict(email="person@example.invalid"), dict(subject_reference="person@example.invalid"), dict(subject_reference={"invalid": "reference"})]:
            with self.subTest(record=record), self.assertRaises(AuditError):
                record_state("ACCOUNT_TOMBSTONE", record)

    def test_output_status_must_match_request_authorization(self):
        status, steps = self.policy.plan([observation("profile", "USER_PROFILE", "ABSENT")])
        rows = [dict(case_id="test", deletion_status=status, steps_json=json.dumps(steps))]
        requests = [dict(case_id="test", audit_at="2026-09-15T12:00:00Z", request_text="Please don't delete my account; send me a copy.")]
        with self.assertRaises(AuditError):
            validate_output(rows, requests, {"proof": WHEN})
        requests[0]["request_text"] = "Please delete my account."
        rows[0].update(deletion_status="NOT_APPLICABLE", steps_json="[]")
        with self.assertRaises(AuditError):
            validate_output(rows, requests, {"proof": WHEN})

    def test_duplicate_and_conflicting_verification_steps_are_rejected(self):
        base = self.policy.step(observation("profile", "USER_PROFILE", "ABSENT"), "VERIFICATION", "VERIFY_RECORD_ABSENT", "proof")
        requests = [dict(case_id="test", audit_at="2026-09-15T12:00:00Z", request_text="Please delete my account.")]
        for duplicate in [dict(base), dict(base, operation="VERIFY_RECORD_PRESENT", state="PRESENT")]:
            steps = [dict(base, step_no=1), dict(duplicate, step_no=2)]
            rows = [dict(case_id="test", deletion_status="COMPLETE", steps_json=json.dumps(steps))]
            with self.subTest(second_operation=duplicate["operation"]), self.assertRaises(AuditError):
                validate_output(rows, requests, {"proof": WHEN})

    def test_explicit_source_lineage_discovers_absent_profile(self):
        from collections import defaultdict
        from core import IdentityIndex
        index = IdentityIndex.__new__(IdentityIndex)
        index.owners, index.values = defaultdict(set), defaultdict(set)
        index.add("user_900", "person@example.invalid")
        index.available_values = lambda user, cutoff: index.values[user]
        store = EvidenceStore.__new__(EvidenceStore)
        store.identities, store.links = index, defaultdict(list)
        store.relationships, store.explicit_owners = defaultdict(list), defaultdict(list)
        store.link("search_900", {"email": "person@example.invalid", "source_resource_id": "account_900"}, WHEN)
        self.assertEqual(store.claimed_resources("user_900", WHEN), {"account_900", "search_900"})
        self.assertEqual(store.claimed_resources("user_900", timestamp("2026-09-14T00:00:00Z")), set())
        store.by_resource = {"search_900": [observation("search_900", "SEARCH_INDEX_ENTRY", "PRESENT", "evidence_1", system="search_service")]}
        store.times = {"evidence_2": WHEN}
        store.complete_scopes = {("evidence_2", "primary")}
        store.scopes = [({"file_id": "evidence_2"}, "account_service", "USER_PROFILE", WHEN, set(), "primary")]
        current = store.current("user_900", WHEN)
        self.assertTrue(any(o.resource == "account_900" and o.state == "ABSENT" for o in current))

    def test_generic_ticket_does_not_override_attachment_policy(self):
        from dataclasses import replace
        store = EvidenceStore.__new__(EvidenceStore)
        store.subject_resources = lambda user, cutoff: {"support_900"}
        store.scopes = []
        earlier = timestamp("2026-09-14T12:00:00Z")
        store.by_resource = {"support_900": [
            observation("support_900", "SUPPORT_ATTACHMENT", "PRESENT", "evidence_1", when=earlier),
            replace(observation("support_900", "SUPPORT_MESSAGE", "REDACTED", "evidence_2"), category_explicit=False),
        ]}
        current = store.current("user", WHEN)
        self.assertEqual((current[0].category, current[0].state), ("SUPPORT_ATTACHMENT", "PRESENT"))

    def test_expired_retention_requires_applicable_policy(self):
        from dataclasses import replace
        obs = replace(observation("security", "SECURITY_AUDIT_LOG", "PRESENT"), payload=json.dumps({"retention_until": "2026-09-14T12:00:00Z"}))
        with self.assertRaises(AuditError):
            self.policy.plan([obs], WHEN)

    def test_unknown_copy_cannot_be_hidden_by_clean_copy(self):
        from dataclasses import replace
        store = EvidenceStore.__new__(EvidenceStore)
        store.subject_resources = lambda user, cutoff: {"backup_900"}
        store.scopes = []
        store.by_resource = {"backup_900": [
            replace(observation("backup_900", "BACKUP_ARCHIVE", "UNKNOWN", "evidence_1"), replica="failover"),
            replace(observation("backup_900", "BACKUP_ARCHIVE", "BLOCKED", "evidence_2"), replica="primary"),
        ]}
        self.assertEqual(self.policy.plan(store.current("user", WHEN))[0], "INCOMPLETE")

    def test_stale_source_or_output_cannot_be_packaged(self):
        import hashlib
        from unittest.mock import patch
        import package
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".cache") as directory:
            root = Path(directory)
            (root / ".cache").mkdir()
            output = root / "output.csv"
            output.write_text("candidate")
            for source_hash, output_hash in [("stale", hashlib.sha256(output.read_bytes()).hexdigest()), (package.source_digest(), "stale")]:
                (root / ".cache/run_summary.json").write_text(json.dumps(dict(source_sha256=source_hash, output_sha256=output_hash)))
                with patch.object(package, "ROOT", root), self.assertRaises(ValueError):
                    package.preflight()

    def test_full_dataset_prediction_does_not_require_sample_answers(self):
        import shutil
        from core import IdentityIndex
        from main import ROOT, load_requests, predict
        dataset = ROOT / "dataset"
        if not dataset.is_dir():
            self.skipTest("Participant dataset is required for the integration test")
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            clone = Path(directory) / "dataset"
            clone.mkdir()
            for name in ("deletion_requests.csv", "user_identities.csv", "user_audit_log.csv", "system_activity.csv", "deletion_rules.csv", "evidence_files.csv"):
                shutil.copyfile(dataset / name, clone / name)
            shutil.copytree(dataset / "evidence", clone / "evidence")
            identities = IdentityIndex(clone)
            store = EvidenceStore(clone, identities, ROOT / ".cache")
            requests = load_requests(clone / "deletion_requests.csv")
            rows, _ = predict(requests, identities, store, Policy(clone))
            self.assertEqual(len(rows), len(requests))
            self.assertEqual([r["case_id"] for r in rows], sorted(r["case_id"] for r in requests))
            self.assertFalse((clone / "sample_output.csv").exists())

    def test_indirect_catalog_alias_cannot_leak_future_identity_link(self):
        from collections import defaultdict
        from core import IdentityIndex
        index = IdentityIndex.__new__(IdentityIndex)
        index.owners, index.values = defaultdict(set), defaultdict(set)
        index.add("user_900", "person@example.invalid")
        index.available_values = lambda user, cutoff: index.values[user]
        store = EvidenceStore.__new__(EvidenceStore)
        store.identities = index
        store.links, store.relationships = defaultdict(list), defaultdict(list)
        store.observations = []
        store.times = {"evidence_1": WHEN}
        later = timestamp("2026-09-15T12:07:00Z")
        store.aliases = {"STATEMENT-ABC": [dict(resource_id="export_900", event_time=later.isoformat())]}
        store.extracted_text = lambda path: "STATEMENT-ABC person@example.invalid"
        item = dict(file_id="evidence_1", captured_at=WHEN.isoformat())
        store.load_pdf(Path("unused.pdf"), item)
        self.assertEqual(store.observations[0].available, later)
        self.assertEqual(store.claimed_resources("user_900", WHEN), set())
        store.extracted_text = lambda path: "STATEMENT-ABC export_900 person@example.invalid"
        store.load_pdf(Path("unused.pdf"), item)
        self.assertEqual(store.observations[-1].available, WHEN)
        self.assertEqual(store.claimed_resources("user_900", WHEN), {"export_900"})

    def test_input_fingerprint_excludes_answers_but_tracks_policy_and_evidence(self):
        from main import ROOT, dataset_digest
        with tempfile.TemporaryDirectory(dir=ROOT / ".cache") as directory:
            root = Path(directory)
            (root / "evidence").mkdir()
            (root / "evidence/record.txt").write_text("original")
            (root / "evidence_files.csv").write_text("file_path\nevidence/record.txt\n")
            for name in ("deletion_requests.csv", "user_identities.csv", "user_audit_log.csv", "system_activity.csv", "deletion_rules.csv"):
                (root / name).write_text("input")
            initial = dataset_digest(root)
            (root / "sample_output.csv").write_text("evaluation only")
            self.assertEqual(dataset_digest(root), initial)
            (root / "deletion_rules.csv").write_text("changed")
            changed_policy = dataset_digest(root)
            self.assertNotEqual(changed_policy, initial)
            (root / "evidence/record.txt").write_text("changed evidence")
            self.assertNotEqual(dataset_digest(root), changed_policy)

    def _review_fixture(self, observations, claimed):
        """Small explicit lineage fixture, independent of sample answers."""
        from collections import defaultdict
        from core import IdentityIndex
        index = IdentityIndex.__new__(IdentityIndex)
        index.owners, index.values = defaultdict(set), defaultdict(set)
        index.snapshot = {"user_900": dict(updated_at=WHEN.isoformat(), email="person@example.invalid", phone="", email_hash="")}
        index.history = defaultdict(list)
        index.add("user_900", "user_900")
        index.add("user_900", "person@example.invalid")
        store = EvidenceStore.__new__(EvidenceStore)
        store.identities = index
        store.links, store.relationships = defaultdict(list), defaultdict(list)
        store.explicit_owners = defaultdict(list)
        store.scopes, store.complete_scopes = [], set()
        store.observations = list(observations)
        store.by_resource = defaultdict(list)
        store.times = {}
        for obs in observations:
            store.by_resource[obs.resource].append(obs)
            store.times[obs.evidence] = obs.available
        for resource in claimed:
            store.link(resource, {"email": "person@example.invalid"}, WHEN)
        request = dict(case_id="review", email="person@example.invalid", requested_at="2026-09-01T12:00:00Z", reported_status="COMPLETE", reported_at="2026-09-02T12:00:00Z", audit_at=WHEN.isoformat(), request_text="Please delete my account.")
        return index, store, request

    def test_explicit_category_conflict_fails_independent_of_evidence_order(self):
        observations = [
            observation("support_900", "SUPPORT_ATTACHMENT", "PRESENT", "evidence_1", system="support_platform"),
            observation("support_900", "SUPPORT_MESSAGE", "PRESENT", "evidence_1", system="support_platform"),
        ]
        for ordered in [observations, list(reversed(observations))]:
            with self.subTest(first_category=ordered[0].category):
                _, store, _ = self._review_fixture(ordered, {"support_900"})
                with self.assertRaises(AuditError):
                    store.current("user_900", WHEN)

    def test_known_retention_expiry_survives_metadata_only_readback(self):
        from dataclasses import replace
        older = timestamp("2026-09-14T12:00:00Z")
        observations = [
            replace(observation("audit_record_900", "SECURITY_AUDIT_LOG", "PRESENT", "evidence_1", system="security_service", when=older), payload=json.dumps({"retention_until": "2026-09-14T23:59:59Z"})),
            replace(observation("audit_record_900", "SECURITY_AUDIT_LOG", "PRESENT", "evidence_2", system="security_service"), payload=json.dumps({"rows": 1, "integrity_check": "passed"})),
        ]
        _, store, _ = self._review_fixture(observations, {"audit_record_900"})
        with self.assertRaises(AuditError):
            self.policy.plan(store.current("user_900", WHEN), WHEN)

    def test_attributed_resource_without_admissible_state_is_not_complete(self):
        from dataclasses import replace
        from main import predict
        future = timestamp("2026-09-16T12:00:00Z")
        observations = [
            observation("account_900", "USER_PROFILE", "ABSENT", "evidence_1"),
            replace(observation("analytics_900", "ANALYTICS_PROFILE", "ANONYMIZED", "evidence_2", system="analytics_platform"), available=future),
        ]
        index, store, request = self._review_fixture(observations, {"account_900", "analytics_900"})
        with self.assertRaises(AuditError):
            predict([request], index, store, self.policy)

    def test_unknown_resource_state_has_explicit_uncertainty_diagnostic(self):
        from main import predict
        observations = [
            observation("account_900", "USER_PROFILE", "ABSENT", "evidence_1"),
            observation("backup_900", "BACKUP_ARCHIVE", "UNKNOWN", "evidence_2", system="backup_service"),
        ]
        index, store, request = self._review_fixture(observations, {"account_900", "backup_900"})
        rows, diagnostics = predict([request], index, store, self.policy)
        self.assertEqual(rows[0]["deletion_status"], "INCOMPLETE")
        self.assertTrue(any("backup_900" in diagnostic and any(word in diagnostic.casefold() for word in ("unknown", "uncertain", "unproven")) for diagnostic in diagnostics))
        self.assertFalse(any(step["phase"] == "FINDING" for step in json.loads(rows[0]["steps_json"])))

    def test_unrelated_user_and_evidence_permutation_do_not_change_result(self):
        from main import predict
        older = timestamp("2026-09-14T12:00:00Z")
        observations = [
            observation("account_900", "USER_PROFILE", "PRESENT", "evidence_1", when=older),
            observation("account_900", "USER_PROFILE", "ABSENT", "evidence_2"),
        ]
        index, store, request = self._review_fixture(observations, {"account_900"})
        expected = predict([request], index, store, self.policy)
        index, store, request = self._review_fixture(list(reversed(observations)), {"account_900"})
        index.snapshot["user_901"] = dict(updated_at=WHEN.isoformat(), email="other@example.invalid", phone="", email_hash="")
        index.add("user_901", "user_901")
        index.add("user_901", "other@example.invalid")
        store.link("account_901", {"email": "other@example.invalid"}, WHEN)
        store.by_resource["account_901"].append(observation("account_901", "USER_PROFILE", "PRESENT", "evidence_3"))
        store.times["evidence_3"] = WHEN
        self.assertEqual(predict([request], index, store, self.policy), expected)

    def test_post_cutoff_capture_cannot_change_earlier_prediction(self):
        from dataclasses import replace
        from main import predict
        observations = [observation("account_900", "USER_PROFILE", "ABSENT", "evidence_1")]
        index, store, request = self._review_fixture(observations, {"account_900"})
        expected = predict([request], index, store, self.policy)
        future_capture = timestamp("2026-09-16T12:00:00Z")
        earlier_observation = timestamp("2026-09-15T11:30:00Z")
        later_artifact = replace(observation("account_900", "USER_PROFILE", "PRESENT", "evidence_2", when=earlier_observation), available=future_capture)
        store.by_resource["account_900"].append(later_artifact)
        store.times["evidence_2"] = future_capture
        store.link("account_900", {"email": "person@example.invalid"}, future_capture)
        self.assertEqual(predict([request], index, store, self.policy), expected)

    def test_removing_required_state_proof_cannot_create_confident_complete(self):
        from main import predict
        observations = [
            observation("account_900", "USER_PROFILE", "ABSENT", "evidence_1"),
            observation("analytics_900", "ANALYTICS_PROFILE", "ANONYMIZED", "evidence_2", system="analytics_platform"),
        ]
        index, store, request = self._review_fixture(observations, {"account_900", "analytics_900"})
        self.assertEqual(predict([request], index, store, self.policy)[0][0]["deletion_status"], "COMPLETE")
        store.by_resource["analytics_900"].clear()
        with self.assertRaises(AuditError):
            predict([request], index, store, self.policy)

    def test_consistent_resource_renaming_preserves_semantic_plan(self):
        from main import predict
        original = [observation("account_900", "USER_PROFILE", "PRESENT", "evidence_1")]
        index, store, request = self._review_fixture(original, {"account_900"})
        expected, expected_diagnostics = predict([request], index, store, self.policy)
        renamed = [observation("opaque-profile-reference", "USER_PROFILE", "PRESENT", "evidence_1")]
        index, store, request = self._review_fixture(renamed, {"opaque-profile-reference"})
        actual, actual_diagnostics = predict([request], index, store, self.policy)
        steps = json.loads(actual[0]["steps_json"])
        for step in steps:
            self.assertEqual(step["resource_id"], "opaque-profile-reference")
            step["resource_id"] = "account_900"
        actual[0]["steps_json"] = json.dumps(steps, ensure_ascii=False, separators=(",", ":"))
        self.assertEqual((actual, actual_diagnostics), (expected, expected_diagnostics))

    def test_shared_identifier_does_not_attribute_resource_to_both_users(self):
        index, store, _ = self._review_fixture([], set())
        index.snapshot["user_901"] = dict(updated_at=WHEN.isoformat(), email="person@example.invalid", phone="", email_hash="")
        index.add("user_901", "person@example.invalid")
        store.link("account_900", {"email": "person@example.invalid"}, WHEN)
        self.assertEqual(store.subject_resources("user_900", WHEN), set())
        self.assertEqual(store.subject_resources("user_901", WHEN), set())
        store.link("account_900", {"user_id": "user_900"}, WHEN)
        self.assertEqual(store.subject_resources("user_900", WHEN), {"account_900"})
        self.assertEqual(store.subject_resources("user_901", WHEN), set())

    def test_new_retention_condition_supersedes_older_expiry(self):
        from dataclasses import replace
        older = timestamp("2026-09-14T12:00:00Z")
        observations = [
            replace(observation("audit_record_900", "SECURITY_AUDIT_LOG", "PRESENT", "evidence_1", when=older), payload=json.dumps({"retention_until": "2026-09-14T23:59:59Z"})),
            replace(observation("audit_record_900", "SECURITY_AUDIT_LOG", "PRESENT", "evidence_2"), payload=json.dumps({"retain_until": "2030-01-01T00:00:00Z"})),
        ]
        for ordered in (observations, list(reversed(observations))):
            _, store, _ = self._review_fixture(ordered, {"audit_record_900"})
            self.assertEqual(self.policy.plan(store.current("user_900", WHEN), WHEN)[0], "COMPLETE")

    def test_failed_or_unrecorded_regressions_block_packaging(self):
        import hashlib
        from unittest.mock import patch
        import package
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".cache") as directory:
            root = Path(directory)
            (root / ".cache").mkdir()
            (root / "dataset").mkdir()
            (root / "output.csv").write_text("candidate")
            (root / "dataset/deletion_requests.csv").write_text("requests")
            run = dict(source_sha256="source", dataset_sha256="inputs",
                       output_sha256=hashlib.sha256((root / "output.csv").read_bytes()).hexdigest(),
                       requests_sha256=hashlib.sha256((root / "dataset/deletion_requests.csv").read_bytes()).hexdigest())
            (root / ".cache/run_summary.json").write_text(json.dumps(run))
            for evaluation in ({}, {"tests_passed": False}):
                (root / ".cache/evaluation_summary.json").write_text(json.dumps(evaluation))
                with patch.object(package, "ROOT", root), patch.object(package, "source_digest", return_value="source"), patch.object(package, "dataset_digest", return_value="inputs"):
                    with self.assertRaisesRegex(ValueError, "Regression tests"):
                        package.preflight()


if __name__ == "__main__":
    unittest.main()
