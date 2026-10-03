import csv, io
from flask import Blueprint, send_file
from app.database.models import ScanSession
reports_bp=Blueprint('reports',__name__,url_prefix='/api/reports')
@reports_bp.get('/<int:scan_id>/export')
def export_csv(scan_id):
 s=ScanSession.query.get_or_404(scan_id); data=io.StringIO(); writer=csv.writer(data); writer.writerow(['Driver','Device','Provider','Version','Classification','Confidence','Evidence','Recommendation'])
 for d in s.drivers:
  p=d.prediction; writer.writerow([d.driver_name,d.device_name,d.provider,d.version,p.classification if p else '',p.confidence if p else '',p.main_evidence if p else '',p.recommendation if p else ''])
 return send_file(io.BytesIO(data.getvalue().encode()),mimetype='text/csv',as_attachment=True,download_name=f'windrive-scan-{scan_id}.csv')
