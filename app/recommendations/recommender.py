def recommend(label):
    if label == "FAULTY": return "Review the official manufacturer driver package; consider rollback or reinstalling only after verification. Run hardware diagnostics and examine crash dumps with WinDbg if failures persist."
    if label == "SUSPICIOUS": return "Monitor this driver, review Event Viewer, check for an official manufacturer package, and inspect the associated hardware."
    return "No driver change is recommended: no significant instability evidence was detected."
