"""Production-model loading and inference for WinDrive scans."""
import os
from functools import lru_cache

import joblib
import pandas as pd

from config import Config
from app.features.feature_engineer import FEATURES


@lru_cache(maxsize=2)
def _load_model(path, modified_time):
    bundle = joblib.load(path)
    return validate_model_bundle(bundle)


def validate_model_bundle(bundle):
    if bundle.get("feature_schema") != FEATURES:
        raise ValueError("The trained model feature schema is incompatible with this WinDrive version. Retrain the model with the current pipeline.")
    if "pipeline" not in bundle or not hasattr(bundle["pipeline"], "predict_proba"):
        raise ValueError("The trained model does not provide the required probability prediction pipeline.")
    return bundle


def load_production_model():
    """Load and validate the configured production model, reloading after file updates."""
    path = Config.MODEL_PATH
    if not os.path.isfile(path):
        raise FileNotFoundError("No trained production model found. Run scripts/train_model.py with a labelled dataset first.")
    return _load_model(path, os.path.getmtime(path))


def predict(features, model_bundle=None):
    """Predict from a complete declared feature vector using the saved preprocessing pipeline."""
    bundle = validate_model_bundle(model_bundle) if model_bundle is not None else load_production_model()
    missing = [name for name in FEATURES if name not in features]
    if missing:
        raise ValueError(f"Feature engineering did not provide required model fields: {missing}")
    frame = pd.DataFrame([{name: features[name] for name in FEATURES}])
    probabilities = bundle["pipeline"].predict_proba(frame)[0]
    class_names = list(bundle["pipeline"].classes_)
    index = int(probabilities.argmax())
    return class_names[index].upper(), float(probabilities[index])
