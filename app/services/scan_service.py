import json, threading, time
from datetime import datetime
from app.database.models import db, ScanSession, Driver, Event, Prediction
from app.services.system_service import system_info
from app.collectors.driver_collector import collect_drivers
from app.collectors.event_collector import collect_events
from app.collectors.crash_collector import collect_crashes
from app.features.feature_engineer import build_features
from app.features.feature_engineer import parse_timestamp
from app.ml.predictor import predict
from app.explanations.explainer import explain
from app.recommendations.recommender import recommend

def update(scan, progress, stage):
    scan.progress,scan.current_stage=progress,stage; db.session.commit()

def start_scan(app):
    info=system_info(); scan=ScanSession(computer_name=info['computer_name'],operating_system=info['operating_system'],status='pending')
    db.session.add(scan); db.session.commit(); threading.Thread(target=_run,args=(app,scan.id),daemon=True).start(); return scan

def _run(app, scan_id):
  with app.app_context():
    scan=ScanSession.query.get(scan_id); start=time.time(); warnings=[]
    try:
      scan.status='running'; update(scan,5,'Checking permissions')
      update(scan,15,'Collecting installed device drivers'); drivers,err=collect_drivers(); warnings += [err] if err else []
      update(scan,35,'Collecting relevant Windows Event Logs'); events,err=collect_events(); warnings += [err] if err else []
      update(scan,50,'Collecting crash-dump metadata'); crashes,err=collect_crashes(); warnings += [err] if err else []
      update(scan,62,'Cleaning and integrating evidence')
      persisted=[]
      for row in drivers:
        item=Driver(scan_id=scan.id,**row); db.session.add(item); persisted.append(item)
      db.session.flush()
      for row in events:
        message=row.get('Message') or ''; linked=next((d for d in persisted if (d.driver_name or '').lower() in message.lower()),None)
        db.session.add(Event(scan_id=scan.id,driver_id=linked.id if linked else None,event_time=parse_timestamp(row.get('TimeCreated')),event_source=row.get('ProviderName'),event_code=row.get('Id'),severity=row.get('LevelDisplayName'),description=message,related_device=None))
      # Preserve raw crash/BugCheck metadata for later technical research review.
      scan.crash_evidence=json.dumps(crashes)
      db.session.commit(); update(scan,72,'Engineering driver features')
      for i,item in enumerate(persisted):
        row={c.name:getattr(item,c.name) for c in item.__table__.columns}; features=build_features(row,events,crashes)
        try: label,confidence=predict(features)
        except FileNotFoundError as exc: raise RuntimeError(str(exc))
        db.session.add(Prediction(scan_id=scan.id,driver_id=item.id,classification=label,confidence=confidence,main_evidence=explain(features),recommendation=recommend(label)))
        if i % 20 == 0: db.session.commit()
      update(scan,93,'Saving results and generating recommendations'); scan.driver_count=len(persisted); scan.event_count=len(events); scan.crash_count=len(crashes); scan.status='completed'; scan.progress=100; scan.current_stage='Complete'; scan.completed_at=datetime.utcnow(); scan.processing_time=round(time.time()-start,2)
      if warnings: scan.error_message=' | '.join(warnings)
      db.session.commit()
    except Exception as exc:
      scan.status='failed'; scan.error_message=str(exc); scan.completed_at=datetime.utcnow(); scan.processing_time=round(time.time()-start,2); db.session.commit()
