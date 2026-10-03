from flask import Blueprint, jsonify, current_app
from app.database.models import db, ScanSession, Driver, Event
from app.services.scan_service import start_scan
scans_bp=Blueprint('scans',__name__,url_prefix='/api')
@scans_bp.post('/scans/start')
def begin():
    scan=start_scan(current_app._get_current_object()); return jsonify({'id':scan.id,'status':scan.status}),202
@scans_bp.get('/scan/<int:id>/progress')
def progress(id):
    s=db.get_or_404(ScanSession,id); return jsonify({'id':s.id,'status':s.status,'progress':s.progress,'stage':s.current_stage,'drivers_found':s.driver_count,'events_processed':s.event_count,'crash_records':s.crash_count,'message':s.error_message})
@scans_bp.post('/scans/<int:id>/cancel')
def cancel(id):
    s=db.get_or_404(ScanSession,id)
    if s.status in ('pending','running'): s.status='cancelled'; s.current_stage='Cancelled'; db.session.commit()
    return jsonify({'status':s.status})
@scans_bp.get('/scan/<int:id>/results')
def results(id):
    s=db.get_or_404(ScanSession,id); rows=[]
    for d in s.drivers:
      p=d.prediction; rows.append({'id':d.id,'driver':d.driver_name,'device':d.device_name,'classification':p.classification if p else 'UNAVAILABLE','confidence':float(p.confidence) if p else 0,'evidence':p.main_evidence if p else 'Prediction unavailable'})
    unassociated = Event.query.filter_by(scan_id=s.id, driver_id=None).count()
    return jsonify({'scan':{'id':s.id,'status':s.status,'warning':s.error_message,'driver_count':s.driver_count,'event_count':s.event_count,'crash_count':s.crash_count,'unassociated_event_count':unassociated,'crash_evidence_available':bool(s.crash_evidence)},'results':rows})
@scans_bp.get('/scan/<int:scan_id>/driver/<int:driver_id>')
def detail(scan_id,driver_id):
    d=Driver.query.filter_by(id=driver_id,scan_id=scan_id).first_or_404(); p=d.prediction
    events=[{'time':event.event_time.isoformat() if event.event_time else None,'source':event.event_source,'id':event.event_code,'severity':event.severity,'message':event.description} for event in d.events]
    return jsonify({'driver':{c.name:getattr(d,c.name) for c in d.__table__.columns},'prediction':{'classification':p.classification,'confidence':float(p.confidence),'evidence':p.main_evidence,'recommendation':p.recommendation} if p else None,'events':events})
@scans_bp.get('/scans')
def history():
    scans=ScanSession.query.order_by(ScanSession.started_at.desc()).all(); data=[]
    for s in scans:
      counts={x:0 for x in ('NORMAL','SUSPICIOUS','FAULTY')}
      for d in s.drivers:
       if d.prediction: counts[d.prediction.classification]=counts.get(d.prediction.classification,0)+1
      data.append({'id':s.id,'date':s.started_at.isoformat(),'computer':s.computer_name,'status':s.status,'drivers':s.driver_count,'duration':s.processing_time,'counts':counts})
    return jsonify(data)
