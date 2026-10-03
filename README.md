# WinDrive

WinDrive is a local, read-only Windows device-driver diagnostic application. It gathers installed-driver metadata, relevant System Event Log records, and available minidump metadata, then sends engineered evidence through a trained supervised ML pipeline to classify drivers as **NORMAL**, **SUSPICIOUS**, or **FAULTY**.

Predictions are probability-based diagnostic aids, not proof of root cause. WinDrive never changes drivers or Windows configuration.

## Setup

1. Start MySQL in XAMPP and create the database: `CREATE DATABASE windrive CHARACTER SET utf8mb4;`
2. Create and activate a Python 3.10+ virtual environment, then run `pip install -r requirements.txt`.
3. Set `WINDRIVE_DATABASE_URL` if your MySQL credentials differ from `mysql+pymysql://root:@localhost/windrive`.
4. Train the model using a reviewed labelled dataset. An engineered CSV must contain all fields in `app.features.feature_engineer.FEATURES` plus `classification`. Prefer a reviewed evidence JSON array whose records include `driver`, `events`, `crashes`, and `classification`; WinDrive will generate its features with the exact same function used during live scans:
   `python scripts/train_model.py data/training/labelled_driver_data.csv`
5. Run `python run.py` and open `http://127.0.0.1:5000`.

The app creates its MySQL tables on first launch. Running as Administrator can make additional Windows Event Log/crash metadata accessible, but a scan continues using accessible sources when data is unavailable.

## Dataset and Training Methodology

The project report does not specify a named public dataset. WinDrive's primary research format is therefore a raw-evidence JSON array collected from controlled Windows machines/VMs and relevant secondary sources. Each reviewed record preserves the driver inventory and Device Manager status, signatures and versions, relevant Event Viewer records, crash-dump metadata, BugCheck records, and available timestamps:

```json
[{"driver": {"driver_name": "example.sys", "device_status": "OK"}, "events": [], "crashes": [], "reference_time": "2026-10-03T10:00:00Z", "classification": "normal"}]
```

Controlled test cases can include stable drivers, outdated drivers, startup failures, repeated warnings, device resets, and verified crash scenarios. Each record is technically reviewed and assigned exactly one ground-truth label: `normal`, `suspicious`, or `faulty`. A driver being old, unsigned, or mentioned in a single event is not enough on its own to assign the `faulty` label; labels must consider multiple evidence sources and, where applicable, controlled test conditions.

The training command uses the same `build_features()` implementation as live scanning. It validates raw records and refuses duplicates, invalid labels, missing required evidence structures, missing classes, or datasets too small for a stratified split. An already-engineered, reviewed CSV remains supported. Live scan predictions never become training labels automatically.
