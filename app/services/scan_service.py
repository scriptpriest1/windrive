"""Background scan orchestration; all collection remains read-only."""
import json
import threading
import time
from datetime import datetime

from app.collectors.crash_collector import collect_crashes
from app.collectors.driver_collector import collect_drivers
from app.collectors.event_collector import collect_events
from app.database.models import db, Driver, Event, Prediction, ScanSession
from app.explanations.explainer import explain
from app.features.feature_engineer import build_features, parse_timestamp
from app.ml.predictor import load_production_model, predict
from app.recommendations.recommender import recommend
from app.services.system_service import system_info


def update(scan, progress, stage):
    scan.progress, scan.current_stage = progress, stage
    db.session.commit()


def _cancelled(scan):
    db.session.refresh(scan)
    return scan.status == "cancelled"


def start_scan(app):
    info = system_info()
    scan = ScanSession(computer_name=info["computer_name"], operating_system=info["operating_system"], status="pending")
    db.session.add(scan)
    db.session.commit()
    threading.Thread(target=_run, args=(app, scan.id), daemon=True, name=f"windrive-scan-{scan.id}").start()
    return scan


def _persist_events(scan, persisted_drivers, events):
    for row in events:
        message = row.get("Message") or ""
        linked = next((driver for driver in persisted_drivers if (driver.driver_name or "").lower() in message.lower()), None)
        db.session.add(Event(
            scan_id=scan.id, driver_id=linked.id if linked else None,
            event_time=parse_timestamp(row.get("TimeCreated")), event_source=row.get("ProviderName"),
            event_code=row.get("Id"), severity=row.get("LevelDisplayName"),
            description=message, related_device=None,
        ))


def _run(app, scan_id):
    with app.app_context():
        scan = db.session.get(ScanSession, scan_id)
        started = time.time()
        warnings = []
        try:
            scan.status = "running"
            update(scan, 5, "Checking permissions")
            if _cancelled(scan):
                return

            update(scan, 15, "Collecting installed device drivers")
            drivers, error = collect_drivers()
            if error:
                warnings.append(error)

            update(scan, 35, "Collecting relevant Windows Event Logs")
            events, error = collect_events()
            scan.event_count = len(events)
            if error:
                warnings.append(error)
            db.session.commit()
            if _cancelled(scan):
                return

            update(scan, 50, "Collecting crash and BugCheck metadata")
            crashes, error = collect_crashes()
            scan.crash_count = len(crashes)
            if error:
                warnings.append(error)
            db.session.commit()
            if _cancelled(scan):
                return

            update(scan, 62, "Saving collected evidence")
            persisted = []
            for row in drivers:
                item = Driver(scan_id=scan.id, **row)
                db.session.add(item)
                persisted.append(item)
            db.session.flush()
            scan.driver_count = len(persisted)
            _persist_events(scan, persisted, events)
            scan.crash_evidence = json.dumps(crashes)
            db.session.commit()
            if _cancelled(scan):
                return

            update(scan, 72, "Engineering features and loading model")
            model = load_production_model()
            for index, item in enumerate(persisted):
                if index % 20 == 0 and _cancelled(scan):
                    return
                row = {column.name: getattr(item, column.name) for column in item.__table__.columns}
                features = build_features(row, events, crashes)
                label, confidence = predict(features, model)
                db.session.add(Prediction(
                    scan_id=scan.id, driver_id=item.id, classification=label, confidence=confidence,
                    main_evidence=explain(features), recommendation=recommend(label),
                ))
                if index % 25 == 0:
                    db.session.commit()

            if _cancelled(scan):
                return
            update(scan, 93, "Saving predictions and recommendations")
            scan.status = "completed"
            scan.progress = 100
            scan.current_stage = "Complete"
            scan.completed_at = datetime.utcnow()
            scan.processing_time = round(time.time() - started, 2)
            scan.error_message = " | ".join(warnings) if warnings else None
            db.session.commit()
        except Exception as exc:
            db.session.rollback()
            scan = db.session.get(ScanSession, scan_id)
            if scan and scan.status != "cancelled":
                scan.status = "failed"
                scan.error_message = str(exc)
                scan.completed_at = datetime.utcnow()
                scan.processing_time = round(time.time() - started, 2)
                db.session.commit()
