from django.db import models
#from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError
from .base import BaseModel, User



class SubscriptionPlan(BaseModel):
    DURATION_CHOICES = [
        ("MONTHLY", "Monthly"),
        ("YEARLY", "Yearly"),
    ]

    name = models.CharField(max_length=100)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    credits = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.name} ({self.duration})"


class UserSubscription(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()
    remaining_credits = models.PositiveIntegerField()
    auto_renew = models.BooleanField(default=True)
    active = models.BooleanField(default=True)
    revenuecat_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ["-start_date"]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

    def is_active(self):
        return self.active and self.end_date > timezone.now()

    def consume_credit(self, amount=1):
        if not self.is_active():
            raise ValidationError("Subscription not active")
        if self.remaining_credits < amount:
            raise ValidationError("Not enough credits available")
        self.remaining_credits -= amount
        self.save(update_fields=["remaining_credits"])
        return self.remaining_credits

    def handle_autorenew(self):
        """Extend subscription if auto_renew is enabled"""
        if not self.auto_renew:
            return
        now = timezone.now()
        if self.end_date <= now:
            if self.plan.duration == "MONTHLY":
                self.end_date = now + timezone.timedelta(days=30)
            else:
                self.end_date = now + timezone.timedelta(days=365)
            self.remaining_credits = self.plan.credits
            self.save()

    def deactivate(self):
        self.active = False
        self.save(update_fields=["active"])


def get_active_subscription(user):
    """Return the user's active or credit-available subscription"""
    active = (
        UserSubscription.objects.filter(user=user, active=True, end_date__gt=timezone.now())
        .order_by("-end_date")
        .first()
    )
    if active and active.remaining_credits > 0:
        return active
    # fallback
    backup = (
        UserSubscription.objects.filter(user=user, remaining_credits__gt=0)
        .order_by("-end_date")
        .first()
    )
    return backup
