from django import forms
<<<<<<< HEAD
from .models import Borrower, Loan, Collateral, Payment, CollateralImage


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True
=======
from .models import Borrower, Loan, Collateral, Payment, Guarantor  # Add Guarantor model
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ['amount', 'interest_rate', 'repayment_period_weeks', 'start_date', 'end_date']


<<<<<<< HEAD



=======
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07
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
<<<<<<< HEAD
        fields = ['name', 'phone', 'email', 'business_type', 'front_id', 'back_id']
=======
        fields = ['name', 'phone', 'id_number', 'email', 'business_type']


class GuarantorForm(forms.ModelForm):
    class Meta:
        model = Guarantor
        fields = ['names', 'phonenumber', 'national_id', 'emails']
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07
