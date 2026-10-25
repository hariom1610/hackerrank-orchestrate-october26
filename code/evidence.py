"""Evidence adapters. All decisions preserve provenance and availability time."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from dataclasses import replace
from pathlib import Path

from core import AuditError, IdentityIndex, Observation, RESOURCE, TOKEN, normalize, read_csv, timestamp


COLLECTIONS = {
    "customer_profiles": ("account_service", "USER_PROFILE"),
    "customer_search_documents": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_analytics_reports": ("analytics_platform", "ANALYTICS_PROFILE"),
    "customer_analytics_profiles": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support_conversations": ("support_platform", "SUPPORT_MESSAGE"),
    "support_records": ("support_platform", "SUPPORT_MESSAGE"),
    "support_attachments": ("support_platform", "SUPPORT_ATTACHMENT"),
    "ticket_attachments": ("support_platform", "SUPPORT_ATTACHMENT"),
    "retained_order_records": ("legal_service", "LEGAL_HOLD_RECORD"),
    "search_documents_primary": ("search_service", "SEARCH_INDEX_ENTRY"),
    "customer_export_jobs": ("export_service", "USER_EXPORT"),
    "customer_exports": ("export_service", "USER_EXPORT"),
    "connector_configurations": ("integration_service", "DATA_FLOW"),
    "connector_subscriptions": ("integration_service", "DATA_FLOW"),
    "backup_catalog": ("backup_service", "BACKUP_ARCHIVE"),
    "backup_restore_entries": ("backup_service", "BACKUP_ARCHIVE"),
    "security_audit_events": ("security_service", "SECURITY_AUDIT_LOG"),
    "security_audit_records": ("security_service", "SECURITY_AUDIT_LOG"),
    "deleted_customer_references": ("identity_service", "ACCOUNT_TOMBSTONE"),
}
PREFIXES = {
    "account": ("account_service", "USER_PROFILE"),
    "search": ("search_service", "SEARCH_INDEX_ENTRY"),
    "analytics": ("analytics_platform", "ANALYTICS_PROFILE"),
    "support": ("support_platform", "SUPPORT_MESSAGE"),
    "export": ("export_service", "USER_EXPORT"),
    "marketing": ("marketing_platform", "MARKETING_PROFILE"),
    "data_flow": ("integration_service", "DATA_FLOW"),
    "backup": ("backup_service", "BACKUP_ARCHIVE"),
    "audit_record": ("security_service", "SECURITY_AUDIT_LOG"),
    "tombstone": ("identity_service", "ACCOUNT_TOMBSTONE"),
    "cache": ("cache_service", "CACHE_ENTRY"),
    "email_log": ("notification_service", "EMAIL_DELIVERY_LOG"),
    "legal_hold": ("legal_service", "LEGAL_HOLD_RECORD"),
    "telemetry": ("analytics_platform", "PRODUCT_TELEMETRY"),
    "identifier": ("identity_service", "SECONDARY_IDENTIFIER"),
    "object": ("object_storage", "SUPPORT_ATTACHMENT"),
}
RECORD_FIELDS = {"name", "full_name", "first_name", "last_name", "display_name", "email", "phone", "email_hash", "requester_name", "requester_email", "requester_phone", "owner_email", "owner_phone", "customer_email", "address", "postal_address", "shipping_address", "billing_address"}
STABLE_FIELDS = {"user_id", "subject_reference", "customer_reference"}


def prefix_kind(resource):
    return PREFIXES.get(resource.rsplit("_", 1)[0], ("", ""))


def nonempty(value):
    return value is not None and str(value).strip().casefold() not in {"", "null", "none", "[redacted]", "redacted", "[removed]"}


def identifiable(record, stable=False):
    if isinstance(record, dict):
        for key, value in record.items():
            if key in RECORD_FIELDS | (STABLE_FIELDS if stable else set()) and nonempty(value):
                return True
            if isinstance(value, (dict, list)) and identifiable(value, stable):
                return True
            if key in {"message_text", "message_excerpt"} and TOKEN.search(str(value)):
                return True
    elif isinstance(record, list):
        return any(identifiable(x, stable) for x in record)
    return False


def bool_value(value):
    if str(value).casefold() in {"true", "1", "yes"}:
        return True
    if str(value).casefold() in {"false", "0", "no"}:
        return False
    raise AuditError(f"Invalid evidence boolean: {value!r}")


def same_ocr_email(left, right):
    """Permit one domain glyph error only when local parts agree exactly.

    Used to detect OCR contradictions, never to assign an identity to evidence.
    """
    a, _, domain_a = left.partition("@")
    b, _, domain_b = right.partition("@")
    if a != b:
        return False
    if domain_a == domain_b:
        return True
    if len(domain_a) == len(domain_b):
        return sum(x != y for x, y in zip(domain_a, domain_b)) == 1
    short, long = sorted((domain_a, domain_b), key=len)
    return len(long) == len(short) + 1 and any(long[:i] + long[i + 1:] == short for i in range(len(long)))


def record_state(category, record):
    if category == "DATA_FLOW":
        return "ACTIVE" if bool_value(record["enabled"]) else "DISABLED"
    if category == "BACKUP_ARCHIVE":
        return "ACTIVE" if bool_value(record["restore_allowed"]) else "BLOCKED"
    if category == "ACCOUNT_TOMBSTONE":
        raw_references = [record[k] for k in STABLE_FIELDS if nonempty(record.get(k))]
        if any(not isinstance(value, str) for value in raw_references):
            raise AuditError("Account tombstone references must be scalar strings")
        references = [value.strip() for value in raw_references]
        if not references or any("@" in value or value.startswith("+") for value in references):
            raise AuditError("Account tombstone is missing a permitted stable internal reference")
    if category in {"SUPPORT_MESSAGE", "ACCOUNT_TOMBSTONE", "EMAIL_DELIVERY_LOG"}:
        return "PRESENT" if identifiable(record) else "REDACTED"
    if category in {"ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"}:
        return "PRESENT" if identifiable(record, stable=True) else "ANONYMIZED"
    return "PRESENT"


class EvidenceStore:
    def __init__(self, dataset: Path, identities: IdentityIndex, cache: Path):
        self.dataset, self.identities, self.cache = dataset.resolve(), identities, cache
        self.observations = []
        self.links = defaultdict(list)
        self.relationships = defaultdict(list)
        self.scopes = []
        self.complete_scopes = set()
        self.times = {}
        self.aliases = defaultdict(list)
        self.explicit_owners = defaultdict(list)
        self.identity_conflicts = []
        self.activities = read_csv(dataset / "system_activity.csv", ("activity_id", "event_time", "event_type", "source_system", "target_system", "resource_id", "details", "reported_result"), "activity_id")
        for row in self.activities:
            when = timestamp(row["event_time"])
            self.times[row["activity_id"]] = when
            # Activities establish identity edges, never resulting record state.
            self.link(row["resource_id"], row["details"], when)
            if row["event_type"] == "LINK_RESOURCE_IDENTITY":
                alias = re.search(r"\(([^)]+)\)", row["details"])
                if alias:
                    self.aliases[alias.group(1)].append(row)
        manifest = read_csv(dataset / "evidence_files.csv", ("file_id", "file_path", "origin", "captured_at"), "file_id")
        self.counts = defaultdict(int)
        self.extraction_stats = defaultdict(int)
        self.extraction_backends = defaultdict(int)
        for item in manifest:
            path = (self.dataset / item["file_path"]).resolve()
            if not path.is_relative_to(self.dataset / "evidence") or not path.is_file():
                raise AuditError("Evidence path is missing or escapes dataset/evidence")
            self.times[item["file_id"]] = timestamp(item["captured_at"])
            self.counts[path.suffix] += 1
            adapter = {".json": self.load_json, ".sql": self.load_sql, ".log": self.load_log, ".txt": self.load_text, ".pdf": self.load_pdf, ".png": self.load_image}.get(path.suffix)
            if not adapter:
                raise AuditError(f"Unsupported evidence format {path.suffix}")
            adapter(path, item)
        self.by_resource = defaultdict(list)
        for obs in self.observations:
            self.by_resource[obs.resource].append(obs)

    def link(self, resource, payload, available):
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        for user in self.identities.match(text):
            tokens = {normalize(v) for v in TOKEN.findall(text)}
            self.links[resource].append((user, available, tokens))
        if isinstance(payload, dict):
            source = payload.get("source_resource_id")
            if isinstance(source, str) and RESOURCE.fullmatch(source):
                self.relationships[resource].append((source, available))
                self.relationships[source].append((resource, available))

    def add(self, item, resource, system, category, state, when, payload, replica="", category_explicit=True, available_after=None):
        if not resource or not category or not system:
            raise AuditError("Incomplete normalized evidence")
        observed = timestamp(when) if isinstance(when, str) else when
        available = self.times[item["file_id"]]
        if available_after is not None:
            available = max(available, available_after)
        text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)
        self.link(resource, payload, max(observed, available))
        self.observations.append(Observation(system, resource, category, state, observed, available, item["file_id"], text, replica, category_explicit))

    def scope(self, item, system, category, when, resources, replica=""):
        self.scopes.append((item, system, category, timestamp(when), set(resources), replica))

    def load_json(self, path, item):
        obj = json.loads(path.read_text(encoding="utf-8"))
        if "service_exports" in obj:
            groups = {"profile_lookups": "USER_PROFILE", "profiles": "ANALYTICS_PROFILE", "restore_entries": "BACKUP_ARCHIVE", "exports": "USER_EXPORT", "connectors": "DATA_FLOW", "index_queries": "SEARCH_INDEX_ENTRY", "audit_records": "SECURITY_AUDIT_LOG", "tickets": "SUPPORT_MESSAGE"}
            for system, exports in obj["service_exports"].items():
                for group, records in exports.items():
                    for record in records:
                        resource = record["resource_id"]
                        category = groups.get(group, prefix_kind(resource)[1])
                        actual = record.get("profile", record)
                        if "hits" in record:
                            actual = record["hits"].get("documents", [])
                        state = "ABSENT" if record.get("status_code") == 404 or ("hits" in record and record["hits"]["total"] == 0) else record_state(category, actual)
                        self.add(item, resource, system, category, state, record["observed_at"], record, category_explicit=group != "tickets")
            return
        snapshots = obj.get("snapshots", [obj])
        for snapshot in snapshots:
            when = snapshot.get("captured_at", snapshot.get("exported_at", item["captured_at"]))
            collection = snapshot.get("collection", "")
            system, category = COLLECTIONS.get(collection, (snapshot.get("data_store", ""), ""))
            records = snapshot.get("records", [])
            if category:
                self.scope(item, system, category, when, [r["resource_id"] for r in records])
            for record in records:
                resource = record["resource_id"]
                if "record_type" in record:
                    self.add(item, resource, record["system"], record["record_type"], self.result_state(record["result"]), record.get("recorded_at", when), record)
                else:
                    sy, cat = (system, category) if category else prefix_kind(resource)
                    self.add(item, resource, sy, cat, record_state(cat, record), when, record)

    @staticmethod
    def result_state(result):
        return {"NOT_FOUND": "ABSENT", "FOUND": "PRESENT", "IDENTIFIABLE": "PRESENT", "ACTIVE": "ACTIVE", "BLOCKED": "BLOCKED", "DISABLED": "DISABLED", "ANONYMIZED": "ANONYMIZED", "REDACTED": "REDACTED"}.get(result, result)

    def load_sql(self, path, item):
        # Never run supplied SQL against a disk database or permit ATTACH/extensions.
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        forbidden = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH}
        def authorize(action, a, b, db, source):
            if action in forbidden or (action == sqlite3.SQLITE_FUNCTION and str(b).lower() in {"load_extension", "readfile", "writefile"}):
                return sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_PRAGMA and a.lower() != "foreign_keys":
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        connection.set_authorizer(authorize)
        budget = 2000
        def progress():
            nonlocal budget
            budget -= 1
            return int(budget <= 0)
        connection.set_progress_handler(progress, 10000)
        try:
            connection.executescript(path.read_text(encoding="utf-8"))
            tables = [r[0] for r in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")]
            for table in tables:
                if table == "snapshot_scope":
                    continue
                quoted = '"' + table.replace('"', '""') + '"'
                rows = [dict(r) for r in connection.execute(f"SELECT * FROM {quoted}")]
                if table.startswith("customer_data_") and (not rows or "record_json" in rows[0]):
                    for row in rows:
                        record = json.loads(row["record_json"])
                        sy, cat = COLLECTIONS[row["collection_name"]]
                        self.add(item, row["resource_id"], row["origin_system"], cat, record_state(cat, record), item["captured_at"], record, table)
                    # These tables capture the full service inventory across replicas.
                    for collection, (sy, cat) in COLLECTIONS.items():
                        resources = [r["resource_id"] for r in rows if r.get("collection_name") == collection]
                        self.scope(item, sy, cat, item["captured_at"], resources, table)
                else:
                    base = "customer_profiles" if table.startswith("customer_profiles_") else table
                    if base not in COLLECTIONS:
                        raise AuditError(f"Unknown SQL evidence table {table}")
                    sy, cat = COLLECTIONS[base]
                    self.scope(item, sy, cat, item["captured_at"], [r["resource_id"] for r in rows], table)
                    # Native physical tables in a full SQL snapshot can be
                    # queried for an explicitly linked source ID. A serialized
                    # multi-service export is not the same completeness claim.
                    if "snapshot_scope" not in tables:
                        self.complete_scopes.add((item["file_id"], table))
                    for row in rows:
                        self.add(item, row["resource_id"], sy, cat, record_state(cat, row), item["captured_at"], row, table, category_explicit=table != "support_records")
        finally:
            connection.close()

    def load_log(self, path, item):
        traces = defaultdict(dict)
        for line in path.read_text(encoding="utf-8").splitlines():
            if not re.match(r"\d{4}-\d\d-\d\dT", line):
                continue
            when = line.split()[0]
            # Normalize cloud-escaped logfmt, JSON, syslog, pipe and app traces.
            clean = line.replace('\\"', '"')
            data = {}
            for key, quoted, bare in re.findall(r'(\w+)=(?:"([^"]*)"|([^\s]+))', clean):
                data[key] = quoted or bare
            if " {" in line:
                data.update(json.loads(line[line.index("{"):]))
            pipe = line.split(" | ")
            if len(pipe) >= 5:
                data.update(service=pipe[2], trace_id=pipe[3], event=pipe[4])
            bracket = re.match(r"\S+ \[\w+\] \[([^]]+)\] \[([^]]+)\] (\w+):", line)
            if bracket:
                data.update(service=bracket[1], trace_id=bracket[2], event=bracket[3])
            syslog = re.match(r"\S+ <\d+>1 \S+ (\S+) (\S+)", line)
            if syslog:
                data.update(service=syslog[1], trace_id=syslog[2])
            if "function" in data:
                data.update(service=data["function"], trace_id=data.get("requestId", ""))
            trace = data.get("trace_id", "")
            if trace:
                traces[trace].update(data)
                merged = traces[trace].copy()
            else:
                merged = data
            resource = data.get("resource_id")
            if not resource:
                continue
            event = data.get("event", "")
            sy, cat = prefix_kind(resource)
            sy = data.get("system", sy)
            state = None
            if event == "record_lookup":
                cat, state = data["record_type"], self.result_state(data["result"])
            elif event in {"profile_lookup_completed", "contact_query_completed", "contact_lookup_completed"}:
                state = "ABSENT" if data.get("rows") == "0" else "PRESENT"
                if event.startswith("contact"):
                    cat = "SECONDARY_IDENTIFIER"
            elif event == "index_query_completed":
                state = "ABSENT" if data.get("result") == "miss" or data.get("total_hits") == "0" else "PRESENT"
            elif event in {"message_pii_scan", "attachment_pii_scan", "analytics_identity_scan"}:
                state = "PRESENT"
                if event == "attachment_pii_scan":
                    cat = "SUPPORT_ATTACHMENT"
            elif event in {"analytics_profile_read", "analytics_profile_read_completed"}:
                state = "ANONYMIZED" if data.get("direct_identifiers") == "0" or not identifiable(data, True) else "PRESENT"
            elif event in {"message_read", "support_ticket_read_completed"}:
                state = "REDACTED" if data.get("redacted") == "true" or data.get("pii_fields") == "0" or not identifiable(data) else "PRESENT"
            elif event in {"connector_heartbeat", "connector_config_loaded", "connector_config_read_completed"}:
                state = "ACTIVE" if bool_value(data["enabled"]) else "DISABLED"
            elif event in {"restore_candidate_evaluated", "restore_authorization_completed", "restore_policy_read_completed"}:
                allowed = data.get("restore_allowed", data.get("eligible", data.get("allowed")))
                if allowed is None and data.get("decision") in {"deny", "allow"}:
                    allowed = data["decision"] == "allow"
                if allowed is not None:
                    state = "ACTIVE" if bool_value(allowed) else "BLOCKED"
            elif event == "audit_record_read_completed":
                state = "PRESENT" if data.get("rows") == "1" else "ABSENT"
            elif event in {"export_download_check_completed", "export_metadata_read_completed"}:
                state = "PRESENT" if bool_value(data.get("available", data.get("download_available", "true"))) else "ABSENT"
            if state:
                self.add(item, resource, sy, cat, state, when, merged, category_explicit=event != "support_ticket_read_completed")

    def load_text(self, path, item):
        for line in path.read_text(encoding="utf-8").splitlines():
            parts = line.lstrip("- ").split(" | ")
            if len(parts) == 6 and re.match(r"\d{4}-", parts[0]):
                when, sy, resource, cat, state, subject = parts
                self.add(item, resource, sy, cat, self.result_state(state), when, subject)

    def extracted_text(self, path, image=False):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        cache_path = self.cache / "extracted" / f"{digest}.txt"
        if cache_path.exists():
            self.extraction_stats["cache_hits"] += 1
            metadata = cache_path.with_suffix(".meta.json")
            if image and metadata.exists():
                self.extraction_backends[json.loads(metadata.read_text(encoding="utf-8"))["backend"]] += 0
            return cache_path.read_text(encoding="utf-8")
        if image:
            self.extraction_stats["ocr_calls"] += 1
            executable = os.environ.get("AUDIT_TESSERACT_CMD") or shutil.which("tesseract")
            if executable:
                backend = "Tesseract"
                result = subprocess.run([executable, str(path), "stdout", "--psm", "11"], capture_output=True, check=True, timeout=90)
                text = result.stdout.decode("utf-8")
            elif os.name == "nt":
                backend = "Windows.Media.Ocr"
                result = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(Path(__file__).with_name("ocr_windows.ps1")), "-ImagePath", str(path)], capture_output=True, check=True, timeout=90)
                text = result.stdout.decode("utf-8-sig")
            else:
                raise AuditError("Screenshot extraction requires Tesseract (see README)")
        else:
            self.extraction_stats["pdf_extractions"] += 1
            from pypdf import PdfReader
            text = "\n".join(page.extract_text() or "" for page in PdfReader(path).pages)
        if not text.strip():
            raise AuditError(f"No text extracted from {path.name}")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(text, encoding="utf-8")
        if image:
            self.extraction_backends[backend] += 1
            cache_path.with_suffix(".meta.json").write_text(json.dumps({"backend": backend}), encoding="utf-8")
        return text

    def load_pdf(self, path, item):
        text = self.extracted_text(path)
        resources = {resource: self.times[item["file_id"]] for resource in RESOURCE.findall(text)}
        for alias, activities in self.aliases.items():
            # A person listed in a multi-person register does not prove that
            # their separately cataloged account reference exists in that PDF.
            if alias in text and not alias.startswith("user_"):
                for activity in activities:
                    resource = activity["resource_id"]
                    available = max(self.times[item["file_id"]], timestamp(activity["event_time"]))
                    resources[resource] = min(resources.get(resource, available), available)
        for resource, available in resources.items():
            sy, cat = prefix_kind(resource)
            if cat == "SUPPORT_MESSAGE":
                cat = "SUPPORT_ATTACHMENT"
            self.add(item, resource, sy, cat, "PRESENT", item["captured_at"], text, available_after=available)

    def load_image(self, path, item):
        text = self.extracted_text(path, image=True)
        text = re.sub(r"\b(account|search|analytics|support|export|marketing|backup|tombstone)\s*_\s*(\d+)", r"\1_\2", text)
        text = re.sub(r"\buser[ _]+(\d+)\b", r"user_\1", text)
        # A console can display decoys. Catalog aliases establish the resource;
        # screenshot text alone must not link every row to every visible person.
        for alias, activities in self.aliases.items():
            if alias not in text:
                continue
            for activity in activities:
                resource = activity["resource_id"]
                available = self.times[item["file_id"]]
                if resource not in RESOURCE.findall(text):
                    available = max(available, timestamp(activity["event_time"]))
                sy, cat = prefix_kind(resource)
                if cat == "BACKUP_ARCHIVE":
                    # A backup browser proves existence, not restore permission.
                    # Permission requires a policy readback in another adapter.
                    state = "UNKNOWN"
                elif cat == "DATA_FLOW":
                    state = "ACTIVE" if re.search(r"continuous|running|enabled", text, re.I) else "DISABLED"
                elif cat == "ACCOUNT_TOMBSTONE":
                    state = "PRESENT" if "@" in text or re.search(r"\+\d[\d -]{8,}", text) else "REDACTED"
                else:
                    state = "PRESENT"
                selected = text[text.rfind(alias):]
                # Detail panels can occur after a table of unrelated customers.
                # For a single customer page, keep its header contact fields.
                if cat in {"USER_PROFILE", "MARKETING_PROFILE", "ANALYTICS_PROFILE", "SECURITY_AUDIT_LOG", "SUPPORT_MESSAGE"}:
                    selected = text
                owners = self.identities.match(selected)
                catalog_owners = self.identities.match(activity["details"])
                visible_emails = {normalize(v) for v in TOKEN.findall(selected) if "@" in v}
                catalog_emails = {v for u in catalog_owners for v in self.identities.values[u] if "@" in v}
                contradictory_email = bool(visible_emails and catalog_emails and not any(same_ocr_email(a, b) for a in visible_emails for b in catalog_emails))
                if (owners and owners.isdisjoint(catalog_owners)) or contradictory_email:
                    self.identity_conflicts.append(f"{item['file_id']}: {resource} artifact owner contradicts catalog claim")
                    self.explicit_owners[resource].append((available, owners))
                self.add(item, resource, sy, cat, state, item["captured_at"], selected, available_after=available)

    def claimed_resources(self, user, cutoff):
        allowed = self.identities.available_values(user, cutoff)
        # A shared historical identifier cannot authorize changes to either
        # person's record. A separate unique token can still establish lineage.
        allowed = {token for token in allowed if {
            owner for owner in self.identities.owners.get(token, set())
            if token in self.identities.available_values(owner, cutoff)
        } == {user}}
        resources = {rid for rid, links in self.links.items() if any(u == user and when <= cutoff and bool(tokens & allowed) for u, when, tokens in links)}
        pending = list(resources)
        while pending:
            for related, available in self.relationships.get(pending.pop(), []):
                if available <= cutoff and related not in resources:
                    resources.add(related)
                    pending.append(related)
        return resources

    def subject_resources(self, user, cutoff):
        resources = self.claimed_resources(user, cutoff)
        for rid, assertions in self.explicit_owners.items():
            visible = [(when, owners) for when, owners in assertions if when <= cutoff]
            if visible and user not in max(visible, key=lambda pair: pair[0])[1]:
                resources.discard(rid)
        return resources

    def current(self, user, cutoff):
        resources = self.subject_resources(user, cutoff)
        candidates = defaultdict(list)
        for resource in resources:
            for obs in self.by_resource.get(resource, []):
                if obs.observed <= cutoff and obs.available <= cutoff:
                    candidates[resource].append(obs)
        # Absence is a query against a complete snapshot, not an activity claim.
        subject_files = {o.evidence for group in candidates.values() for o in group}
        for item, sy, cat, when, present, replica in self.scopes:
            if when > cutoff or self.times[item["file_id"]] > cutoff or cat not in {"USER_PROFILE", "SEARCH_INDEX_ENTRY", "SECONDARY_IDENTIFIER", "USER_EXPORT", "SUPPORT_ATTACHMENT", "MARKETING_PROFILE"}:
                continue
            if item["file_id"] not in subject_files and (item["file_id"], replica) not in getattr(self, "complete_scopes", set()):
                continue
            for resource in resources - present:
                prior = [o for o in candidates.get(resource, []) if o.system == sy and o.category == cat]
                # Explicit lineage can identify an absent source record even
                # when no positive observation of that source survives.
                if prior or (prefix_kind(resource) == (sy, cat) and replica):
                    candidates[resource].append(Observation(sy, resource, cat, "ABSENT", when, self.times[item["file_id"]], item["file_id"], "Complete inventory query returned no record", replica))
        selected = []
        missing = resources - candidates.keys()
        if missing:
            raise AuditError("Attributed resources have no admissible state readback: " + ", ".join(sorted(missing)))
        for resource, observations in sorted(candidates.items()):
            explicit = [o for o in observations if o.category_explicit]
            if len({o.category for o in explicit}) > 1:
                raise AuditError(f"Conflicting explicit evidence categories for {resource}")
            category = max(explicit, key=lambda o: o.observed).category if explicit else None
            copies = defaultdict(list)
            for obs in observations:
                if category and obs.category != category and not obs.category_explicit:
                    if {obs.category, category} != {"SUPPORT_MESSAGE", "SUPPORT_ATTACHMENT"}:
                        raise AuditError("Conflicting evidence categories require review")
                    # A generic ticket wrapper does not turn an explicitly
                    # identified attachment into a shared support message.
                    state = "ABSENT" if obs.state == "ABSENT" else "PRESENT"
                    obs = replace(obs, category=category, state=state)
                copies[obs.replica].append(obs)
            current = []
            for copy in copies.values():
                newest = max(o.observed for o in copy)
                current.extend(o for o in copy if o.observed == newest)
            # An exposed replica defeats a same-time clean primary. Prefer a
            # direct readback over a bundle when observations are simultaneous.
            current.sort(key=lambda o: ({"PRESENT": 2, "ACTIVE": 2, "UNKNOWN": 1}.get(o.state, 0), o.observed, o.available, int(o.evidence.split("_")[-1])), reverse=True)
            chosen = current[0]
            if chosen.category in {"SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD"}:
                # A metadata-only readback does not erase known policy facts.
                facts = {}
                for obs in sorted(observations, key=lambda o: (o.observed, o.available, o.evidence)):
                    try:
                        record = json.loads(obs.payload)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if not isinstance(record, dict):
                        continue
                    for key in ("retention_until", "retained_until", "retain_until", "legal_hold_active"):
                        if key in record and record[key] is not None:
                            canonical = "legal_hold_active" if key == "legal_hold_active" else "retention_until"
                            facts[canonical] = record[key]
                chosen = replace(chosen, policy_facts=tuple(sorted(facts.items())))
            selected.append(chosen)
        return selected
