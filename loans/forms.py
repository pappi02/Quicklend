from django import forms
from .models import Borrower, Loan, Collateral, Payment


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['amount', 'interest_rate', 'repayment_period_weeks', 'start_date', 'end_date']




# loans/forms.py
from django import forms

class CollateralForm(forms.ModelForm):
    class Meta:
        model = Collateral
        fields = ['description', 'value', 'status']
        widgets = {
            'status': forms.Select(choices=Collateral.COLLATERAL_STATUS_CHOICES),
        }

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['amount', 'date', 'payment_type']

class BorrowerForm(forms.ModelForm):
    class Meta:
        model = Borrower
        fields = ['name', 'phone', 'email', 'business_type']