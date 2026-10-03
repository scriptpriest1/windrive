"""Train WinDrive's supervised model from reviewed research data, never live predictions.

Primary input is raw-evidence JSON: each manually reviewed record contains driver,
events, crashes, optional reference_time, and one ground-truth classification. CSV is
retained only for already-engineered, reviewed datasets.
"""
import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.features.feature_engineer import (
    CATEGORICAL_FEATURES, FEATURES, NUMERIC_FEATURES, VALID_CLASSIFICATIONS,
    build_feature_rows,
)


def load_dataset(dataset_path):
    if dataset_path.lower().endswith(".json"):
        try:
            with open(dataset_path, encoding="utf-8") as source:
                records = json.load(source)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Raw evidence JSON is invalid: {exc}") from exc
        return pd.DataFrame(build_feature_rows(records))
    try:
        return pd.read_csv(dataset_path)
    except (OSError, pd.errors.ParserError) as exc:
        raise ValueError(f"Could not read engineered CSV dataset: {exc}") from exc


def validate_engineered_dataset(frame):
    if frame.empty:
        raise ValueError("Dataset contains no training records.")
    missing = sorted(set(FEATURES + ["classification"]) - set(frame.columns))
    if missing:
        raise ValueError(f"Dataset is missing required feature/classification fields: {missing}")
    if frame.duplicated().any():
        raise ValueError(f"Dataset contains {int(frame.duplicated().sum())} duplicate record(s); remove or review them before training.")
    if frame["classification"].isna().any():
        raise ValueError("Dataset has records with missing reviewed classification.")
    labels = frame["classification"].astype(str).str.strip().str.lower()
    invalid = sorted(set(labels) - VALID_CLASSIFICATIONS)
    if invalid:
        raise ValueError(f"Invalid classifications: {invalid}. Expected only normal, suspicious, faulty.")
    counts = labels.value_counts()
    missing_classes = sorted(VALID_CLASSIFICATIONS - set(counts.index))
    if missing_classes:
        raise ValueError(f"Stratified training requires all three reviewed classes; missing: {missing_classes}.")
    too_small = counts[counts < 2]
    if not too_small.empty:
        raise ValueError(f"Each class needs at least two reviewed records for stratification; insufficient: {too_small.to_dict()}.")
    test_size = math.ceil(len(frame) * 0.2)
    if test_size < len(VALID_CLASSIFICATIONS) or len(frame) - test_size < len(VALID_CLASSIFICATIONS):
        raise ValueError("Dataset is too small for a reliable stratified train/test split containing normal, suspicious, and faulty. Add reviewed records to every class.")
    return frame.assign(classification=labels), counts.to_dict()


def main():
    parser = argparse.ArgumentParser(description="Train WinDrive from reviewed raw evidence JSON or reviewed engineered CSV.")
    parser.add_argument("dataset", help="Raw evidence .json (primary) or reviewed engineered .csv")
    parser.add_argument("--output", default="artifacts/models/driver_classifier.joblib")
    args = parser.parse_args()

    dataset, class_distribution = validate_engineered_dataset(load_dataset(args.dataset))
    features, labels = dataset[FEATURES], dataset["classification"]
    x_train, x_test, y_train, y_test = train_test_split(features, labels, test_size=0.2, random_state=42, stratify=labels)
    preprocessing = ColumnTransformer([
        ("number", Pipeline([("impute", SimpleImputer(strategy="median"))]), NUMERIC_FEATURES),
        ("category", Pipeline([("impute", SimpleImputer(strategy="most_frequent")), ("encode", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL_FEATURES),
    ])
    pipeline = Pipeline([("preprocessing", preprocessing), ("model", RandomForestClassifier(n_estimators=300, random_state=42, class_weight="balanced"))])
    started = time.time()
    pipeline.fit(x_train, y_train)
    predicted = pipeline.predict(x_test)
    processing_time = time.time() - started
    ordered_classes = ["normal", "suspicious", "faulty"]
    metrics = {
        "accuracy": accuracy_score(y_test, predicted),
        "classification_report": classification_report(y_test, predicted, labels=ordered_classes, target_names=ordered_classes, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, predicted, labels=ordered_classes).tolist(),
        "test_set_size": len(x_test),
        "training_set_size": len(x_train),
        "class_distribution": class_distribution,
        "training_processing_time_seconds": processing_time,
    }
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    joblib.dump({"pipeline": pipeline, "classes": list(pipeline.classes_), "feature_schema": FEATURES, "model_version": "1.0", "metrics": metrics}, args.output)
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
