import os


class Config:
    SECRET_KEY = os.getenv("WINDRIVE_SECRET_KEY", "windrive-local-development")
    SQLALCHEMY_DATABASE_URI = os.getenv("WINDRIVE_DATABASE_URL", "mysql+pymysql://root:@localhost/windrive")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MODEL_PATH = os.getenv("WINDRIVE_MODEL_PATH", os.path.join(os.path.dirname(__file__), "artifacts", "models", "driver_classifier.joblib"))
    DEBUG = os.getenv("WINDRIVE_DEBUG", "0") == "1"
