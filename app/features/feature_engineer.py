"""Auditable driver-level feature generation shared by dataset preparation and live scans."""
import re
from datetime import datetime, timedelta, timezone

NUMERIC_FEATURES = ["error_count", "warning_count", "critical_event_count", "driver_start_failure_count", "timeout_count", "device_reset_count", "crash_reference_count", "driver_age_days", "days_since_last_update", "recently_updated", "device_error_present", "affected_device_count", "error_count_7_days", "warning_count_7_days", "critical_count_7_days", "timeout_count_7_days", "reset_count_7_days", "crash_count_30_days", "error_count_30_days", "recent_failure_trend"]
CATEGORICAL_FEATURES = ["signature_status", "device_status", "last_error_severity", "driver_running_status", "device_category"]
FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def parse_timestamp(value):
    """Return an aware timestamp for PowerShell, Python, and ISO date values; otherwise None."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    text = str(value).strip()
    match = re.match(r"/Date\((\d+)", text)  # PowerShell JSON DateTime format
    if match:
        return datetime.fromtimestamp(int(match.group(1)) / 1000, tz=timezone.utc)
    dmtf = re.match(r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})", text)
    if dmtf:  # CIM/WMI DMTF date: YYYYMMDDhhmmss.ffffff±UUU
        return datetime(*map(int, dmtf.groups()), tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
    except ValueError:
        return None


def _text(record):
    return " ".join(str(record.get(key) or "") for key in ("Message", "description", "message", "related_device", "RelatedDevice")).lower()


def _driver_tokens(driver):
    values = (driver.get("driver_name"), driver.get("file_name"), driver.get("driver_path"))
    tokens = set()
    for value in values:
        if value:
            tokens.add(str(value).replace("\\", "/").rsplit("/", 1)[-1].lower())
    return {token for token in tokens if token and token not in {"unknown", "none"}}


def _matches_driver(record, tokens):
    record_tokens = {str(x).lower() for x in (record.get("module_names") or record.get("modules") or [])}
    haystack = _text(record)
    return any(token in record_tokens or token in haystack for token in tokens)


def _count_keyword(records, keyword):
    return sum(_text(record).count(keyword) for record in records)


def build_features(driver, events, crashes, reference_time=None):
    """Create FEATURES from raw evidence only; no feature has a synthetic stand-in value.

    `events` need TimeCreated/event_time plus severity/message fields. `crashes` need a
    timestamp and module_names when dump or BugCheck metadata identifies a module.
    """
    now = parse_timestamp(reference_time) or datetime.now(timezone.utc)
    seven_days_ago, thirty_days_ago = now - timedelta(days=7), now - timedelta(days=30)
    tokens = _driver_tokens(driver)
    matched_events = [event for event in events if tokens and _matches_driver(event, tokens)]
    event_30 = [event for event in matched_events if (stamp := parse_timestamp(event.get("TimeCreated") or event.get("event_time"))) and thirty_days_ago <= stamp <= now]
    event_7 = [event for event in event_30 if parse_timestamp(event.get("TimeCreated") or event.get("event_time")) >= seven_days_ago]
    matched_crashes = [crash for crash in crashes if tokens and _matches_driver(crash, tokens)]
    crash_30 = [crash for crash in matched_crashes if (stamp := parse_timestamp(crash.get("timestamp") or crash.get("TimeCreated"))) and thirty_days_ago <= stamp <= now]

    def severity_count(records, severity):
        return sum((record.get("LevelDisplayName") or record.get("severity") or "").lower() == severity for record in records)

    driver_date = parse_timestamp(driver.get("driver_date"))
    age_days = max(0, (now - driver_date).days) if driver_date and driver_date <= now else None
    device_name = (driver.get("device_name") or "").lower()
    related_devices = {str(event.get("related_device") or event.get("RelatedDevice") or "").strip().lower() for event in matched_events}
    related_devices.discard("")
    if device_name:
        related_devices.add(device_name)

    errors, warnings, critical = (severity_count(event_30, label) for label in ("error", "warning", "critical"))
    errors_7, warnings_7, critical_7 = (severity_count(event_7, label) for label in ("error", "warning", "critical"))
    start_failures = sum("start" in _text(event) and ("fail" in _text(event) or "unable" in _text(event)) for event in event_30)
    return {
        "error_count": errors, "warning_count": warnings, "critical_event_count": critical,
        "driver_start_failure_count": start_failures, "timeout_count": _count_keyword(event_30, "timeout"),
        "device_reset_count": _count_keyword(event_30, "reset"), "crash_reference_count": len(matched_crashes),
        # Win32_PnPSignedDriver.DriverDate is the driver/package date, not the
        # installation or last-update date. Preserve that distinction for ML.
        "driver_age_days": age_days, "days_since_last_update": None,
        "recently_updated": None,
        "device_error_present": int(str(driver.get("device_error_code") or "0") not in {"0", "", "None", "null"}),
        "affected_device_count": len(related_devices), "error_count_7_days": errors_7,
        "warning_count_7_days": warnings_7, "critical_count_7_days": critical_7,
        "timeout_count_7_days": _count_keyword(event_7, "timeout"), "reset_count_7_days": _count_keyword(event_7, "reset"),
        "crash_count_30_days": len(crash_30), "error_count_30_days": errors,
        "recent_failure_trend": int((errors_7 + critical_7) > 0 and (errors_7 + critical_7) >= (errors + critical) / 2),
        "signature_status": driver.get("signature_status") or "Unknown", "device_status": driver.get("device_status") or "Unknown",
        "last_error_severity": "Critical" if critical else ("Error" if errors else ("Warning" if warnings else "None")),
        "driver_running_status": driver.get("driver_start_status") or "Unknown", "device_category": driver.get("device_category") or "Unknown",
    }


def build_feature_rows(records):
    """Dataset-preparation entry point using the exact live build_features implementation."""
    return [{**build_features(record["driver"], record.get("events", []), record.get("crashes", []), record.get("reference_time")), "classification": record["classification"]} for record in records]
