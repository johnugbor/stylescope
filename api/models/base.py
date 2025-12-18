import uuid
import random
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.forms import ValidationError
from django.utils import timezone
from datetime import timedelta

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    #id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = None  # Remove username field
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)  # Optional during registration
    last_name = models.CharField(max_length=30, blank=True)   # Optional during registration
    is_email_verified = models.BooleanField(default=False)  # Email verification status
    
    # Christmas-specific fields
    is_christmas_user = models.BooleanField(default=False)  # Whether user has Christmas features enabled
    christmas_credits = models.PositiveIntegerField(default=0)  # Available credits for Christmas try-ons
    christmas_active = models.BooleanField(default=True)  # Whether Christmas account is active
    
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    
    objects = UserManager()
    
    # Christmas-related methods
    def has_christmas_credits(self, amount=1):
        """Check if user has enough Christmas credits"""
        return self.christmas_credits >= amount
    
    def consume_christmas_credits(self, amount=1):
        """Consume Christmas credits for try-on"""
        if not self.has_christmas_credits(amount):
            raise ValidationError(f"Insufficient credits. You need {amount} credits.")
        self.christmas_credits -= amount
        self.save(update_fields=['christmas_credits'])
        return self.christmas_credits
    
    def add_christmas_credits(self, amount):
        """Add Christmas credits to user account"""
        self.christmas_credits += amount
        self.save(update_fields=['christmas_credits'])
        return self.christmas_credits

class BaseModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class PasswordResetToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="password_reset_tokens")
    code = models.CharField(max_length=4)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            # Token expires in 15 minutes
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a random 4-digit code"""
        return str(random.randint(1000, 9999))
    
    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    @classmethod
    def create_for_user(cls, user):
        """Create a new password reset token for user and invalidate old ones"""
        # Invalidate any existing unused tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new token
        return cls.objects.create(user=user)
    
    def __str__(self):
        return f"Reset token {self.code} for {self.user.email}"


class EmailVerificationToken(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="email_verification_tokens")
    code = models.CharField(max_length=4)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_code()
        if not self.expires_at:
            # Token expires in 30 minutes (longer than password reset for convenience)
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    @staticmethod
    def generate_code():
        """Generate a random 4-digit code"""
        return str(random.randint(1000, 9999))
    
    def is_valid(self):
        """Check if token is still valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.save(update_fields=['is_used'])
    
    @classmethod
    def create_for_user(cls, user):
        """Create a new email verification token for user and invalidate old ones"""
        # Invalidate any existing unused tokens
        cls.objects.filter(user=user, is_used=False).update(is_used=True)
        
        # Create new token
        return cls.objects.create(user=user)
    
    def __str__(self):
        return f"Email verification token for {self.user.email}"