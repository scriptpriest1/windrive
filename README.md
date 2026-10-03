# WinDrive

WinDrive is a local, read-only Windows device-driver diagnostic application. It gathers installed-driver metadata, relevant System Event Log records, and available minidump metadata, then sends engineered evidence through a trained supervised ML pipeline to classify drivers as **NORMAL**, **SUSPICIOUS**, or **FAULTY**.

Predictions are probability-based diagnostic aids, not proof of root cause. WinDrive never changes drivers or Windows configuration.

## Setup

1. Start MySQL in XAMPP and create the database: `CREATE DATABASE windrive CHARACTER SET utf8mb4;`
2. Create and activate a Python 3.10+ virtual environment, then run `pip install -r requirements.txt`.
3. Set `WINDRIVE_DATABASE_URL` if your MySQL credentials differ from `mysql+pymysql://root:@localhost/windrive`.
4. Generate the controlled labelled development dataset: `python scripts/create_test_dataset.py`.
5. Train the model: `python scripts/train_model.py data/training/labelled_driver_data.json`.
6. Run `python run.py` and open `http://127.0.0.1:5000`.

The app creates its MySQL tables on first launch. Running as Administrator can make additional Windows Event Log/crash metadata accessible, but a scan continues using accessible sources when data is unavailable.

## Dataset and Training Methodology

The report does not name a public dataset. This project uses a controlled synthetic evidence dataset constructed to represent Windows driver diagnostic scenarios. The dataset is used as the labelled development/training dataset for the prototype. It contains 89 explicitly marked synthetic records: **43 NORMAL**, **27 SUSPICIOUS**, and **19 FAULTY**. These counts are intentionally imbalanced and must not be treated as independent real-world prevalence.

Run `python scripts/create_test_dataset.py` to generate the raw fixture evidence and the sole labelled training file, `data/training/labelled_driver_data.json`. The generator uses deterministic evidence rules only and never reads model files, `Prediction` rows, or ML output. Its labels are controlled pseudo-labels, not independently collected real-world ground truth. The 113 collected Windows observations remain unlabelled diagnostic evidence and are not mixed into this labelled training dataset.

Driver age, package date, version, and signature status are not used to label fixtures. The raw JSON is processed by the same `build_feature_rows()` / `build_features()` logic used for live prediction. Controlled-fixture metrics demonstrate pipeline behavior only; they are not real-world model validation.
