import io
import os
from datetime import date
from django.conf import settings
from django.contrib import messages  # Correct import for messages
from django.shortcuts import render, get_object_or_404, redirect
from .forms import BorrowerForm, CollateralForm, LoanForm, PaymentForm
from .models import Borrower, Loan, Collateral, CollateralImage
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
                loan.status = 'past_due'
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
        # Initialize the forms with POST data and FILES
        borrower_form = BorrowerForm(request.POST, request.FILES)
        loan_form = LoanForm(request.POST)
        collateral_form = CollateralForm(request.POST, request.FILES)

        if borrower_form.is_valid() and loan_form.is_valid():
            # Check if the borrower already exists by email
            email = borrower_form.cleaned_data['email']
            borrower, created = Borrower.objects.get_or_create(
                email=email,
                defaults={
                    'name': borrower_form.cleaned_data['name'],
                    'phone': borrower_form.cleaned_data['phone'],
                    'business_type': borrower_form.cleaned_data['business_type'],
                    'front_id': borrower_form.cleaned_data.get('front_id'),
                    'back_id': borrower_form.cleaned_data.get('back_id'),
                }
            )

            # If borrower already exists, update their information
            if not created:
                borrower.name = borrower_form.cleaned_data['name']
                borrower.phone = borrower_form.cleaned_data['phone']
                borrower.business_type = borrower_form.cleaned_data['business_type']
                borrower.front_id = borrower_form.cleaned_data.get('front_id')
                borrower.back_id = borrower_form.cleaned_data.get('back_id')
                borrower.save()

            # Create and save the loan
            loan = loan_form.save(commit=False)
            loan.borrower = borrower  # Attach the borrower to the loan
            loan.save()

            # Initialize collateral to None
            collateral = None

            # If collateral form is valid, save collateral
            if collateral_form.is_valid():
                collateral = collateral_form.save(commit=False)
                collateral.loan = loan  # Attach the loan to the collateral
                collateral.save()

                # Handle multiple collateral images
                images = request.FILES.getlist('collateral_images')
                for image in images:
                    CollateralImage.objects.create(collateral=collateral, image=image)

            # Generate the loan agreement and receipt PDF
            loan_data = {
                'borrower_name': borrower.name,
                'loan_amount': loan.amount,
                'total_amount': loan.total_amount,  # Ensure total_amount exists
                'start_date': loan.start_date,
                'end_date': loan.end_date,
                'collateral': collateral.description if collateral else None,
                'phone_number': borrower.phone,
                'email': borrower.email,
            }

            # Set the file path for saving the PDF (ensure the directory exists)
            pdf_directory = os.path.join(settings.MEDIA_ROOT, 'pdfs')  # Use MEDIA_ROOT for cross-platform compatibility
            if not os.path.exists(pdf_directory):
                os.makedirs(pdf_directory)  # Create the directory if it doesn't exist

            # Include the file name in the path
            pdf_file_path = os.path.join(pdf_directory, 'loan_agreement_receipt.pdf')

            # Generate the PDF for loan agreement and receipt using new secure generator
            from .pdf_generator_v2 import generate_loan_pdf_v2
            verification_base_url = request.build_absolute_uri('/verify_receipt/')
            result = generate_loan_pdf_v2(loan_data, pdf_file_path, verification_base_url=verification_base_url)

            # Save serial and hash to loan
            loan.receipt_serial = result['serial']
            loan.receipt_hash = result['hash']
            loan.save()

            # Send SMS with the download link
            #send_sms_with_link(borrower.phone, email_link)

            # Send email with the PDF attached
            send_email_with_attachment(borrower.email, pdf_file_path)

            # Success message
            messages.success(request, 'Loan created successfully. Receipt attached to Email.')

            # Redirect to loan creation success page
            return redirect('loan_creation_success')  # Update this to the success URL
        else:
            # If forms are not valid, show error messages
            messages.error(request, 'There were errors in the form, please correct them.')
            context = {
                'borrower_form': borrower_form,
                'loan_form': loan_form,
                'collateral_form': collateral_form,
            }
            return render(request, 'create_loan.html', context)

    else:
        # Initialize empty forms for GET request
        borrower_form = BorrowerForm()
        loan_form = LoanForm()
        collateral_form = CollateralForm()

    # Send the forms to the template
    context = {
        'borrower_form': borrower_form,
        'loan_form': loan_form,
        'collateral_form': collateral_form,
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
    Function to send an HTML email with the PDF attached.
    """
    from django.core.mail import EmailMessage

    subject = 'Your Loan Agreement and Receipt - QuickLend Maseno'
    html_message = """
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f4f4f4;
                margin: 0;
                padding: 0;
            }}
            .container {{
                max-width: 600px;
                margin: 20px auto;
                background-color: #ffffff;
                padding: 20px;
                border-radius: 8px;
                box-shadow: 0 0 10px rgba(0, 0, 0, 0.1);
            }}
            .header {{
                background-color: #667eea;
                color: #ffffff;
                padding: 20px;
                text-align: center;
                border-radius: 8px 8px 0 0;
            }}
            .content {{
                padding: 20px;
                color: #333333;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 10px;
                text-align: center;
                color: #666666;
                border-radius: 0 0 8px 8px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>QuickLend Maseno</h1>
                <p>Your Trusted Loan Partner</p>
            </div>
            <div class="content">
                <h2>Dear Borrower,</h2>
                <p>Thank you for choosing QuickLend Maseno for your loan needs. Your loan agreement and receipt have been successfully processed and are attached to this email.</p>
                <p>Please find your loan agreement and receipt attached as a PDF file.</p>
                <p>If you have any questions or need assistance, please don't hesitate to contact our support team.</p>
                <p>Best regards,<br>The QuickLend Maseno Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2023 QuickLend Maseno. All rights reserved.</p>
                <p>For support, email us at support@quicklend.co.ke</p>
            </div>
        </div>
    </body>
    </html>
    """
    plain_message = "Dear borrower, your loan agreement and receipt are attached to this email."
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    try:
        email_message = EmailMessage(subject, plain_message, from_email, recipient_list)
        email_message.attach_file(pdf_file_path, 'application/pdf')
        email_message.send()
        print(f"Email with attachment sent to {email}")
    except Exception as e:
        print(f"Error sending email: {e}")


def loan_creation_success(request):
    # Retrieve the latest loan created (assuming it's the most recent one)
    loan = Loan.objects.last()
    borrower = loan.borrower if loan else None
    context = {
        'loan': loan,
        'borrower': borrower,
    }
    return render(request, 'loan_creation_success.html', context)





@login_required
def dashboard(request):
    # Aggregating statistics
    total_loans = Loan.objects.count()
    total_loan_amount = Loan.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_interest_earned = sum([loan.calculate_total_interest() for loan in Loan.objects.all()])

    # Additional metrics (e.g., past due loans)
    past_due_loans_count = Loan.objects.filter(status='past_due').count()
    paid_off_loans_count = Loan.objects.filter(status='paid_off').count()
    active_loans_count = Loan.objects.filter(status='active').count()

    context = {
        'total_loans': total_loans,
        'total_loan_amount': total_loan_amount,
        'total_interest_earned': total_interest_earned,
        'past_due_loans_count': past_due_loans_count,
        'paid_off_loans_count': paid_off_loans_count,
        'active_loans_count': active_loans_count,
    }
    return render(request, 'dashboard.html', context)




# Function to generate the loan PDF with enhanced styling and signature
def generate_loan_pdf(loan_data, file_path):
    c = canvas.Canvas(file_path, pagesize=A6)  # Adjusted to A6 for a compact look

    # Set background color for header
    c.setFillColor(colors.HexColor('#667eea'))
    c.rect(0, 350, 297, 50, fill=1)

    # Header text
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 370, "QuickLend Maseno")
    c.setFont("Helvetica", 10)
    c.drawString(50, 355, "Loan Agreement and Receipt")

    # Borrower details section
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, 330, "Borrower Information:")
    c.setFont("Helvetica", 8)
    c.drawString(30, 315, f"Name: {loan_data['borrower_name']}")
    c.drawString(30, 300, f"Phone: {loan_data['phone_number']}")
    c.drawString(30, 285, f"Email: {loan_data['email']}")

    # Loan details section
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, 265, "Loan Details:")
    c.setFont("Helvetica", 8)
    c.drawString(30, 250, f"Loan Amount: KES {loan_data['loan_amount']}")
    c.drawString(30, 235, f"Total Amount to be Paid: KES {loan_data['total_amount']}")
    c.drawString(30, 220, f"Start Date: {loan_data['start_date']}")
    c.drawString(30, 205, f"End Date: {loan_data['end_date']}")
    c.drawString(30, 190, f"Collateral: {loan_data['collateral'] if loan_data['collateral'] else 'None'}")

    # Terms and Conditions section with enhanced styling
    c.setFillColor(colors.HexColor('#f0f0f0'))
    c.rect(20, 140, 257, 40, fill=1)
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(30, 170, "Terms and Conditions:")
    c.setFont("Helvetica", 6)
    c.drawString(30, 160, "1. The loan must be repaid in full by the end date.")
    c.drawString(30, 150, "2. Non-payment may result in penalties or collateral loss.")
    c.drawString(30, 140, "3. Any disputes will be settled according to the governing laws.")

    # Signature section
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, 110, "Borrower Signature:")
    c.setFont("Helvetica", 8)
    c.drawString(30, 95, "_______________________  Date: __________")

    # Company signature
    c.setFont("Helvetica-Bold", 8)
    c.drawString(30, 75, "Authorized by: QuickLend Maseno")
    c.drawString(30, 65, "_______________________  Date: __________")

    # Footer
    c.setFillColor(colors.HexColor('#667eea'))
    c.rect(0, 0, 297, 30, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 6)
    c.drawString(30, 15, "Thank you for choosing QuickLend Maseno. For inquiries, contact us at support@quicklend.co.ke")

    # Draw border for the document
    c.setStrokeColor(colors.black)
    c.setLineWidth(2)
    c.rect(5, 5, 287, 407)

    # Finalize the PDF
    c.save()

    # Add a digital signature (text overlay) for authenticity
    add_digital_signature(file_path, file_path, "Authorized Signature: QuickLend Maseno")


def add_digital_signature(input_pdf_path, output_pdf_path, signature_text):
    # Open the existing PDF
    reader = PdfReader(input_pdf_path)
    writer = PdfWriter()

    # Iterate through each page and add the signature
    for page_num in range(len(reader.pages)):
        page = reader.pages[page_num]

        # Create a temporary canvas to overlay text
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=letter)
        can.setFont("Helvetica-Bold", 10)
        can.drawString(400, 50, signature_text)  # Position the signature as needed
        can.save()

        # Move to the beginning of the StringIO buffer and read it as a PDF
        packet.seek(0)
        new_pdf = PdfReader(packet)
        overlay_page = new_pdf.pages[0]

        # Merge the overlay (with text) onto the original PDF page
        page.merge_page(overlay_page)
        
        # Add the modified page to the writer
        writer.add_page(page)

    # Save the output PDF with the applied signature
    with open(output_pdf_path, "wb") as output_pdf:
        writer.write(output_pdf)





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


from django.http import JsonResponse, HttpResponseBadRequest
from .models import Loan

def verify_receipt(request):
    s = request.GET.get("s")  # serial
    h = request.GET.get("h")  # hash
    if not s or not h:
        return HttpResponseBadRequest("Missing parameters")

    try:
        loan = Loan.objects.get(receipt_serial=s)
    except Loan.DoesNotExist:
        return JsonResponse({"status":"not_found", "message":"Receipt not found"}, status=404)

    valid = (loan.receipt_hash == h)
    return JsonResponse({
        "status": "ok",
        "serial": s,
        "valid": valid,
        "loan_id": loan.id if valid else None,
        "borrower": loan.borrower.name if valid else None
    })
    


