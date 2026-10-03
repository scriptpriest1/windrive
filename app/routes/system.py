from flask import Blueprint, jsonify, render_template
from app.services.system_service import system_info, permission_info
from app.database.models import ScanSession
system_bp=Blueprint('system',__name__)
@system_bp.get('/')
def home(): return render_template('index.html')
@system_bp.get('/api/system-info')
def info():
    data=system_info(); last=ScanSession.query.order_by(ScanSession.started_at.desc()).first(); data['last_scan']=last.completed_at.isoformat() if last and last.completed_at else None; return jsonify(data)
@system_bp.get('/api/permissions')
def permissions(): return jsonify(permission_info())
