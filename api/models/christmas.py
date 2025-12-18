from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ValidationError
from django.utils import timezone
from .base import BaseModel
import random
import string


class ChristmasCloth(BaseModel):
    """Christmas clothing items uploaded by admin"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    image_url = models.CharField(max_length=1024)  # S3 URL
    category = models.CharField(max_length=100, blank=True)  # e.g., "Sweater", "Costume", "Accessories"
    is_active = models.BooleanField(default=True)
    order_index = models.PositiveIntegerField(default=0)  # For sorting display
    
    class Meta:
        ordering = ['order_index', 'name']
    
    def __str__(self):
        return self.name


class MyPicture(BaseModel):
    """User's uploaded pictures for try-on"""
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="christmas_my_pictures", null=True, blank=True)
    image_url = models.CharField(max_length=1024)  # S3 URL
    is_primary = models.BooleanField(default=False)  # User's default picture
    session_id = models.CharField(max_length=100, blank=True)  # For non-logged in users
    
    def __str__(self):
        return f"Picture {self.id} - {self.user.email if self.user else self.session_id}"


class CreditBundle(BaseModel):
    """Predefined credit bundles for purchase"""
    name = models.CharField(max_length=100)  # e.g., "Starter Pack", "Holiday Bundle"
    credits = models.PositiveIntegerField()  # Number of credits
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Price in USD
    discount_percentage = models.PositiveIntegerField(default=0)  # Discount compared to single try-on
    is_active = models.BooleanField(default=True)
    order_index = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order_index', 'price']
    
    def __str__(self):
        return f"{self.name} - {self.credits} credits (${self.price})"


class PaymentCode(BaseModel):
    """Payment codes for verification"""
    code = models.CharField(max_length=50, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    credits = models.PositiveIntegerField(default=1)  # Credits this payment grants
    is_used = models.BooleanField(default=False)
    used_by = models.ForeignKey('User', on_delete=models.SET_NULL, null=True, blank=True, related_name="used_christmas_payment_codes")
    used_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    session_id = models.CharField(max_length=100, blank=True)  # For non-logged in users
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Payment Code {self.code} - {self.credits} credits"
    
    @classmethod
    def generate_code(cls, length=12):
        """Generate a unique payment code"""
        characters = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choice(characters) for _ in range(length))
            if not cls.objects.filter(code=code).exists():
                return code
    
    def is_valid(self):
        """Check if payment code is valid"""
        if self.is_used:
            return False
        if self.expires_at < timezone.now():
            return False
        return True
    
    def use(self, user=None, session_id=None):
        """Mark payment code as used"""
        if not self.is_valid():
            raise ValidationError("Payment code is invalid or already used.")
        
        self.is_used = True
        self.used_by = user
        self.used_at = timezone.now()
        if session_id:
            self.session_id = session_id
        self.save()
        
        # Add credits to user if logged in
        if user:
            user.add_credits(self.credits)
        
        return self.credits


class PaystackTransaction(BaseModel):
    """Track Paystack payment transactions"""
    
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="christmas_paystack_transactions", null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True)  # For non-logged in users
    reference = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount in Naira
    status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    paystack_reference = models.CharField(max_length=100, blank=True)
    payment_code = models.OneToOneField(PaymentCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="christmas_paystack_transaction")
    
    def __str__(self):
        return f"Paystack Transaction {self.reference} - {self.status}"


class ChristmasTryOn(BaseModel):
    """Try-on jobs for Christmas clothes"""
    
    class JobStatus(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="christmas_try_ons", null=True, blank=True)
    session_id = models.CharField(max_length=100, blank=True)  # For non-logged in users
    christmas_cloth = models.ForeignKey(ChristmasCloth, on_delete=models.CASCADE)
    my_picture = models.ForeignKey(MyPicture, on_delete=models.CASCADE)
    
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.QUEUED)
    result_image_url = models.CharField(max_length=1024, blank=True)  # Generated try-on image
    error_message = models.TextField(blank=True)
    
    payment_code = models.ForeignKey(PaymentCode, on_delete=models.SET_NULL, null=True, blank=True, related_name="christmas_try_ons")
    was_paid = models.BooleanField(default=False)  # Whether this was a paid try-on
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        user_info = self.user.email if self.user else f"Session {self.session_id}"
        return f"Try-on {self.id} - {user_info} - {self.status}"


class CreditTransaction(BaseModel):
    """Track all credit transactions for auditing"""
    
    class TransactionType(models.TextChoices):
        PURCHASE = "PURCHASE", "Purchase"
        CONSUME = "CONSUME", "Consume"
        REFUND = "REFUND", "Refund"
        ADMIN_GRANT = "ADMIN_GRANT", "Admin Grant"
    
    user = models.ForeignKey('User', on_delete=models.CASCADE, related_name="christmas_credit_transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.IntegerField()  # Positive for additions, negative for consumption
    balance_after = models.PositiveIntegerField()  # User's balance after transaction
    
    payment_code = models.ForeignKey(PaymentCode, on_delete=models.SET_NULL, null=True, blank=True)
    credit_bundle = models.ForeignKey(CreditBundle, on_delete=models.SET_NULL, null=True, blank=True)
    try_on = models.ForeignKey(ChristmasTryOn, on_delete=models.SET_NULL, null=True, blank=True)
    
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.transaction_type} - {self.amount} credits"
