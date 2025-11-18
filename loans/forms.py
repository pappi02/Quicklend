from django import forms
from .models import Borrower, Loan, Collateral, Payment, CollateralImage, Guarantor


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['amount', 'interest_rate', 'repayment_period_weeks', 'start_date', 'end_date']


class CollateralForm(forms.ModelForm):
    collateral_images = forms.FileField(widget=MultipleFileInput(attrs={'multiple': True}), required=False)

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
        fields = ['name', 'phone', 'id_number', 'email', 'business_type', 'front_id', 'back_id']


class GuarantorForm(forms.ModelForm):
    class Meta:
        model = Guarantor
        fields = ['names', 'phonenumber', 'national_id', 'emails']
