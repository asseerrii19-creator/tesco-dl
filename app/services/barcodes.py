from __future__ import annotations

from pathlib import Path

import qrcode
from reportlab.graphics.barcode import code128
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas


def generate_assets(barcode_value: str, request_number: str, client_name: str, asset_code: str, output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe = barcode_value.replace("/", "-")
    qr_path = output_dir / f"{safe}_qr.png"
    pdf_path = output_dir / f"{safe}_label.pdf"

    qr = qrcode.QRCode(version=4, box_size=8, border=2)
    qr.add_data(barcode_value)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(qr_path)

    page = landscape((100 * mm, 55 * mm))
    canvas = Canvas(str(pdf_path), pagesize=page)
    canvas.setTitle(f"TSCO Sample Tag {request_number}")
    canvas.setFont("Helvetica-Bold", 12)
    canvas.drawString(6 * mm, 48 * mm, "TSCO FIELD SAMPLE TAG")
    canvas.setFont("Helvetica", 8)
    canvas.drawString(6 * mm, 42 * mm, f"Request: {request_number}")
    canvas.drawString(6 * mm, 38 * mm, f"Client: {client_name[:42]}")
    canvas.drawString(6 * mm, 34 * mm, f"Asset: {asset_code[:42]}")
    canvas.drawImage(str(qr_path), 75 * mm, 29 * mm, width=20 * mm, height=20 * mm, preserveAspectRatio=True)
    barcode = code128.Code128(barcode_value, barHeight=13 * mm, barWidth=0.34 * mm, humanReadable=True)
    barcode.drawOn(canvas, 6 * mm, 10 * mm)
    canvas.setFont("Helvetica", 7)
    canvas.drawString(6 * mm, 5 * mm, "Scan at field collection, transport handover and laboratory receipt.")
    canvas.showPage()
    canvas.save()
    return {"qr": str(qr_path), "label_pdf": str(pdf_path)}
