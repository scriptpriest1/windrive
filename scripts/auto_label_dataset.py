"""Create WinDrive training pseudo-labels from stored raw diagnostic evidence.

This intentionally never reads Prediction records or loads a model. The labels are
deterministic evidence-rule pseudo-labels, not manually verified ground truth.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from app.database.models import Driver, ScanSession
from app.features.feature_engineer import build_features, validate_raw_evidence_records

DRIVER_FIELDS = ("driver_name", "file_name", "provider", "version", "driver_date", "driver_path", "device_name", "device_category", "signature_status", "driver_start_status", "device_status", "device_error_code")


def crash_evidence(scan):
    if not scan.crash_evidence:
        return []
    try:
        value = json.loads(scan.crash_evidence)
        return value if isinstance(value, list) else []
    except json.JSONDecodeError:
        return []


def raw_record(driver):
    events = [{"TimeCreated": event.event_time.isoformat() if event.event_time else None, "ProviderName": event.event_source, "Id": event.event_code, "LevelDisplayName": event.severity, "Message": event.description or "", "related_device": event.related_device} for event in driver.events]
    return {
        "driver": {field: getattr(driver, field) for field in DRIVER_FIELDS},
        "events": events,
        "crashes": crash_evidence(driver.scan),
        "reference_time": driver.scan.completed_at.isoformat() if driver.scan.completed_at else None,
    }


def label_from_evidence(features):
    """Return a deterministic pseudo-label and auditable reason from raw evidence features.

    Driver age, signature and version are deliberately not used for labelling.
    """
    errors = features["error_count"]
    critical = features["critical_event_count"]
    warnings = features["warning_count"]
    starts = features["driver_start_failure_count"]
    timeouts = features["timeout_count"]
    resets = features["device_reset_count"]
    crashes = features["crash_reference_count"]
    device_error = features["device_error_present"]
    repeated_errors = errors >= 3 or critical >= 2
    repeated_runtime_failures = timeouts + resets >= 3
    independent_failures = sum((starts > 0, crashes > 0, repeated_errors, repeated_runtime_failures))
    if (starts > 0 and (errors + critical + timeouts + resets > 0)) or (crashes > 0 and (errors + critical + timeouts + resets > 0)) or independent_failures >= 2:
        return "faulty", "strong_failure_evidence"
    if repeated_errors or repeated_runtime_failures:
        return "faulty", "repeated_failure_indicators"
    if errors > 0 or critical > 0 or warnings >= 2 or timeouts + resets > 0 or device_error:
        return "suspicious", "multiple_error_indicators" if sum((errors > 0, critical > 0, warnings >= 2, timeouts + resets > 0, bool(device_error))) >= 2 else "warning_or_single_investigation_indicator"
    return "normal", "no_significant_failure_evidence"


def auto_label_record(evidence):
    """Apply the single evidence-rule labelling source to a raw dataset record."""
    features = build_features(evidence["driver"], evidence["events"], evidence["crashes"], evidence.get("reference_time"))
    classification, reason = label_from_evidence(features)
    return {**evidence, "classification": classification, "label_source": "automatic_evidence_rules", "label_reason": reason}


def build_dataset():
    app = create_app()
    records, excluded, fingerprints = [], Counter(), set()
    with app.app_context():
        drivers = Driver.query.join(ScanSession).filter(ScanSession.status.in_(("completed", "failed"))).order_by(Driver.id).all()
        for driver in drivers:
            if not (driver.driver_name or driver.file_name):
                excluded["missing_driver_identity"] += 1
                continue
            evidence = raw_record(driver)
            # Events lacking timestamps cannot meet the raw dataset contract; do not invent one.
            if any(event["TimeCreated"] is None for event in evidence["events"]):
                excluded["event_missing_timestamp"] += 1
                continue
            # Ignore reference_time and labels when identifying unchanged evidence across scans.
            identity = {key: evidence[key] for key in ("driver", "events", "crashes")}
            fingerprint = hashlib.sha256(json.dumps(identity, sort_keys=True, default=str).encode()).hexdigest()
            if fingerprint in fingerprints:
                excluded["duplicate_evidence"] += 1
                continue
            fingerprints.add(fingerprint)
            records.append(auto_label_record(evidence))
    validate_raw_evidence_records(records)
    return records, excluded, len(drivers)


def main():
    records, excluded, processed = build_dataset()
    output = PROJECT_ROOT / "data" / "training" / "labelled_driver_data.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")
    counts = Counter(record["classification"] for record in records)
    print("Automatic labeling complete.")
    print(f"NORMAL: {counts['normal']}")
    print(f"SUSPICIOUS: {counts['suspicious']}")
    print(f"FAULTY: {counts['faulty']}")
    print(f"TOTAL: {len(records)}")
    print(f"RECORDS PROCESSED: {processed}")
    print(f"EXCLUDED: {sum(excluded.values())} ({dict(excluded)})")
    print(f"OUTPUT: {output.relative_to(PROJECT_ROOT)}")
    missing = [label for label in ("normal", "suspicious", "faulty") if not counts[label]]
    if missing:
        print(f"WARNING: No {', '.join(missing)} pseudo-label examples were collected. Do not train a supervised model until all required classes have evidence.")


if __name__ == "__main__":
    main()
