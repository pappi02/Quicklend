from django.contrib import admin
from .models import Borrower, Loan, Payment, TransactionHistory, Collateral

admin.site.register(Borrower)
admin.site.register(Loan)
admin.site.register(Payment)
admin.site.register(TransactionHistory)
admin.site.register(Collateral)
