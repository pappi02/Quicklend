from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import os
import io
from PyPDF2 import PdfReader, PdfWriter
from reportlab.platypus import Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from .utils_security import generate_serial, sha256_of_file, make_qr_image

def secure_pdf_v2(file_path):
    pass


def generate_loan_pdf_v2(loan_data, file_path, logo_path=None, verification_base_url=None):
    width, height = A4
    temp_pdf = file_path + ".tmp.pdf"
    c = canvas.Canvas(temp_pdf, pagesize=A4)

    serial = generate_serial()
    loan_data['serial_number'] = serial

    margin = 40
    card_width = width - 2 * margin
    current_y = height - 120   # More top space to avoid header collision

    # ===================================================================
    #   HEADER STRIP (cleaner, non-overlapping)
    # ===================================================================
    for i, alpha in enumerate([0.18, 0.12, 0.08]):
        c.setFillAlpha(alpha)
        c.setFillColor(colors.HexColor("#6C63FF"))
        c.roundRect(margin - i*3, height - 130 - i*3, card_width + 6*i, 90 + i*4, 10, fill=1, stroke=0)
    c.setFillAlpha(1.0)

    # Logo
    if logo_path and os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            c.drawImage(logo, margin, height - 120, width=70, height=55, preserveAspectRatio=True, mask='auto')
        except:
            pass

    # Header Text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 28)
    c.drawString(margin + 90, height - 85, "QuickLend Maseno")

    c.setFont("Helvetica", 12)
    c.setFillColor(colors.HexColor("#E6E0FF"))
    c.drawString(margin + 90, height - 110, "Official Loan Agreement & Receipt")

    # Serial number (top-right)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawRightString(width - margin, height - 90, f"Receipt No: {serial}")

    # ===================================================================
    #   BACKGROUND WATERMARK (lighter & safe)
    # ===================================================================
    c.saveState()
    c.setFillAlpha(0.06)
    c.setFillColor(colors.HexColor("#BBBBBB"))
    c.setFont("Helvetica-Bold", 95)

    c.translate(width/2, height/2)
    c.rotate(45)
    c.drawCentredString(0, 0, "QUICKLEND")
    c.restoreState()
    c.setFillAlpha(1)

    # ===================================================================
    #   CARD HELPERS
    # ===================================================================
    card_gap = 35  # More spacing between cards

    def draw_card(title, bg_color, card_height):
        nonlocal current_y
        c.setFillColor(bg_color)
        c.roundRect(margin, current_y - card_height, card_width, card_height, 12, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#1A1A1A"))
        c.setFont("Helvetica-Bold", 16)
        c.drawString(margin + 18, current_y - 28, title)

        content_start_y = current_y - 50
        current_y -= (card_height + card_gap)
        return margin + 18, content_start_y

    # ===================================================================
    #   Borrower Information (taller card)
    # ===================================================================
    x, y = draw_card("Borrower Information", colors.HexColor("#F8FAFF"), 140)

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.HexColor("#222"))

    c.drawString(x, y,     f"Name:    {loan_data.get('borrower_name', '-')}")
    c.drawString(x, y-22,  f"Phone:   {loan_data.get('phone_number', '-')}")
    c.drawString(x, y-44,  f"Email:   {loan_data.get('email', '-')}")

    # ===================================================================
    #   Loan Details (taller)
    # ===================================================================
    x, y = draw_card("Loan Details", colors.HexColor("#FFF5E6"), 150)

    c.drawString(x, y,       f"Loan Amount:     KES {loan_data.get('loan_amount', '0')}")
    c.drawString(x, y-22,    f"Total Repay:     KES {loan_data.get('total_amount', '0')}")
    c.drawString(x, y-44,    f"Start Date:      {loan_data.get('start_date', '-')}")
    c.drawString(x, y-66,    f"Due Date:        {loan_data.get('end_date', '-')}")

    # ===================================================================
    #   Collateral Card (auto-wrapped text)
    # ===================================================================
    x, y = draw_card("Collateral", colors.HexColor("#F0FFF0"), 130)

    collateral_text = loan_data.get("collateral") or "No collateral provided"

    from reportlab.platypus import Paragraph
    from reportlab.lib.styles import getSampleStyleSheet
    styles = getSampleStyleSheet()
    para = Paragraph(f"<font size=11><b>Item:</b> {collateral_text}</font>", styles["Normal"])

    w, h = para.wrap(card_width - 40, 100)
    para.drawOn(c, x, y - h + 20)

    # ===================================================================
    #   Terms & Conditions (bigger space)
    # ===================================================================
    x, y = draw_card("Terms & Conditions", colors.HexColor("#FFF8EA"), 155)

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.HexColor("#333333"))

    terms = [
        "1. Full repayment required by the due date.",
        "2. Late payment may result in penalties.",
        "3. Collateral may be forfeited upon default.",
        "4. This is a legally binding agreement.",
        "5. Verify authenticity using the QR code."
    ]

    line_y = y
    for line in terms:
        c.drawString(x, line_y, line)
        line_y -= 16

    # ===================================================================
    #   MICROTEXT (moved far down, safe)
    # ===================================================================
    c.setFont("Helvetica", 5)
    c.setFillColor(colors.HexColor("#C0C0C0"))

    micro_y_start = current_y + 20

    micro_line = "QUICKLEND • AUTHENTIC • VERIFY QR • DO NOT ACCEPT WITHOUT QR CODE • "
    for row in range(5):
        ypos = micro_y_start - (row * 12)
        for col in range(10):
            xpos = margin + col * 52
            if xpos < width - margin:
                c.drawString(xpos, ypos, micro_line)

    # FINISH PAGE
    c.showPage()
    c.save()

    # ===================================================================
    #   HASH + QR + FOOTER LAYER
    # ===================================================================
    file_hash = sha256_of_file(temp_pdf)
    verification_url = f"{verification_base_url}?s={serial}&h={file_hash}" if verification_base_url else f"S:{serial}"

    qr_img = make_qr_image(verification_url, error_correction='H')

    overlay_buf = io.BytesIO()
    overlay = canvas.Canvas(overlay_buf, pagesize=A4)

    # QR bottom-right
    overlay.drawImage(qr_img, width - margin - 140, 45, width=130, height=130)

    overlay.setFillColor(colors.HexColor("#222"))
    overlay.setFont("Helvetica-Bold", 12)
    overlay.drawString(margin, 115, "Verification QR Code")

    #overlay.setFont("Helvetica", 10)
    #overlay.drawString(margin, 95, f"Serial: {serial}")
    #overlay.drawString(margin, 75, f"Hash: {file_hash[:32]}...")

    overlay.setFont("Helvetica-Oblique", 10)
    overlay.setFillColor(colors.HexColor("#666"))
    overlay.drawString(margin, 50, "This document is digitally secured • Verify at quicklend.co/verify")

    # Signature block
    #overlay.setFont("Helvetica-Bold", 12)
    #overlay.setFillColor(colors.HexColor("#6C63FF"))
    #overlay.drawString(width - margin - 200, 75, "Digitally Authorized")
    #overlay.drawString(width - margin - 200, 55, "QuickLend Maseno")

    overlay.save()
    overlay_buf.seek(0)

    # MERGE LAYERS
    reader = PdfReader(temp_pdf)
    writer = PdfWriter()
    overlay_pdf = PdfReader(overlay_buf)
    overlay_page = overlay_pdf.pages[0]

    for page in reader.pages:
        page.merge_page(overlay_page)
        writer.add_page(page)

    writer.add_metadata({
        "/Title": f"QuickLend Receipt - {serial}",
        "/Author": "QuickLend Maseno",
        "/Producer": "QuickLend Secure PDF System V2",
        "/ReceiptSerial": serial,
        "/ReceiptHash": file_hash
    })

    with open(file_path, "wb") as f:
        writer.write(f)

    os.remove(temp_pdf)
    secure_pdf_v2(file_path)

    return {"serial": serial, "hash": file_hash, "verification_url": verification_url}
