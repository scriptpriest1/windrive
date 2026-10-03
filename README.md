# WinDrive

WinDrive is a local, read-only Windows device-driver diagnostic application. It gathers installed-driver metadata, relevant System Event Log records, and available minidump metadata, then sends engineered evidence through a trained supervised ML pipeline to classify drivers as **NORMAL**, **SUSPICIOUS**, or **FAULTY**.

Predictions are probability-based diagnostic aids, not proof of root cause. WinDrive never changes drivers or Windows configuration.

## Setup

1. Start MySQL in XAMPP and create the database: `CREATE DATABASE windrive CHARACTER SET utf8mb4;`
2. Create and activate a Python 3.10+ virtual environment, then run `pip install -r requirements.txt`.
3. Set `WINDRIVE_DATABASE_URL` if your MySQL credentials differ from `mysql+pymysql://root:@localhost/windrive`.
4. Train the model using a reviewed labelled dataset containing all fields in `app.features.feature_engineer.FEATURES` plus `classification`:
   `python scripts/train_model.py data/training/labelled_driver_data.csv`
5. Run `python run.py` and open `http://127.0.0.1:5000`.

The app creates its MySQL tables on first launch. Running as Administrator can make additional Windows Event Log/crash metadata accessible, but a scan continues using accessible sources when data is unavailable.
