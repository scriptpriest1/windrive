"""Read-only minidump and BugCheck metadata collection."""
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

WINDOW_DAYS_MS = 30 * 24 * 60 * 60 * 1000
BUGCHECK_QUERY = f"*[System[(EventID=1001) and TimeCreated[timediff(@SystemTime) <= {WINDOW_DAYS_MS}]]]"
NAMESPACE = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}


def _bugcheck_events():
    result = subprocess.run(["wevtutil", "qe", "System", f"/q:{BUGCHECK_QUERY}", "/c:100", "/rd:true", "/f:RenderedXml"], capture_output=True, text=True, timeout=45)
    if result.returncode != 0:
        return [], (result.stderr or result.stdout).strip()
    records = []
    for document in re.findall(r"<Event\b[\s\S]*?</Event>", result.stdout):
        try:
            root = ET.fromstring(document)
        except ET.ParseError:
            continue
        provider = root.find("e:System/e:Provider", NAMESPACE)
        provider_name = provider.get("Name") if provider is not None else ""
        if not re.search(r"BugCheck|WER-SystemErrorReporting", provider_name, re.I):
            continue
        timestamp = root.find("e:System/e:TimeCreated", NAMESPACE)
        message = root.findtext("e:RenderingInfo/e:Message", default="", namespaces=NAMESPACE)
        records.append({"name": "BugCheck event", "timestamp": timestamp.get("SystemTime") if timestamp is not None else None, "module_names": re.findall(r"\b[\w.-]+\.sys\b", message, flags=re.I), "message": message or ""})
    return records, None


def collect_crashes():
    dumps, warnings = [], []
    try:
        path = Path(r"C:\Windows\Minidump")
        if path.exists():
            dumps = [{"name": item.name, "timestamp": item.stat().st_mtime, "module_names": []} for item in path.glob("*.dmp")]
    except OSError as exc:
        warnings.append(f"Minidump metadata unavailable: {exc}")
    try:
        bugchecks, error = _bugcheck_events()
        dumps.extend(bugchecks)
        if error:
            warnings.append(f"BugCheck metadata unavailable: {error}")
    except (OSError, subprocess.SubprocessError) as exc:
        warnings.append(f"BugCheck metadata unavailable: {exc}")
    return dumps, " | ".join(warnings) if warnings else None
