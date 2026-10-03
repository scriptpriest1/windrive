from datetime import datetime

NUMERIC_FEATURES=["error_count","warning_count","critical_event_count","driver_start_failure_count","timeout_count","device_reset_count","crash_reference_count","driver_age_days","days_since_last_update","recently_updated","device_error_present","affected_device_count","error_count_7_days","warning_count_7_days","critical_count_7_days","timeout_count_7_days","reset_count_7_days","crash_count_30_days","error_count_30_days","recent_failure_trend"]
CATEGORICAL_FEATURES=["signature_status","device_status","last_error_severity","driver_running_status","device_category"]
FEATURES=NUMERIC_FEATURES+CATEGORICAL_FEATURES

def build_features(driver, events, crashes):
    name=(driver.get("driver_name") or "").lower(); matched=[e for e in events if name and name in (e.get("Message") or "").lower()]
    severity=[(e.get("LevelDisplayName") or "").lower() for e in matched]
    errors=sum(x=="error" for x in severity); warnings=sum(x=="warning" for x in severity); critical=sum(x=="critical" for x in severity)
    text=" ".join(e.get("Message") or "" for e in matched).lower()
    return {"error_count":errors,"warning_count":warnings,"critical_event_count":critical,"driver_start_failure_count":int("start" in text and "fail" in text),"timeout_count":text.count("timeout"),"device_reset_count":text.count("reset"),"crash_reference_count":0,"driver_age_days":0,"days_since_last_update":0,"recently_updated":0,"device_error_present":int((driver.get("device_error_code") or 0)!=0),"affected_device_count":1 if matched else 0,"error_count_7_days":errors,"warning_count_7_days":warnings,"critical_count_7_days":critical,"timeout_count_7_days":text.count("timeout"),"reset_count_7_days":text.count("reset"),"crash_count_30_days":0,"error_count_30_days":errors,"recent_failure_trend":int(errors+critical>1),"signature_status":driver.get("signature_status") or "Unknown","device_status":driver.get("device_status") or "Unknown","last_error_severity":"Critical" if critical else ("Error" if errors else ("Warning" if warnings else "None")),"driver_running_status":driver.get("driver_start_status") or "Unknown","device_category":driver.get("device_category") or "Unknown"}
