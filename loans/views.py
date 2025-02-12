import io
import os
from datetime import date
from django.conf import settings
from django.contrib import messages  # Correct import for messages
from django.shortcuts import render, get_object_or_404, redirect
import qrcode
from .forms import BorrowerForm, CollateralForm, LoanForm, PaymentForm, GuarantorForm
from .models import Borrower, Loan, Guarantor
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.mail import send_mail
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A6
from reportlab.lib import colors
from io import BytesIO
from django.core.mail import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import io
from PyPDF2 import PdfReader, PdfWriter



@user_passes_test(lambda user: user.is_staff)
@login_required
def loan_list(request):
    search_query = request.GET.get('search', '')
    loans = Loan.objects.all().order_by('-id')

    if search_query:
        loans = loans.filter(
            Q(id__icontains=search_query) | Q(borrower__name__icontains=search_query)
        )

    context = {
        'loans': loans,
    }

    return render(request, 'loan_list.html', context)



def loan_detail(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    payments = loan.payments.all()  # Use 'loan.payments' instead of 'Payment.objects.filter(loan=loan)'

    remaining_balance = loan.calculate_remaining_balance()
    total_paid = payments.aggregate(Sum('amount'))['amount__sum'] or 0

    # Handle the form submission for a new payment
    if request.method == "POST":
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.loan = loan
            payment.save()

            # Directly update the loan status after payment
            if loan.calculate_remaining_balance() <= 0:
                loan.status = 'paid_off'
            elif loan.end_date < date.today():
                loan.status = 'overdue'
            else:
                loan.status = 'active'

            loan.save()  # Save the updated status

            # Redirect to the payment confirmation page
            return redirect('payment_confirmation', loan_id=loan.id)  # Ensure 'payment_confirmation' URL exists
    else:
        form = PaymentForm()

    context = {
        'loan': loan,
        'payments': payments,
        'remaining_balance': remaining_balance,
        'total_paid': total_paid,
        'form': form,
    }

    return render(request, 'loan_detail.html', context)



def payment_confirmation(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Get the most recent payment made to this loan
    payment = loan.payments.last()  # Assuming the last payment is the most recent one
    
    # Calculate the remaining balance
    remaining_balance = loan.calculate_remaining_balance()

    context = {
        'loan': loan,
        'payment': payment,
        'remaining_balance': remaining_balance,
    }

    return render(request, 'payment_confirmation.html', context)



@login_required
def create_loan(request):
    if request.method == "POST":
        borrower_form = BorrowerForm(request.POST)
        loan_form = LoanForm(request.POST)
        collateral_form = CollateralForm(request.POST)
        guarantor_form = GuarantorForm(request.POST)

        if borrower_form.is_valid() and loan_form.is_valid() and guarantor_form.is_valid():
            email = borrower_form.cleaned_data['email']
            borrower, created = Borrower.objects.get_or_create(
                email=email,
                defaults={
                    'name': borrower_form.cleaned_data['name'],
                    'phone': borrower_form.cleaned_data['phone'],
                    'business_type': borrower_form.cleaned_data['business_type']
                }
            )

            loan = loan_form.save(commit=False)
            loan.borrower = borrower
            loan.save()

            if collateral_form.is_valid():
                collateral = collateral_form.save(commit=False)
                collateral.loan = loan
                collateral.save()

            guarantor = guarantor_form.save(commit=False)
            guarantor.loan = loan
            guarantor.save()

            # Prepare loan data for PDF generation
            loan_data = {
                'date': loan.start_date.strftime('%Y-%m-%d'),  # Agreement date
                'agreement_number': f"LN-{loan.id}",  # Unique loan agreement number
                'borrower_name': borrower.name,
                'borrower_phone': borrower.phone,
                'borrower_id_number': borrower.id_number,  # Assuming ID is used as borrower ID
                'borrower_email': borrower.email,
                'business_type': borrower.business_type,
                'loan_amount': f"{loan.amount:,.2f}",  # Format with commas
                'interest_rate': loan.interest_rate,
                'repayment_period': loan.repayment_period_weeks,
                'start_date': loan.start_date.strftime('%d-%m-%Y'),
                'end_date': loan.end_date.strftime('%d-%m-%Y'),
                'guarantor_required': True if guarantor else False,
                'guarantor_names': guarantor.names if guarantor else "N/A",
                'guarantor_phonnumber': guarantor.phonenumber if guarantor else "N/A",
                'guarantor_emails': guarantor.emails if guarantor else "N/A",
                'guarantor_national_id': guarantor.national_id if guarantor else "N/A",
                'collateral_description': collateral.description if collateral else "None",
                'collateral_value': f"{collateral.value:,.2f}" if collateral else "0.00",
                'collateral_acquired': True if collateral else False,
                'repayment_schedule': f"Weekly Payments of {loan.amount / loan.repayment_period_weeks:,.2f} KES",
                'repayment_method': "Mobile Money (Mpesa)",  # Default repayment method
            }

            # Generate PDF
            pdf_directory = os.path.join(settings.BASE_DIR, 'media', 'pdfs')
            if not os.path.exists(pdf_directory):
                os.makedirs(pdf_directory)

            pdf_file_path = os.path.join(pdf_directory, f'loan_agreement_{loan.id}.pdf')
            generate_loan_pdf(loan_data, pdf_file_path)

            # Send the PDF as an email attachment
            send_email_with_attachment(borrower.email, pdf_file_path)

            messages.success(request, 'Loan created successfully. PDF receipt sent via email.')
            return redirect('loan_creation_success')

        else:
            messages.error(request, 'There were errors in the form, please correct them.')

    else:
        borrower_form = BorrowerForm()
        loan_form = LoanForm()
        collateral_form = CollateralForm()
        guarantor_form = GuarantorForm()

    context = {
        'borrower_form': borrower_form,
        'loan_form': loan_form,
        'collateral_form': collateral_form,
        'guarantor_form': guarantor_form,
    }

    return render(request, 'create_loan.html', context)



'''
def send_sms_with_link(phone_number, sms_link):
    """
    Function to send an SMS via Twilio.
    """
    try:
        # Initialize the Twilio client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        # Send the SMS
        message = client.messages.create(
            body=f"Your loan agreement and receipt are ready. Download it here: {sms_link}",
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print(f"SMS sent to {phone_number} with SID: {message.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")
'''


def send_email_with_attachment(email, pdf_file_path):
    """
    Function to send an email with the loan agreement PDF as an attachment.
    """
    subject = 'Your Loan Agreement and Receipt'
    message = "Dear borrower, attached is your loan agreement and receipt."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    email_message = EmailMessage(subject, message, from_email, recipient_list)

    try:
        # Attach the PDF file to the email
        email_message.attach_file(pdf_file_path)
        email_message.send()
        print(f"Email sent with PDF attachment to {email}")
    except Exception as e:
        print(f"Error sending email with attachment: {e}")


def loan_creation_success(request):
    return render(request, 'loan_creation_success.html')




def generate_loan_pdf(loan_data, file_path):
    # Create the PDF document using ReportLab's built-in Helvetica fonts
    doc = SimpleDocTemplate(file_path, pagesize=letter,
                            rightMargin=72, leftMargin=72,
                            topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    # Use Helvetica (built-in)
    styles.add(ParagraphStyle(name='Underline', fontSize=12, leading=14,
                              alignment=1, textColor=colors.black,
                              fontName='Helvetica', underlineProportion=0.9))
    styles.add(ParagraphStyle(name='Body', fontSize=10, leading=12,
                              alignment=0, textColor=colors.black,
                              fontName='Helvetica'))

    elements = []

    # Generate QR Code for authentication and position it at the top-right
    qr_url = loan_data.get("qr_auth_url", "http://default-auth-url.com")
    qr = qrcode.QRCode(box_size=2, border=1)
    qr.add_data(qr_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    qr_buffer = io.BytesIO()
    img.save(qr_buffer, format="PNG")
    qr_buffer.seek(0)
    qr_img = Image(qr_buffer, 50, 50)  # size: 50 x 50 points
    # Use a table to position the QR code at the top-right
    qr_table = Table([[qr_img]], colWidths=[50])
    qr_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    # Insert QR code at the beginning
    elements.insert(0, qr_table)
    elements.insert(1, Spacer(1, 12))

    # Header Section
    header_text = f"""
    <para align=center spaceb=3>
    <font name="Helvetica" size=14><u>QUICKLEND LOANS AGENCY</u></font><br/>
    <font size=10>Date: {loan_data['date']}</font><br/>
    <font size=10>Loan Agreement No.: {loan_data['agreement_number']}</font>
    </para>
    """
    elements.append(Paragraph(header_text, styles['Normal']))
    elements.append(Spacer(1, 24))

    # Section I: Borrower Details
    elements.append(Paragraph("<font name='Helvetica' size=12><u>SECTION I: BORROWER DETAILS</u></font>", styles['Normal']))
    borrower_data = [
        ["Borrower's Full Name:", loan_data['borrower_name']],
        ["Phone Number:", loan_data['borrower_phone']],
        ["ID number:", loan_data['borrower_id_number']],
        ["Email Address:", loan_data['borrower_email']],
        ["Business Type:", loan_data['business_type']],
    ]
    borrower_table = Table(borrower_data, colWidths=[2*inch, 4*inch])
    borrower_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(borrower_table)
    elements.append(Spacer(1, 24))

    # Section II: Loan Details
    elements.append(Paragraph("<font name='Helvetica' size=12><u>SECTION II: LOAN DETAILS</u></font>", styles['Normal']))
    loan_details = [
        ["Loan Amount:", f"KES {loan_data['loan_amount']}"],
        ["Interest Rate:", f"{loan_data['interest_rate']}% (per annum)"],
        ["Repayment Period:", f"{loan_data['repayment_period']} week(s)"],
        ["Start Date:", loan_data['start_date']],
        ["End Date:", loan_data['end_date']],
    ]
    loan_table = Table(loan_details, colWidths=[2*inch, 4*inch])
    loan_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
    ]))
    elements.append(loan_table)
    elements.append(Spacer(1, 24))

    # Section III: Guarantor Details (Conditional)
    if loan_data.get('guarantor_required'):
        elements.append(Paragraph("<font name='Helvetica' size=12><u>SECTION III: GUARANTOR DETAILS</u></font>", styles['Normal']))
        guarantor_data = [
            ["Guarantor's Full Name:", loan_data['guarantor_names']],
            ["Phone Number:", loan_data['guarantor_phonnumber']],
            ["Email Address:", loan_data['guarantor_emails']],
            ["ID number:", loan_data['guarantor_national_id']],
        ]
        guarantor_table = Table(guarantor_data, colWidths=[2*inch, 4*inch])
        elements.append(guarantor_table)
        elements.append(Spacer(1, 24))

    # Section IV: Collateral Details
    elements.append(Paragraph("<font name='Helvetica' size=12><u>SECTION IV: COLLATERAL DETAILS</u></font>", styles['Normal']))
    collateral_data = [
        ["Collateral Description:", loan_data['collateral_description']],
        ["Estimated Value:", f"KES {loan_data['collateral_value']}"],
        ["Status of Collateral:", "☐ Acquired" if loan_data['collateral_acquired'] else "☐ Not Acquired"],
    ]
    collateral_table = Table(collateral_data, colWidths=[2*inch, 4*inch])
    elements.append(collateral_table)
    elements.append(Spacer(1, 24))

    # Section V: Payment Terms
    elements.append(Paragraph("<font name='Helvetica' size=12><u>SECTION V: PAYMENT TERMS</u></font>", styles['Normal']))
    payment_text = """
    <para>
    <font name="Helvetica" size=10>
    MAKE PAYMENT TO LIPA NA MPESA (BUY GOODS)<br/>
    TILL NUMBER : 4521896<br/>
    TILL NAME : DAVID NYONGESA<br/><br/>
    Repayment Schedule:<br/>
    {repayment_schedule}<br/>
    Repayment Method: {repayment_method}
    </font>
    </para>
    """.format(**loan_data)
    elements.append(Paragraph(payment_text, styles['Normal']))
    elements.append(Spacer(1, 24))

    # Section VI: Agreement Terms
    agreement_terms = """
    <para>
    <font name="Helvetica" size=12><u>SECTION VI: AGREEMENT TERMS</u></font><br/><br/>
    1. <b>Interest and Fees:</b> The loan shall bear interest at the agreed rate and must comply with CBK regulations.<br/>
    2. <b>Repayment:</b> The Borrower may repay the loan in installments as per the repayment schedule or full amount at any time within the repayment period without penalty.<br/>
    3. <b>Collateral:</b> The Borrower agrees to provide the described collateral as security for the loan. If the Borrower defaults on the loan, the Lender has the right to sell, dispose of, or otherwise liquidate the collateral two (2) weeks after the payment due date to recover the outstanding loan amount, including any accrued interest and associated costs.<br/>
    4. <b>Default and Acceleration:</b> Failure to pay installments on time shall constitute a default, and the full loan amount may become immediately due.<br/>
    5. <b>Expenses:</b> In case of default, the Borrower will bear legal and administrative costs incurred by the Lender to recover the loan.<br/>
    6. <b>Governing Law:</b> This agreement is governed by rules and regulations of the Central Bank of Kenya and the laws of the Republic of Kenya.<br/>
    <br/>
    <font size=8><i>@2025 Quicklend Loans Agency</i></font>
    </para>
    """
    elements.append(Paragraph(agreement_terms, styles['Normal']))
    elements.append(Spacer(1, 24))

    # Signature Section
    signature_data = [
        ["Borrower's Signature:", "_________________________", f"Date: {loan_data['date']}"],
        ["Guarantor's Signature:", "_________________________", f"Date: {loan_data['date']}"],
        ["Lender's Signature:", "_________________________", f"Date: {loan_data['date']}"],
    ]
    signature_table = Table(signature_data, colWidths=[2*inch, 2*inch, 2*inch])
    signature_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,0), (-1,-1), 10),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(signature_table)

    # Build PDF
    doc.build(elements)

    # Add digital signature overlay and set PDF to read-only (by encrypting without a user password)
    add_digital_signature(file_path, file_path, "Authorized Signature: QuickLend")
    set_pdf_readonly(file_path, file_path)

def add_digital_signature(input_pdf_path, output_pdf_path, signature_text):
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=letter)
    can.setFont("Helvetica", 10)
    can.drawString(400, 50, signature_text)
    can.save()

    packet.seek(0)
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(open(input_pdf_path, "rb"))
    writer = PdfWriter()

    for page_num in range(len(existing_pdf.pages)):
        page = existing_pdf.pages[page_num]
        if page_num == 0:
            page.merge_page(new_pdf.pages[0])
        writer.add_page(page)

    with open(output_pdf_path, "wb") as output_stream:
        writer.write(output_stream)

def set_pdf_readonly(input_pdf_path, output_pdf_path, user_pwd=""):
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # Set an owner password to restrict editing; user password is empty so anyone can open but not edit.
    owner_pwd = "owner_secret"
    writer.encrypt(user_pwd, owner_pwd, use_128bit=True)
    
    with open(output_pdf_path, "wb") as f:
        writer.write(f)
        


@login_required
def dashboard(request):
    # Aggregating statistics
    total_loans = Loan.objects.count()
    total_loan_amount = Loan.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_interest_earned = sum([loan.calculate_total_interest() for loan in Loan.objects.all()])

    # Additional metrics (e.g., overdue loans)
    overdue_loans_count = Loan.objects.filter(status='overdue').count()
    paid_off_loans_count = Loan.objects.filter(status='paid_off').count()
    active_loans_count = Loan.objects.filter(status='active').count()

    context = {
        'total_loans': total_loans,
        'total_loan_amount': total_loan_amount,
        'total_interest_earned': total_interest_earned,
        'overdue_loans_count': overdue_loans_count,
        'paid_off_loans_count': paid_off_loans_count,
        'active_loans_count': active_loans_count,
    }
    return render(request, 'dashboard.html', context)








def save_locally(file_path, file_name):
    """
    Save the PDF file locally
    :param file_path: File path where the file should be saved
    :param file_name: Name of the file
    :return: Local file path if successful, else None
    """
    # Define the directory to save the files (e.g., 'media/pdfs')
    save_dir = os.path.join(settings.BASE_DIR, 'media', 'pdfs')
    
    # Make sure the directory exists, create if not
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    # Create the full path to save the file
    full_file_path = os.path.join(save_dir, file_name)

    try:
        # Save the file locally
        with open(full_file_path, 'wb') as f:
            f.write(file_path)
        
        return full_file_path
    except Exception as e:
        print(f"Error saving file locally: {e}")
        return None
    



