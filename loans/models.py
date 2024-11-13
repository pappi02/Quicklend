from django.db import models 
from django.db.models import Sum
from datetime import date




# Borrowers Table
class Borrower(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    email = models.EmailField(unique=True)
    BUSINESS_TYPE_CHOICES = [
        ('student', 'Student'),
        ('business', 'Business'),
    ]

    business_type = models.CharField(max_length=10, choices=BUSINESS_TYPE_CHOICES)

    def __str__(self):
        return self.name

# Loans Table
class Loan(models.Model):
    id = models.AutoField(primary_key=True)
    borrower = models.ForeignKey(Borrower, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=4, decimal_places=2)  # Example: 5.00 for 5%
    repayment_period_weeks = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('overdue', 'Overdue'),
        ('paid_off', 'Paid Off'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')

    def __str__(self):
        return f"Loan {self.id} for {self.borrower.name}"
    
    def calculate_total_interest(self):
        """
        Calculate the total interest for the loan using the flat-rate method.
        """
        return (self.amount * self.interest_rate * self.repayment_period_weeks) / 100

    def calculate_total_repayment(self):
        """
        Calculate the total repayment (principal + interest).
        """
        return self.amount + self.calculate_total_interest()

    def calculate_remaining_balance(self):
        total_paid = self.payments.aggregate(Sum('amount'))['amount__sum'] or 0
        return self.amount + (self.amount * (self.interest_rate / 100)) - total_paid

    def update_status(self):
        # Check if the loan is fully paid off
        if self.calculate_remaining_balance() <= 0:
            self.status = 'paid_off'
        elif self.end_date < date.today():
            self.status = 'overdue'
        else:
            self.status = 'active'
        self.save()


# Collateral Table
class Collateral(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey('Loan', on_delete=models.CASCADE)  # Using string reference
    description = models.CharField(max_length=255, blank=True, null=True)
    value = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True) # Estimated value of the collateral
    COLLATERAL_STATUS_CHOICES = [
        ('secured', 'Secured'),
        ('released', 'Released'),
        ('reposessed', 'Repossessed'),
        ('none', 'none')
    ]
    status = models.CharField(max_length=10, choices=COLLATERAL_STATUS_CHOICES, default='none')
    date_added = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Collateral for Loan {self.loan.id}: {self.description} valued at {self.value}"

# Payments Table
class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(Loan, related_name='payments', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    PAYMENT_TYPE_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_payment', 'Mobile Payment'),
        # Add more options as needed
    ]
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_late = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        # Check if the payment is late
        if self.date > self.loan.end_date:
            self.is_late = True
        else:
            self.is_late = False

        # Save the payment record
        super().save(*args, **kwargs)

        # Update loan status after each payment
        if self.loan.calculate_remaining_balance() <= 0:
            self.loan.status = 'paid_off'
        elif self.loan.status != 'paid_off' and self.is_late:
            self.loan.status = 'overdue'

        # Save the updated loan status
        self.loan.save()

    def __str__(self):
        return f"Payment {self.id} for Loan {self.loan.id}"

# Transaction History Table
class TransactionHistory(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    description = models.TextField()
    date = models.DateField()

    def __str__(self):
        return f"Transaction {self.id} for Loan {self.loan.id}"
