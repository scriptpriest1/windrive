import os, joblib, pandas as pd
from config import Config
from app.features.feature_engineer import FEATURES

def predict(features):
    if not os.path.exists(Config.MODEL_PATH): raise FileNotFoundError("No trained model found. Run scripts/train_model.py with a labelled dataset first.")
    bundle=joblib.load(Config.MODEL_PATH); frame=pd.DataFrame([{k:features.get(k) for k in FEATURES}]); probabilities=bundle["pipeline"].predict_proba(frame)[0]; index=probabilities.argmax()
    return bundle["classes"][index].upper(), float(probabilities[index])
