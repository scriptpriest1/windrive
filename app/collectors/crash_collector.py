from pathlib import Path
def collect_crashes():
    path=Path(r"C:\Windows\Minidump")
    try:
        return [{"name": p.name, "timestamp": p.stat().st_mtime} for p in path.glob("*.dmp")], None
    except Exception as exc: return [], f"Crash dump evidence unavailable: {exc}"
