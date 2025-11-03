from django.db import models
from .base import BaseModel, User

class Support(BaseModel):
    STATUS_CHOICES = [
        ('OPEN', 'Open'),
        ('CLOSED', 'Closed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_tickets")
    subject = models.CharField(max_length=255)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='OPEN')
    closed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="closed_support_tickets")
    closed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Support #{self.id} - {self.subject}"
    
    def close(self, closed_by_user):
        """Close the support ticket"""
        from django.utils import timezone
        self.status = 'CLOSED'
        self.closed_by = closed_by_user
        self.closed_at = timezone.now()
        self.save()

class SupportMessage(BaseModel):
    MESSAGE_TYPE_CHOICES = [
        ('USER', 'User Message'),
        ('ADMIN', 'Admin Message'),
    ]
    
    support = models.ForeignKey(Support, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="support_messages")
    message = models.TextField()
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Message from {self.sender.email} in Support #{self.support.id}"
    
    def save(self, *args, **kwargs):
        # Automatically set message_type based on sender's staff status
        if self.sender.is_staff:
            self.message_type = 'ADMIN'
        else:
            self.message_type = 'USER'
        super().save(*args, **kwargs)