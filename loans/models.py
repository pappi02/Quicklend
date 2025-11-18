from django.db import models
from django.db.models import Sum
from datetime import date

# Borrowers Table
class Borrower(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
<<<<<<< HEAD
    email = models.EmailField()
=======
    id_number = models.CharField(max_length=10, blank=True)
    email = models.EmailField(blank=True)
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07
    BUSINESS_TYPE_CHOICES = [
        ('student', 'Student'),
        ('business', 'Business'),
    ]
    business_type = models.CharField(max_length=10, choices=BUSINESS_TYPE_CHOICES)
    front_id = models.ImageField(upload_to='borrower_ids/', blank=True, null=True)
    back_id = models.ImageField(upload_to='borrower_ids/', blank=True, null=True)

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
        ('past_due', 'Past Due'),
        ('paid_off', 'Paid Off'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
<<<<<<< HEAD
    receipt_serial = models.CharField(max_length=20, blank=True, null=True, unique=True)
    receipt_hash = models.CharField(max_length=128, blank=True, null=True)
    @property
    def total_amount(self):
        # Assuming you calculate total_amount based on the amount and interest rate
        return self.amount + self.calculate_total_interest()
    
    
    def __str__(self):
        return f"Loan {self.id} for {self.borrower.name}"
    
    def calculate_total_interest(self):
        """
        Calculate the total interest for the loan using the flat-rate method.
        """
        return (self.amount * self.interest_rate ) / 100

   
=======

    def __str__(self):
        return f"Loan {self.id} for {self.borrower.name}"

    @property
    def total_amount(self):
        return self.amount + self.calculate_total_interest()
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07

    def calculate_total_interest(self):
        """Calculate the total interest for the loan using the flat-rate method."""
        return (self.amount * self.interest_rate) / 100

    def calculate_remaining_balance(self):
        if self.pk is None:
            # For new loans, no payments exist yet
            return self.amount + self.calculate_total_interest()
        total_paid = self.payments.aggregate(Sum('amount'))['amount__sum'] or 0
        return self.amount + self.calculate_total_interest() - total_paid

    def update_status(self):
        if self.calculate_remaining_balance() <= 0:
            self.status = 'paid_off'
        elif self.end_date < date.today():
            self.status = 'past_due'
        else:
            self.status = 'active'
        # Don't save here to avoid recursion; save will be called separately

    def save(self, *args, **kwargs):
        self.update_status()
        super().save(*args, **kwargs)


# Guarantor Table
class Guarantor(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='guarantors', blank=True, null=True)
    names = models.CharField(max_length=255)
    national_id = models.CharField(max_length=10, blank=True)
    phonenumber = models.CharField(max_length=15)
    emails = models.EmailField(blank=True)
   

    def __str__(self):
        return f"Guarantor: {self.name} for Loan {self.loan.id if self.loan else 'N/A'}"


# Collateral Table
class Collateral(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey('Loan', on_delete=models.CASCADE)
    description = models.CharField(max_length=255, blank=True, null=True)
    value = models.DecimalField(max_digits=15, decimal_places=2, blank=True, null=True)
    COLLATERAL_STATUS_CHOICES = [
        ('secured', 'Secured'),
        ('released', 'Released'),
        ('repossessed', 'Repossessed'),
        ('none', 'None')
    ]
    status = models.CharField(max_length=15, choices=COLLATERAL_STATUS_CHOICES, default='none')
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
    ]
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    is_late = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        self.is_late = self.date > self.loan.end_date
        super().save(*args, **kwargs)
<<<<<<< HEAD

        # Update loan status after each payment
        if self.loan.calculate_remaining_balance() <= 0:
            self.loan.status = 'paid_off'
        elif self.loan.status != 'paid_off' and self.is_late:
            self.loan.status = 'past_due'

        # Save the updated loan status
        self.loan.save()
=======
        self.loan.update_status()
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07

    def __str__(self):
        return f"Payment {self.id} for Loan {self.loan.id}"

<<<<<<< HEAD
# Collateral Images Table
class CollateralImage(models.Model):
    id = models.AutoField(primary_key=True)
    collateral = models.ForeignKey(Collateral, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='collateral_images/')

    def __str__(self):
        return f"Image for Collateral {self.collateral.id}"
=======
>>>>>>> f2f9c1d976812b830664e594ea0c0e39c4597d07

# Transaction History Table
class TransactionHistory(models.Model):
    id = models.AutoField(primary_key=True)
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE)
    description = models.TextField()
    date = models.DateField()

    def __str__(self):
        return f"Transaction {self.id} for Loan {self.loan.id}"
