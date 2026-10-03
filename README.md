# WinDrive

WinDrive is a local, read-only Windows diagnostic aid for identifying device drivers that may require investigation. It combines available driver/device metadata, relevant System Event Log records, and crash/BugCheck metadata, then applies a saved supervised machine-learning pipeline to classify each driver as **NORMAL**, **SUSPICIOUS**, or **FAULTY**. A prediction is a probability-based indication, not proof of root cause.

## Safety and scope

WinDrive never updates, installs, disables, removes, rolls back, or otherwise changes Windows drivers or configuration. It is intended for Windows laptops and desktops. Use the results alongside Event Viewer, official manufacturer driver packages, hardware diagnostics, restore points, WinDbg, or professional support as appropriate.

## Architecture

`Windows collectors → evidence association → build_features() → saved preprocessing/model → classification + confidence → evidence explanation + recommendation → MySQL scan history and CSV report`

Unmatched System events are retained as scan-level evidence instead of being assigned to a driver without support. Missing evidence is reported as unavailable; it is not interpreted as proof of health.

## Setup and run

1. Start MySQL in XAMPP and create `windrive`:

   `CREATE DATABASE windrive CHARACTER SET utf8mb4;`

2. Install dependencies:

   `venv\Scripts\pip.exe install -r requirements.txt`

3. Set `WINDRIVE_DATABASE_URL` if your local MySQL credentials differ from `mysql+pymysql://root:@localhost/windrive`.
4. Start the local application:

   `venv\Scripts\python.exe run.py`

5. Open `http://127.0.0.1:5000`.

Administrator access can provide richer driver and crash metadata. When CIM access is unavailable, WinDrive uses a read-only PnPUtil inventory fallback and clearly records the limitation.

## Models and datasets

The normal application model is configured by `WINDRIVE_MODEL_PATH` / `Config.MODEL_PATH` and currently loads [driver_classifier.joblib](artifacts/models/driver_classifier.joblib). It retains the full declared feature schema. `days_since_last_update` and `recently_updated` remain unavailable unless a genuine install/update timestamp is collected; the saved preprocessor safely omits entirely unobserved numeric columns without inventing values.

Synthetic development data is explicitly not real-world ground truth or real-world validation:

- [synthetic_driver_data.json](data/training/synthetic_driver_data.json) contains 300 reproducible synthetic raw-evidence records (100 per class), generated with seed `20261003`.
- [synthetic_driver_classifier.joblib](artifacts/models/synthetic_driver_classifier.joblib) is a separate development artifact.
- [labelled_driver_data.json](data/training/labelled_driver_data.json) is the project’s controlled prototype training dataset. It also remains synthetic/controlled and must not be described as independently validated Windows data.

Generate the broader synthetic dataset:

`venv\Scripts\python.exe scripts\create_synthetic_driver_dataset.py`

Train it without changing the normal application model:

`venv\Scripts\python.exe scripts\train_model.py data\training\synthetic_driver_data.json --output artifacts\models\synthetic_driver_classifier.joblib`

Train a selected labelled raw-evidence file into the configured production location only when intentionally approved:

`venv\Scripts\python.exe scripts\train_model.py data\training\labelled_driver_data.json`

Both JSON workflows use the same raw schema: `driver`, `events`, `crashes`, optional `reference_time`, and `classification`. Training validates raw records, duplicate records, labels, class coverage, feature schema, and preprocessing compatibility. Live scan predictions never become training labels automatically.

## Reports and tests

Completed scans can be exported from the dashboard as UTF-8 CSV or PDF. Both include scan metadata, model version where available, individual findings, evidence, recommendations, and a diagnostic disclaimer.

Run the automated checks:

`venv\Scripts\python.exe -m unittest discover -s tests -v`

## Limitations

The project report does not specify a named public real-world labelled dataset. Current synthetic-model metrics only demonstrate the prototype pipeline on controlled synthetic scenarios; they do not validate real-world driver-fault detection performance. Windows permissions, Event Log availability, driver metadata availability, and crash-dump availability vary by host.
