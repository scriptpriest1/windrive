def recommend(label):
    if label == "FAULTY": return "Review the official hardware manufacturer driver package and associated Event Viewer records. Before any manual rollback or reinstall, create a restore point. Run hardware diagnostics and inspect crash dumps with WinDbg if failures persist."
    if label == "SUSPICIOUS": return "Monitor this driver, review the associated Event Viewer records, check the hardware manufacturer's driver page, and inspect the related hardware."
    return "No driver change is recommended: no significant instability evidence was detected."
