"""Generate reproducible, explicitly synthetic WinDrive raw-evidence training data.

The records are development fixtures, not observations from a Windows computer. Raw
driver/event/crash evidence is generated here; app.features.build_features remains
the only source of engineered ML features.
"""
import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.features.feature_engineer import FEATURES, build_feature_rows, validate_raw_evidence_records

GENERATOR_VERSION = "1.0"
REFERENCE_TIME = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
PROVIDERS = ("Aster Systems", "Northwind Devices", "Contoso Components", "Fabrikam Hardware", "Blue Oak Computing")
CATEGORIES = ("Net", "Display", "USB", "SCSIAdapter", "HIDClass", "MEDIA")
SOURCES = ("Kernel-PnP", "DriverFrameworks-UserMode", "Disk", "Display", "USBXHCI", "NDIS")


def timestamp(days_ago, hour):
    return (REFERENCE_TIME - timedelta(days=days_ago, hours=hour)).isoformat().replace("+00:00", "Z")


def base_record(index, rng):
    """Neutral metadata is sampled independently of the intended class scenario."""
    filename = f"drv{index:04d}.sys"
    month = rng.randint(1, 12)
    return {
        "driver": {
            "driver_name": filename,
            "file_name": filename,
            "provider": rng.choice(PROVIDERS),
            "version": f"{rng.randint(1, 4)}.{rng.randint(0, 12)}.{rng.randint(100, 9999)}",
            "driver_date": f"{rng.randint(2021, 2026)}{month:02d}{rng.randint(1, 28):02d}",
            "driver_path": f"C:/SyntheticWinDrive/Drivers/{filename}",
            "device_name": f"Lab Device {rng.randint(1000, 9999)}",
            "device_category": rng.choice(CATEGORIES),
            # Signature/provider/category intentionally overlap across all labels.
            "signature_status": rng.choice(("Signed", "Signed", "Unknown/Unsigned")),
            "driver_start_status": rng.choice(("True", "True", "Unknown")),
            "device_status": rng.choice(("OK", "OK", "Unknown", "Degraded")),
            "device_error_code": 0,
        },
        "events": [],
        "crashes": [],
        "reference_time": REFERENCE_TIME.isoformat().replace("+00:00", "Z"),
    }


def make_event(filename, rng, severity, days_ago, message):
    return {
        "TimeCreated": timestamp(days_ago, rng.randint(0, 23)),
        "ProviderName": rng.choice(SOURCES),
        "Id": rng.randint(1000, 9999),
        "LevelDisplayName": severity,
        # The module name supports the same evidence association as a live scan.
        "Message": f"{filename}: {message}",
    }


def normal_evidence(record, rng):
    """Normal cases include none or isolated non-failure diagnostic noise."""
    filename = record["driver"]["driver_name"]
    pattern = rng.randrange(4)
    if pattern == 0:
        return
    if pattern == 1:
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(8, 28), "configuration change was applied"))
    elif pattern == 2:
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(10, 29), "capability negotiation completed"))
    else:
        # One older, recoverable warning is deliberately not repeated failure evidence.
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(15, 29), "temporary resource condition resolved"))


def suspicious_evidence(record, rng):
    """Concerning but non-conclusive patterns, varied by combination rather than one cutoff."""
    filename = record["driver"]["driver_name"]
    pattern = rng.randrange(5)
    if pattern == 0:
        for day in rng.sample(range(1, 21), 2):
            record["events"].append(make_event(filename, rng, "Warning", day, "intermittent communication warning"))
    elif pattern == 1:
        record["events"].append(make_event(filename, rng, "Error", rng.randint(2, 18), "recoverable request error"))
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(1, 15), "operation continued after retry"))
    elif pattern == 2:
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(1, 12), "operation timeout recovered"))
    elif pattern == 3:
        record["events"].append(make_event(filename, rng, "Warning", rng.randint(1, 15), "device reset completed"))
        record["driver"]["device_error_code"] = rng.choice((10, 22, 28))
        record["driver"]["device_status"] = rng.choice(("Degraded", "Error", "Unknown"))
    else:
        for day in rng.sample(range(1, 10), 3):
            record["events"].append(make_event(filename, rng, "Warning", day, "intermittent driver warning"))


def faulty_evidence(record, rng):
    """Corroborated failure patterns; no single universal feature defines the class."""
    filename = record["driver"]["driver_name"]
    pattern = rng.randrange(5)
    if pattern == 0:
        record["events"] = [
            make_event(filename, rng, "Error", 1, "driver start failed"),
            make_event(filename, rng, "Error", 2, "initialization failed after retry"),
            make_event(filename, rng, "Warning", 3, "device reset requested"),
        ]
    elif pattern == 1:
        record["events"] = [make_event(filename, rng, "Error", day, "unrecoverable request failure") for day in (1, 4, 9)]
        record["crashes"].append({"timestamp": timestamp(1, 2), "module_names": [filename], "message": f"Synthetic BugCheck module reference: {filename}"})
    elif pattern == 2:
        record["events"] = [
            make_event(filename, rng, "Critical", 1, "device controller failure"),
            make_event(filename, rng, "Error", 3, "driver operation failed"),
            make_event(filename, rng, "Warning", 4, "operation timeout"),
        ]
    elif pattern == 3:
        record["events"] = [make_event(filename, rng, "Warning", day, "operation timeout and device reset") for day in (1, 2, 4)]
        record["events"].append(make_event(filename, rng, "Error", 5, "request failed after reset"))
    else:
        record["events"] = [
            make_event(filename, rng, "Error", 2, "driver start failed"),
            make_event(filename, rng, "Critical", 3, "device failure detected"),
        ]
        record["driver"]["device_error_code"] = rng.choice((10, 22, 28, 43))
        record["driver"]["device_status"] = rng.choice(("Degraded", "Error"))


def generate_records(normal_count, suspicious_count, faulty_count, seed):
    rng = random.Random(seed)
    records, index = [], 1
    for label, count, constructor in (("normal", normal_count, normal_evidence), ("suspicious", suspicious_count, suspicious_evidence), ("faulty", faulty_count, faulty_evidence)):
        for _ in range(count):
            record = base_record(index, rng)
            constructor(record, rng)
            # This is the target label of a documented synthetic scenario, not a feature.
            record["classification"] = label
            records.append(record)
            index += 1
    rng.shuffle(records)
    return records


def parse_args():
    parser = argparse.ArgumentParser(description="Create reproducible synthetic WinDrive raw-evidence data.")
    parser.add_argument("--seed", type=int, default=20261003)
    parser.add_argument("--normal", type=int, default=100)
    parser.add_argument("--suspicious", type=int, default=100)
    parser.add_argument("--faulty", type=int, default=100)
    parser.add_argument("--output", default="data/training/synthetic_driver_data.json")
    parser.add_argument("--metadata", default="data/training/synthetic_driver_data.metadata.json")
    return parser.parse_args()


def main():
    args = parse_args()
    if min(args.normal, args.suspicious, args.faulty) < 1:
        raise ValueError("Each synthetic class count must be at least one.")
    records = generate_records(args.normal, args.suspicious, args.faulty, args.seed)
    validate_raw_evidence_records(records)
    # Explicitly exercise production feature generation; it must create only FEATURES.
    rows = build_feature_rows(records)
    if any(set(row) != set(FEATURES + ["classification"]) for row in rows):
        raise ValueError("Generated raw evidence did not produce the declared WinDrive feature schema.")
    output, metadata = Path(args.output), Path(args.metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(records, indent=2, allow_nan=False), encoding="utf-8")
    counts = Counter(record["classification"] for record in records)
    metadata.write_text(json.dumps({
        "generator_version": GENERATOR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "record_count": len(records),
        "class_distribution": dict(counts),
        "description": "Synthetic development/training evidence fixtures. Not real-world Windows observations or independently validated ground truth.",
        "raw_evidence_file": str(output),
    }, indent=2, allow_nan=False), encoding="utf-8")
    print(f"Synthetic raw evidence generated: {len(records)} records")
    print(f"Class distribution: {dict(counts)}")
    print("Validation and production feature-building: PASSED")
    print(f"Output: {output}")
    print(f"Metadata: {metadata}")


if __name__ == "__main__":
    main()
