import platform, socket, ctypes
def system_info(): return {"computer_name":socket.gethostname(),"operating_system":platform.platform()}
def permission_info():
    try: admin=bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: admin=False
    return {"administrator":admin,"message":"Administrator access improves Event Log and crash-dump availability." if not admin else "Administrator access is available."}
