from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _text(value):
    return escape(str(value if value not in (None, "") else "Unavailable"))


def build_pdf(scan, model_version):
    """Build a read-only diagnostic report from persisted scan results only."""
    output = BytesIO()
    document = SimpleDocTemplate(output, pagesize=A4, rightMargin=14 * mm, leftMargin=14 * mm, topMargin=14 * mm, bottomMargin=14 * mm)
    styles = getSampleStyleSheet()
    story = [Paragraph("WinDrive Diagnostic Report", styles["Title"]), Spacer(1, 5 * mm)]
    summary = [["Scan ID", _text(scan.id)], ["Computer", _text(scan.computer_name)], ["Operating system", _text(scan.operating_system)], ["Started", _text(scan.started_at)], ["Completed", _text(scan.completed_at)], ["Model version", _text(model_version)], ["Drivers", _text(scan.driver_count)], ["Relevant events", _text(scan.event_count)], ["Crash/BugCheck records", _text(scan.crash_count)]]
    table = Table(summary, colWidths=[45 * mm, 130 * mm])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8f0f2")), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.extend([table, Spacer(1, 6 * mm), Paragraph("Driver findings", styles["Heading2"])])
    for driver in scan.drivers:
        prediction = driver.prediction
        story.append(Paragraph(f"<b>{_text(driver.driver_name)}</b> — {_text(prediction.classification if prediction else 'Prediction unavailable')}", styles["Heading3"]))
        story.append(Paragraph(f"Device: {_text(driver.device_name)} | Provider: {_text(driver.provider)} | Version: {_text(driver.version)} | Confidence: {_text(f'{float(prediction.confidence) * 100:.1f}%' if prediction else None)}", styles["BodyText"]))
        story.append(Paragraph(f"Evidence: {_text(prediction.main_evidence if prediction else None)}", styles["BodyText"]))
        story.append(Paragraph(f"Recommendation: {_text(prediction.recommendation if prediction else None)}", styles["BodyText"]))
        story.append(Spacer(1, 3 * mm))
    story.extend([Spacer(1, 4 * mm), Paragraph("Disclaimer: WinDrive is a diagnostic aid. Results are probability-based indications and do not prove root cause. This report did not change any driver or Windows configuration.", styles["Italic"])])
    document.build(story)
    return output.getvalue()
