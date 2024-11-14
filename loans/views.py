import io
import os
from datetime import date
from django.conf import settings
from django.contrib import messages  # Correct import for messages
from django.shortcuts import render, get_object_or_404, redirect
from .forms import BorrowerForm, CollateralForm, LoanForm, PaymentForm
from .models import Borrower, Loan
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
        # Initialize the forms with POST data
        borrower_form = BorrowerForm(request.POST)
        loan_form = LoanForm(request.POST)
        collateral_form = CollateralForm(request.POST)

        if borrower_form.is_valid() and loan_form.is_valid():
            # Check if the borrower already exists by email
            email = borrower_form.cleaned_data['email']
            borrower, created = Borrower.objects.get_or_create(
                email=email,
                defaults={
                    'name': borrower_form.cleaned_data['name'],
                    'phone': borrower_form.cleaned_data['phone'],
                    'business_type': borrower_form.cleaned_data['business_type'],
                }
            )

            # Create and save the loan
            loan = loan_form.save(commit=False)
            loan.borrower = borrower  # Attach the borrower to the loan
            loan.save()

            # If collateral form is valid, save collateral
            if collateral_form.is_valid():
                collateral = collateral_form.save(commit=False)
                collateral.loan = loan  # Attach the loan to the collateral
                collateral.save()

            # Generate the loan agreement and receipt PDF
            loan_data = {
                'borrower_name': borrower.name,
                'loan_amount': loan.amount,
                'total_amount': loan.total_amount,  # Ensure total_amount exists
                'start_date': loan.start_date,
                'end_date': loan.end_date,
                'collateral': collateral_form.cleaned_data.get('collateral', '') if collateral_form.is_valid() else None,
                'phone_number': borrower.phone,
                'email': borrower.email,
            }

            # Set the file path for saving the PDF (ensure the directory exists)
            pdf_directory = '/home/munga/quicklend/media/pdfs/'  # Adjust the directory path as needed
            if not os.path.exists(pdf_directory):
                os.makedirs(pdf_directory)  # Create the directory if it doesn't exist

            # Include the file name in the path
            pdf_file_path = os.path.join(pdf_directory, 'loan_agreement_receipt.pdf')

            # Generate the PDF for loan agreement and receipt
            generate_loan_pdf(loan_data, pdf_file_path)

            # Get the server IP address and port
            server_ip = "192.168.1.106:8000" 

            # Define the download link
            email_link = f"http://{server_ip}/media/pdfs/loan_agreement_receipt.pdf"

            # Send SMS with the download link
            #send_sms_with_link(borrower.phone, email_link)

            # Send email with the download link
            send_email_with_link(borrower.email, email_link)

            # Success message
            messages.success(request, 'Loan created successfully. Receipt sent via SMS and Email.')

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

def send_email_with_link(email, download_link):
    """
    Function to send an email with the download link.
    """
    subject = 'Your Loan Agreement and Receipt'
    message = f"Dear borrower, your loan agreement and receipt are ready. Download it here: {download_link}"
    from_email = settings.EMAIL_HOST_USER
    recipient_list = [email]

    try:
        send_mail(subject, message, from_email, recipient_list)
        print(f"Email sent to {email}")
    except Exception as e:
        print(f"Error sending email: {e}")


def loan_creation_success(request):
    return render(request, 'loan_creation_success.html')





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




# Function to generate the loan PDF with enhanced styling and signature
def generate_loan_pdf(loan_data, file_path):
    c = canvas.Canvas(file_path, pagesize=A6)  # Adjusted to A6 for a compact look

    # Modern font and adjusted layout for compact page
    c.setFont("Helvetica-Bold", 12)  # Smaller font for a smaller page
    c.drawString(50, 400, "Loan Agreement and Receipt")
    c.setFont("Helvetica", 8)  # Small, readable font size
    c.drawString(30, 380, f"Borrower: {loan_data['borrower_name']}")
    c.drawString(30, 365, f"Loan Amount: KES {loan_data['loan_amount']}")
    c.drawString(30, 350, f"Total Amount to be Paid: KES {loan_data['total_amount']}")
    c.drawString(30, 335, f"Start Date: {loan_data['start_date']}")
    c.drawString(30, 320, f"End Date: {loan_data['end_date']}")
    c.drawString(30, 305, f"Collateral: {loan_data['collateral'] if loan_data['collateral'] else 'None'}")

    # Terms and Conditions section with compact layout
    c.setFont("Helvetica-Oblique", 6)  # Smaller font for terms
    c.drawString(30, 290, "Terms and Conditions:")
    c.drawString(30, 275, "1. The loan must be repaid in full by the end date.")
    c.drawString(30, 260, "2. Non-payment may result in penalties or collateral loss.")

    c.drawString(30, 245, "3. Any disputes will be settled according to the governing laws.")
    
    # Add some space for signature section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, 215, "Borrower Signature:")
    c.setFont("Helvetica", 10)
    c.drawString(30, 200, "_______________________  Date: __________")
    
    # Signature placeholder (could be replaced with a digital signature later)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(30, 170, "Signed by: QuickLend Maseno")
    
    # Add logo or brand name (if applicable)
    # c.drawImage('logo.png', 450, 750, width=100, height=50)  # Optional logo
    
    # Draw border for the document for modern look
    c.setStrokeColor(colors.black)
    c.rect(10, 10, 277, 400)
    
    # Finalize the PDF
    c.save()


    # Add a digital signature (text overlay) for authenticity
    add_digital_signature(file_path, file_path, "Authorized Signature: QuickLend")


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
    


