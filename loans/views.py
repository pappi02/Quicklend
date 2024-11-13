from datetime import date
from django.contrib import messages  # Correct import for messages
from django.shortcuts import render, get_object_or_404, redirect
from .forms import BorrowerForm, CollateralForm, LoanForm, PaymentForm
from .models import Borrower, Loan
from django.db.models import Sum
from django.contrib.auth.decorators import login_required
from django_otp.decorators import otp_required
from django.contrib.auth.decorators import user_passes_test
from django.db.models import Q
from django.contrib.auth import logout
from django.views.decorators.cache import never_cache




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

            #redirect to loan creation success page
           
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



