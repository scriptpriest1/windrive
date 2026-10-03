"""Create explicitly synthetic, controlled raw evidence fixtures for ML pipeline tests.

This development utility neither reads Windows drivers nor writes to MySQL. It creates
raw evidence only and delegates every classification to auto_label_record().
"""
import json
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.features.feature_engineer import validate_raw_evidence_records
from scripts.auto_label_dataset import auto_label_record

REFERENCE = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
CATEGORIES = ("Net", "Display", "USB", "SCSIAdapter", "HIDClass")


def iso(days_ago, hours=0):
    return (REFERENCE - timedelta(days=days_ago, hours=hours)).isoformat().replace("+00:00", "Z")


def base_record(number, device_error=0):
    filename = f"testdrv{number:03d}.sys"
    return {
        "dataset_source": "synthetic_controlled_fixture",
        "fixture_notice": "Synthetic controlled test fixture; not collected from a Windows machine.",
        "driver": {
            "driver_name": filename, "file_name": filename, "provider": "WinDrive Test Fixture Provider",
            "version": f"1.{number % 7}.{number}", "driver_date": f"2025{(number % 9) + 1:02d}15",
            "driver_path": f"C:/WinDriveFixtures/drivers/{filename}", "device_name": f"Synthetic Test Device {number:03d}",
            "device_category": CATEGORIES[number % len(CATEGORIES)], "signature_status": "Signed",
            "driver_start_status": "True", "device_status": "OK", "device_error_code": device_error,
        },
        "events": [], "crashes": [], "reference_time": REFERENCE.isoformat().replace("+00:00", "Z"),
    }


def event(filename, level, days_ago, message):
    return {"TimeCreated": iso(days_ago, days_ago % 5), "ProviderName": "WinDrive-Test-System", "Id": 7000 + days_ago, "LevelDisplayName": level, "Message": f"{filename}: {message}"}


def quiet_fixture(number):
    record = base_record(number)
    # A single harmless warning in some examples remains below the suspicious rule threshold.
    if number % 3 == 0:
        record["events"].append(event(record["driver"]["driver_name"], "Warning", 12, "informational configuration notice"))
    return record


def watch_fixture(number):
    record = base_record(number, device_error=10 if number % 5 == 0 else 0)
    filename = record["driver"]["driver_name"]
    pattern = number % 4
    if pattern == 0:
        record["events"] = [event(filename, "Warning", 2, "intermittent driver warning"), event(filename, "Warning", 6, "intermittent driver warning")]
    elif pattern == 1:
        record["events"] = [event(filename, "Error", 4, "recoverable device communication error")]
    elif pattern == 2:
        record["events"] = [event(filename, "Warning", 1, "operation timeout recovered")]
    else:
        record["events"] = [event(filename, "Warning", 3, "device reset completed")]
    return record


def failure_fixture(number):
    record = base_record(number)
    filename = record["driver"]["driver_name"]
    pattern = number % 4
    if pattern == 0:
        record["events"] = [event(filename, "Error", 1, "driver start failed"), event(filename, "Error", 2, "driver failed during initialization")]
    elif pattern == 1:
        record["events"] = [event(filename, "Error", 1, "unrecoverable I/O failure")]
        record["crashes"] = [{"timestamp": iso(1), "module_names": [filename], "message": f"Synthetic BugCheck references {filename}"}]
    elif pattern == 2:
        record["events"] = [event(filename, "Error", day, "repeated driver operation error") for day in (1, 3, 8)]
    else:
        record["events"] = [event(filename, "Warning", day, "operation timeout and device reset") for day in (1, 2, 4)]
    return record


def main():
    # Intentional controlled-dataset imbalance for the prototype's development training.
    raw = [quiet_fixture(number) for number in range(1, 44)]
    raw += [watch_fixture(number) for number in range(44, 71)]
    raw += [failure_fixture(number) for number in range(71, 90)]
    labelled = [auto_label_record(record) for record in raw]
    validate_raw_evidence_records(labelled)
    directory = PROJECT_ROOT / "data" / "training"
    directory.mkdir(parents=True, exist_ok=True)
    raw_path = directory / "controlled_raw_evidence.json"
    labelled_path = directory / "labelled_driver_data.json"
    raw_path.write_text(json.dumps(raw, indent=2), encoding="utf-8")
    labelled_path.write_text(json.dumps(labelled, indent=2), encoding="utf-8")
    counts = Counter(record["classification"] for record in labelled)
    print("Controlled fixture generation complete.")
    print(f"Raw records: {len(raw)}")
    print("Automatically labelled:")
    print(f"NORMAL: {counts['normal']}")
    print(f"SUSPICIOUS: {counts['suspicious']}")
    print(f"FAULTY: {counts['faulty']}")
    print("Validation: PASSED")
    print(f"Raw output: {raw_path.relative_to(PROJECT_ROOT)}")
    print(f"Labelled output: {labelled_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
