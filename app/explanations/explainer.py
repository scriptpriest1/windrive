def explain(features):
    evidence=[]
    for field,label in [("critical_event_count","critical driver-related events"),("error_count","driver-related errors"),("warning_count","driver-related warnings"),("timeout_count","timeout events"),("device_reset_count","device reset events"),("crash_reference_count","crash-dump references")]:
        if features.get(field,0): evidence.append(f"{features[field]} {label} recorded")
    if features.get("device_error_present"): evidence.append("Windows reported a device error code")
    return "; ".join(evidence) if evidence else "No significant driver-related instability evidence was collected."
