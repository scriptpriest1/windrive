from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class ScanSession(db.Model):
    __tablename__ = "scan_sessions"
    id = db.Column(db.Integer, primary_key=True)
    computer_name = db.Column(db.String(255), nullable=False)
    operating_system = db.Column(db.String(500), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    status = db.Column(db.String(30), default="pending", index=True, nullable=False)
    driver_count = db.Column(db.Integer, default=0)
    event_count = db.Column(db.Integer, default=0)
    crash_count = db.Column(db.Integer, default=0)
    processing_time = db.Column(db.Float)
    progress = db.Column(db.Integer, default=0)
    current_stage = db.Column(db.String(255), default="Pending")
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    drivers = db.relationship("Driver", backref="scan", lazy=True, cascade="all, delete-orphan")


class Driver(db.Model):
    __tablename__ = "drivers"
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scan_sessions.id"), nullable=False, index=True)
    driver_name = db.Column(db.String(255), nullable=False, index=True)
    file_name = db.Column(db.String(255))
    provider = db.Column(db.String(255))
    version = db.Column(db.String(255))
    driver_date = db.Column(db.String(100))
    driver_path = db.Column(db.Text)
    device_name = db.Column(db.String(500))
    device_category = db.Column(db.String(255))
    signature_status = db.Column(db.String(100))
    driver_start_status = db.Column(db.String(100))
    device_status = db.Column(db.String(100))
    device_error_code = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    events = db.relationship("Event", backref="driver", lazy=True)
    prediction = db.relationship("Prediction", backref="driver", uselist=False, lazy=True)


class Event(db.Model):
    __tablename__ = "events"
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scan_sessions.id"), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), index=True)
    event_time = db.Column(db.DateTime, index=True)
    event_source = db.Column(db.String(255))
    event_code = db.Column(db.Integer)
    severity = db.Column(db.String(50))
    description = db.Column(db.Text)
    related_device = db.Column(db.String(500))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Prediction(db.Model):
    __tablename__ = "predictions"
    id = db.Column(db.Integer, primary_key=True)
    scan_id = db.Column(db.Integer, db.ForeignKey("scan_sessions.id"), nullable=False, index=True)
    driver_id = db.Column(db.Integer, db.ForeignKey("drivers.id"), nullable=False, index=True)
    classification = db.Column(db.String(30), nullable=False, index=True)
    confidence = db.Column(db.Numeric(5, 4), nullable=False)
    main_evidence = db.Column(db.Text)
    recommendation = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
