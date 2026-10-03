import csv, io
from flask import Blueprint, request, send_file
from app.database.models import ScanSession
from app.ml.predictor import load_production_model
from app.reports.pdf_report import build_pdf
reports_bp=Blueprint('reports',__name__,url_prefix='/api/reports')
@reports_bp.get('/<int:scan_id>/export')
def export_csv(scan_id):
 s=ScanSession.query.get_or_404(scan_id); data=io.StringIO(); writer=csv.writer(data)
 try: model_version=load_production_model().get('model_version','Unavailable')
 except Exception: model_version='Unavailable'
 writer.writerow(['WinDrive diagnostic report'])
 writer.writerow(['Scan ID',s.id]); writer.writerow(['Computer',s.computer_name]); writer.writerow(['Operating system',s.operating_system]); writer.writerow(['Started',s.started_at]); writer.writerow(['Completed',s.completed_at]); writer.writerow(['Model version',model_version]); writer.writerow(['Drivers',s.driver_count]); writer.writerow(['Relevant events',s.event_count]); writer.writerow(['Crash/BugCheck records',s.crash_count]); writer.writerow([])
 writer.writerow(['Driver','Device','Provider','Version','Classification','Confidence','Evidence','Recommendation'])
 for d in s.drivers:
  p=d.prediction; writer.writerow([d.driver_name,d.device_name,d.provider,d.version,p.classification if p else '',p.confidence if p else '',p.main_evidence if p else '',p.recommendation if p else ''])
 if request.args.get('format','csv').lower() == 'pdf':
  return send_file(io.BytesIO(build_pdf(s,model_version)),mimetype='application/pdf',as_attachment=True,download_name=f'windrive-scan-{scan_id}.pdf')
 writer.writerow([]); writer.writerow(['Disclaimer','WinDrive is a diagnostic aid. Predictions are probability-based indications, not proof of root cause. No driver was changed by this report.'])
 return send_file(io.BytesIO(data.getvalue().encode('utf-8-sig')),mimetype='text/csv',as_attachment=True,download_name=f'windrive-scan-{scan_id}.csv')
