"""Read relevant Windows System events without depending on Get-WinEvent formatting."""
import re
import subprocess
import xml.etree.ElementTree as ET


WINDOW_DAYS_MS = 30 * 24 * 60 * 60 * 1000
EVENT_QUERY = f"*[System[TimeCreated[timediff(@SystemTime) <= {WINDOW_DAYS_MS}] and (Level=1 or Level=2 or Level=3)]]"
RELEVANT_PROVIDER = re.compile(r"Kernel|Driver|Disk|Display|Network|USB|PnP|stor", re.IGNORECASE)
LEVEL_NAMES = {1: "Critical", 2: "Error", 3: "Warning"}
NAMESPACE = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}


def _run(command, timeout=90):
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def _event_log_available():
    """Check Event Log service and make a minimal read before collecting evidence."""
    service = _run(["sc.exe", "query", "eventlog"], timeout=15)
    if service.returncode != 0 or "RUNNING" not in service.stdout.upper():
        return False, "Windows Event Log service is unavailable or not running."
    probe = _run(["wevtutil", "qe", "System", "/c:1", "/rd:true", "/f:xml"], timeout=30)
    if probe.returncode != 0:
        detail = (probe.stderr or probe.stdout).strip()
        return False, f"Windows System log cannot be read: {detail or 'wevtutil query failed.'}"
    return True, None


def _parse_rendered_events(output):
    """Parse only actual RenderedXml event documents returned by wevtutil."""
    events = []
    for document in re.findall(r"<Event\b[\s\S]*?</Event>", output):
        try:
            root = ET.fromstring(document)
        except ET.ParseError:
            continue
        provider = root.find("e:System/e:Provider", NAMESPACE)
        provider_name = provider.get("Name") if provider is not None else ""
        if not RELEVANT_PROVIDER.search(provider_name or ""):
            continue
        event_id = root.findtext("e:System/e:EventID", default="", namespaces=NAMESPACE)
        level = root.findtext("e:System/e:Level", default="", namespaces=NAMESPACE)
        timestamp = root.find("e:System/e:TimeCreated", NAMESPACE)
        message = root.findtext("e:RenderingInfo/e:Message", default="", namespaces=NAMESPACE)
        try:
            level_value = int(level)
        except (TypeError, ValueError):
            level_value = 0
        try:
            event_id_value = int(event_id)
        except (TypeError, ValueError):
            event_id_value = None
        events.append({
            "TimeCreated": timestamp.get("SystemTime") if timestamp is not None else None,
            "ProviderName": provider_name,
            "Id": event_id_value,
            "LevelDisplayName": root.findtext("e:RenderingInfo/e:Level", default=LEVEL_NAMES.get(level_value, "Unknown"), namespaces=NAMESPACE),
            # An empty value means this Windows event has no renderable message; no text is invented.
            "Message": message or "",
        })
    return events


def collect_events():
    """Return (events, None), including when no relevant events match, or an access error."""
    try:
        available, error = _event_log_available()
        if not available:
            return [], error
        result = _run(["wevtutil", "qe", "System", f"/q:{EVENT_QUERY}", "/c:1000", "/rd:true", "/f:RenderedXml"])
        if result.returncode != 0:
            detail = (result.stderr or result.stdout).strip()
            return [], f"Windows Event Log is available, but relevant System events could not be read: {detail or 'wevtutil query failed.'}"
        return _parse_rendered_events(result.stdout), None
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"Windows Event Log unavailable: {exc}"
