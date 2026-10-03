from pathlib import Path
import json
import re
import subprocess


BUGCHECK_SCRIPT = "Get-WinEvent -FilterHashtable @{LogName='System'; Id=1001; StartTime=(Get-Date).AddDays(-30)} -ErrorAction SilentlyContinue | Where-Object {$_.ProviderName -match 'BugCheck|WER-SystemErrorReporting'} | Select-Object TimeCreated,ProviderName,Id,Message | ConvertTo-Json -Depth 2"


def collect_crashes():
    path=Path(r"C:\Windows\Minidump")
    try:
        dumps = [{"name": p.name, "timestamp": p.stat().st_mtime, "module_names": []} for p in path.glob("*.dmp")]
        result = subprocess.run(["powershell", "-NoProfile", "-Command", BUGCHECK_SCRIPT], capture_output=True, text=True, timeout=45)
        if result.returncode == 0 and result.stdout.strip():
            rows = json.loads(result.stdout)
            for row in (rows if isinstance(rows, list) else [rows]):
                message = row.get("Message") or ""
                dumps.append({"name": "BugCheck event", "timestamp": row.get("TimeCreated"), "module_names": re.findall(r"\b[\w.-]+\.sys\b", message, flags=re.I), "message": message})
        return dumps, None
    except Exception as exc: return [], f"Crash dump evidence unavailable: {exc}"
