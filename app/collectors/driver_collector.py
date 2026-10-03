"""Read-only Windows driver inventory collection with a PnPUtil fallback."""
import json
import subprocess

SCRIPT = "Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceName,DeviceClass,DriverName,InfName,DriverProviderName,DriverVersion,DriverDate,DriverPath,IsSigned,Started,Status,DeviceID | ConvertTo-Json -Depth 3"


def _normalise_cim(rows):
    if isinstance(rows, dict):
        rows = [rows]
    return [{
        "driver_name": row.get("DriverName") or row.get("InfName") or "Unknown",
        "file_name": row.get("DriverName") or row.get("InfName"),
        "provider": row.get("DriverProviderName"), "version": row.get("DriverVersion"),
        "driver_date": row.get("DriverDate"), "driver_path": row.get("DriverPath"),
        "device_name": row.get("DeviceName"), "device_category": row.get("DeviceClass"),
        "signature_status": "Signed" if row.get("IsSigned") else "Unknown/Unsigned",
        "driver_start_status": str(row.get("Started") if row.get("Started") is not None else "Unknown"),
        "device_status": row.get("Status") or "Unknown", "device_error_code": None,
    } for row in rows]


def _parse_pnputil(output):
    """Parse the documented /enum-drivers label/value blocks without inventing fields."""
    blocks, current = [], {}
    labels = {
        "Published Name": "published", "Original Name": "original", "Provider Name": "provider",
        "Class Name": "category", "Driver Version": "version_date", "Signer Name": "signer",
    }
    for line in output.splitlines():
        if not line.strip():
            if current:
                blocks.append(current); current = {}
            continue
        if ":" not in line:
            continue
        label, value = (part.strip() for part in line.split(":", 1))
        if label in labels:
            current[labels[label]] = value
    if current:
        blocks.append(current)
    rows = []
    for block in blocks:
        name = block.get("original") or block.get("published")
        if not name:
            continue
        version_date = block.get("version_date", "")
        date, _, version = version_date.partition(" ")
        rows.append({
            "driver_name": name, "file_name": name, "provider": block.get("provider"),
            "version": version or None, "driver_date": date or None, "driver_path": None,
            "device_name": None, "device_category": block.get("category"),
            "signature_status": "Signed" if block.get("signer") else "Unknown",
            "driver_start_status": "Unknown", "device_status": "Unknown", "device_error_code": None,
        })
    return rows


def collect_drivers():
    """Return (rows, None) on success, using available read-only Windows sources."""
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", SCRIPT], capture_output=True, text=True, timeout=90)
        if result.returncode == 0:
            return _normalise_cim(json.loads(result.stdout or "[]")), None
        cim_error = result.stderr.strip() or "Win32_PnPSignedDriver query failed."
    except Exception as exc:
        cim_error = str(exc)
    try:
        fallback = subprocess.run(["pnputil", "/enum-drivers"], capture_output=True, text=True, timeout=90)
        rows = _parse_pnputil(fallback.stdout) if fallback.returncode == 0 else []
        if rows:
            return rows, f"Detailed CIM driver/device fields were unavailable; using PnPUtil inventory. {cim_error}"
        detail = (fallback.stderr or fallback.stdout).strip()
        return [], f"Driver inventory unavailable. CIM: {cim_error} PnPUtil: {detail or 'no driver records returned.'}"
    except Exception as exc:
        return [], f"Driver inventory unavailable. CIM: {cim_error} PnPUtil: {exc}"
