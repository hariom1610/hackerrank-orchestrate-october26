"""Validated domain types, exact identity resolution, and ordered policy plans."""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


class AuditError(ValueError):
    """A supplied input cannot support a safe audit."""


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            raise ValueError("timezone required")
        return result.astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError) as exc:
        raise AuditError(f"Invalid ISO-8601 timestamp: {value!r}") from exc


def read_csv(path: Path, required: tuple[str, ...], unique: str = "") -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not set(required) <= set(reader.fieldnames or []):
            raise AuditError(f"Missing required columns in {path.name}")
        rows = list(reader)
    seen = set()
    for n, row in enumerate(rows, 2):
        if None in row or any(row.get(k) is None for k in required):
            raise AuditError(f"Malformed CSV row {n} in {path.name}")
        if unique:
            key = row[unique]
            if not key or key in seen:
                raise AuditError(f"Empty/duplicate {unique} in {path.name}, row {n}")
            seen.add(key)
    return rows


TOKEN = re.compile(r"[\w.+%'-]+@[\w.-]+\.[a-zA-Z]{2,}|\buser_\d+\b|\b[a-fA-F0-9]{64}\b|\+\d[\d ()-]{6,}\d")
RESOURCE = re.compile(r"\b(?:account|search|analytics|support|export|marketing|backup|data_flow|audit_record|tombstone|cache|email_log|legal_hold|telemetry|identifier)_\d+\b")


def normalize(value: str) -> str:
    value = str(value).strip().casefold()
    return re.sub(r"\D", "", value) if value.startswith("+") else value


class IdentityIndex:
    def __init__(self, dataset: Path):
        self.values = defaultdict(set)
        self.owners = defaultdict(set)
        self.snapshot = {}
        self.history = defaultdict(list)
        for row in read_csv(dataset / "user_identities.csv", ("user_id", "name", "email", "phone", "email_hash", "updated_at"), "user_id"):
            self.snapshot[row["user_id"]] = row
            timestamp(row["updated_at"])
            for key in ("user_id", "email", "phone", "email_hash"):
                self.add(row["user_id"], row[key])
        for row in read_csv(dataset / "user_audit_log.csv", ("audit_id", "user_id", "event_time", "field_name", "old_value", "new_value"), "audit_id"):
            timestamp(row["event_time"])
            if row["user_id"] not in self.snapshot:
                raise AuditError("Audit history references an unknown user")
            self.history[row["user_id"]].append(row)
            if row["field_name"] in {"email", "phone", "email_hash"}:
                for key in ("old_value", "new_value"):
                    self.add(row["user_id"], row[key])
        # Historical email hashes are deterministically recoverable even if omitted.
        for user, values in list(self.values.items()):
            for value in list(values):
                if "@" in value:
                    self.add(user, hashlib.sha256(value.encode()).hexdigest())

    def add(self, user: str, value: str):
        if value:
            value = normalize(value)
            self.values[user].add(value)
            self.owners[value].add(user)

    def match(self, payload) -> set[str]:
        text = json.dumps(payload, ensure_ascii=False) if not isinstance(payload, str) else payload
        return set().union(*(self.owners.get(normalize(t), set()) for t in TOKEN.findall(text)))

    def resolve(self, email: str, cutoff: datetime | None = None) -> str:
        users = self.owners.get(normalize(email), set())
        if cutoff is not None:
            users = {user for user in users if normalize(email) in self.available_values(user, cutoff)}
        if len(users) != 1:
            raise AuditError("Request identity is missing or ambiguous")
        return next(iter(users))

    def available_values(self, user: str, cutoff: datetime) -> set[str]:
        """Do not let future identity changes create a historical evidence link."""
        row = self.snapshot[user]
        values = {normalize(user)}
        history = self.history[user]
        for field in ("email", "phone", "email_hash"):
            changes = sorted((r for r in history if r["field_name"] == field), key=lambda r: timestamp(r["event_time"]))
            if timestamp(row["updated_at"]) <= cutoff:
                values.add(normalize(row[field]))
            for change in changes:
                if timestamp(change["event_time"]) <= cutoff:
                    values.update(normalize(change[k]) for k in ("old_value", "new_value"))
                else:
                    break
        values.update(hashlib.sha256(v.encode()).hexdigest() for v in list(values) if "@" in v)
        return values - {""}


def deletion_authorized(text: str) -> bool:
    """Conservative multilingual intent rules; unknown intent fails visibly."""
    t = text.casefold().replace("’", "'")
    negatives = ("don't delete", "do not delete", "not a request to erase", "marketing lists only", "stop the promotional", "resetting the login", "copy of last year", "surname is misspelled", "mobile number", "change the email", "portable format")
    if any(x in t for x in negatives):
        return False
    positives = ("delet", "erase", "erased", "remove my account", "remove my profile", "remove records", "remove that search", "close this account", "close my account", "close the account", "account closed", "exclusão", "eliminación", "eliminar mi cuenta", "suppression", "삭제", "削除", "fully removed", "profile is gone", "personal details", "identifiable analytics")
    if any(x in t for x in positives):
        return True
    if any(x in t for x in ("copy", "information request", "correct", "access my", "marketing", "promotional")):
        return False
    raise AuditError("Unrecognized request intent; review or extend the language adapter")


@dataclass(frozen=True)
class Observation:
    system: str
    resource: str
    category: str
    state: str
    observed: datetime
    available: datetime
    evidence: str
    payload: str
    replica: str = ""
    category_explicit: bool = True
    policy_facts: tuple[tuple[str, object], ...] = ()


OPERATIONS = {
    "FINDING": ["REPORT_REMAINING_RECORD", "REPORT_EXPOSED_PII", "REPORT_ACTIVE_DATA_FLOW", "REPORT_RESTORE_RISK"],
    "REMEDIATION": ["DISABLE_DATA_FLOW", "BLOCK_RESTORE", "DELETE_RECORD", "REDACT_RECORD", "ANONYMIZE_RECORD"],
    "VERIFICATION": ["VERIFY_RECORD_ABSENT", "VERIFY_RECORD_PRESENT", "VERIFY_RECORD_REDACTED", "VERIFY_RECORD_ANONYMIZED", "VERIFY_DATA_FLOW_DISABLED", "VERIFY_RESTORE_BLOCKED"],
}
STATES = dict(zip(sum(OPERATIONS.values(), []), ["PRESENT", "PRESENT", "ACTIVE", "ACTIVE", "DISABLED", "BLOCKED", "ABSENT", "REDACTED", "ANONYMIZED", "ABSENT", "PRESENT", "REDACTED", "ANONYMIZED", "DISABLED", "BLOCKED"]))
FIELDS = {"step_no", "phase", "system_id", "resource_id", "operation", "state", "evidence_id"}


class Policy:
    def __init__(self, dataset: Path):
        self.actions = {}
        for row in read_csv(dataset / "deletion_rules.csv", ("rule_id", "data_category", "condition", "required_action"), "rule_id"):
            if row["required_action"] not in {"DELETE", "REDACT", "ANONYMIZE", "RETAIN"}:
                raise AuditError("Unsupported policy action")
            if row["data_category"] in self.actions:
                raise AuditError("Multiple conditional rules need an explicit policy adapter")
            self.actions[row["data_category"]] = row["required_action"]

    def plan(self, observations: list[Observation], cutoff: datetime | None = None) -> tuple[str, list[dict]]:
        if not observations:
            raise AuditError("No observations support this deletion decision")
        findings, remediation, verification = [], [], []
        for obs in observations:
            category = obs.category
            if category in {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"}:
                try:
                    record = json.loads(obs.payload)
                except (json.JSONDecodeError, TypeError):
                    record = {}
                if obs.policy_facts:
                    record = dict(obs.policy_facts)
                if isinstance(record, dict):
                    expiry = next((record[k] for k in ("retention_until", "retained_until", "retain_until") if record.get(k)), None)
                    if expiry and timestamp(expiry) <= (cutoff or obs.observed):
                        raise AuditError("Retention condition has expired; supplied policy has no post-retention action")
                    if category == "LEGAL_HOLD_RECORD" and record.get("legal_hold_active") is False:
                        raise AuditError("Legal hold is inactive; supplied policy has no alternative action")
            if category == "DATA_FLOW":
                target, fix, verify = "DISABLED", "DISABLE_DATA_FLOW", "VERIFY_DATA_FLOW_DISABLED"
                finding = "REPORT_ACTIVE_DATA_FLOW"
            elif category == "BACKUP_ARCHIVE":
                target, fix, verify = "BLOCKED", "BLOCK_RESTORE", "VERIFY_RESTORE_BLOCKED"
                finding = "REPORT_RESTORE_RISK"
            else:
                action = self.actions.get(category)
                if not action:
                    raise AuditError(f"No policy for {category}")
                target, fix, verify = {
                    "DELETE": ("ABSENT", "DELETE_RECORD", "VERIFY_RECORD_ABSENT"),
                    "REDACT": ("REDACTED", "REDACT_RECORD", "VERIFY_RECORD_REDACTED"),
                    "ANONYMIZE": ("ANONYMIZED", "ANONYMIZE_RECORD", "VERIFY_RECORD_ANONYMIZED"),
                    "RETAIN": ("PRESENT", "", "VERIFY_RECORD_PRESENT"),
                }[action]
                finding = "REPORT_REMAINING_RECORD" if action == "DELETE" else "REPORT_EXPOSED_PII"
            compliant = obs.state == target
            if not compliant:
                if not fix:
                    raise AuditError("A mandatory retained record is missing; contract provides no restoration operation")
                if obs.state != "UNKNOWN":
                    findings.append(self.step(obs, "FINDING", finding, obs.evidence))
                remediation.append(self.step(obs, "REMEDIATION", fix, ""))
            verification.append(self.step(obs, "VERIFICATION", verify, obs.evidence))
        incomplete = bool(remediation)
        if incomplete:
            for step in verification:
                step["evidence_id"] = ""
        steps = findings + remediation + verification
        steps.sort(key=lambda s: (list(OPERATIONS).index(s["phase"]), OPERATIONS[s["phase"]].index(s["operation"]), s["system_id"], s["resource_id"]))
        for n, step in enumerate(steps, 1):
            step["step_no"] = n
        return ("INCOMPLETE" if incomplete else "COMPLETE"), steps

    @staticmethod
    def step(obs, phase, operation, evidence):
        return dict(step_no=0, phase=phase, system_id=obs.system, resource_id=obs.resource, operation=operation, state=STATES[operation], evidence_id=evidence)


def validate_output(rows: list[dict], requests: list[dict], evidence_times: dict[str, datetime]):
    if [r["case_id"] for r in rows] != sorted(r["case_id"] for r in requests):
        raise AuditError("Output case coverage or ordering mismatch")
    request_map = {r["case_id"]: r for r in requests}
    for row in rows:
        status = row["deletion_status"]
        steps = json.loads(row["steps_json"])
        request = request_map[row["case_id"]]
        if "request_text" in request and (status == "NOT_APPLICABLE") == deletion_authorized(request["request_text"]):
            raise AuditError("Output status disagrees with request authorization")
        if status not in {"COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"} or not isinstance(steps, list):
            raise AuditError("Invalid output status/steps")
        if status == "NOT_APPLICABLE" and steps:
            raise AuditError("Non-deletion request has steps")
        if status != "NOT_APPLICABLE" and not steps:
            raise AuditError("Deletion audit has no evidence-backed checks")
        previous = (-1, -1, "", "")
        seen = set()
        for n, step in enumerate(steps, 1):
            if not isinstance(step, dict) or set(step) != FIELDS or type(step["step_no"]) is not int or step["step_no"] != n:
                raise AuditError("Invalid step schema/numbering")
            if any(not isinstance(step[k], str) for k in FIELDS - {"step_no"}) or not step["system_id"] or not step["resource_id"]:
                raise AuditError("Invalid step field types or empty resource/system")
            phase, op = step["phase"], step["operation"]
            if phase not in OPERATIONS or op not in OPERATIONS[phase] or step["state"] != STATES[op]:
                raise AuditError("Invalid phase/operation/state")
            key = (list(OPERATIONS).index(phase), OPERATIONS[phase].index(op), step["system_id"], step["resource_id"])
            if key < previous:
                raise AuditError("Invalid step order")
            previous = key
            identity = (phase, step["system_id"], step["resource_id"])
            if identity in seen:
                raise AuditError("Duplicate or conflicting operations for the same resource and phase")
            seen.add(identity)
            cited = phase == "FINDING" or status == "COMPLETE"
            if status == "COMPLETE" and phase != "VERIFICATION":
                raise AuditError("Complete case contains proposed work")
            if cited:
                if step["evidence_id"] not in evidence_times or evidence_times[step["evidence_id"]] > timestamp(request_map[row["case_id"]]["audit_at"]):
                    raise AuditError("Evidence is missing or after audit cutoff")
            elif step["evidence_id"]:
                raise AuditError("Future step cites past evidence")
