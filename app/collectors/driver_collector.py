import json, subprocess

SCRIPT = "Get-CimInstance Win32_PnPSignedDriver | Select-Object DeviceName,DeviceClass,DriverName,InfName,DriverProviderName,DriverVersion,DriverDate,DriverPath,IsSigned,Started,Status,DeviceID | ConvertTo-Json -Depth 3"

def collect_drivers():
    try:
        result = subprocess.run(["powershell", "-NoProfile", "-Command", SCRIPT], capture_output=True, text=True, timeout=90)
        if result.returncode != 0: raise RuntimeError(result.stderr.strip())
        rows = json.loads(result.stdout or "[]")
        if isinstance(rows, dict): rows = [rows]
        rows = [{"driver_name": r.get("DriverName") or r.get("InfName") or "Unknown", "file_name": r.get("DriverName"), "provider": r.get("DriverProviderName"), "version": r.get("DriverVersion"), "driver_date": r.get("DriverDate"), "driver_path": r.get("DriverPath"), "device_name": r.get("DeviceName"), "device_category": r.get("DeviceClass"), "signature_status": "Signed" if r.get("IsSigned") else "Unknown/Unsigned", "driver_start_status": str(r.get("Started") or "Unknown"), "device_status": r.get("Status") or "Unknown", "device_error_code": 0} for r in rows]
        return rows, None
    except Exception as exc:
        return [], f"Driver inventory unavailable: {exc}"
