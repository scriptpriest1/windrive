import json, subprocess

SCRIPT = "Get-WinEvent -FilterHashtable @{LogName='System'; StartTime=(Get-Date).AddDays(-30)} -ErrorAction Stop | Where-Object {$_.Level -in 1,2,3 -and $_.ProviderName -match 'Kernel|Driver|Disk|Display|Network|USB|PnP|stor'} | Select-Object -First 1000 TimeCreated,ProviderName,Id,LevelDisplayName,Message | ConvertTo-Json -Depth 2"
def collect_events():
    try:
        r = subprocess.run(["powershell","-NoProfile","-Command",SCRIPT], capture_output=True, text=True, timeout=90)
        if r.returncode != 0: raise RuntimeError(r.stderr.strip())
        rows=json.loads(r.stdout or "[]"); return (rows if isinstance(rows,list) else [rows]), None
    except Exception as exc: return [], f"Event Log evidence unavailable: {exc}"
