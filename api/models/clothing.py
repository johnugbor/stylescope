from django.db import models
from django.conf import settings
from .base import BaseModel, User

class HumanModel(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="human_models")
    name = models.CharField(max_length=255)
    image_url = models.CharField(max_length=1024)  # stores complete S3 URL
    is_selected = models.BooleanField(default=False)
    consent_given = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def full_image_url(self):
        return self.image_url

class ClothingItem(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clothing_items")
    name = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=1024)  # stores complete S3 URL
    display_image_url = models.CharField(max_length=1024, blank=True)  # stores the generated try-on image complete S3 URL

    def __str__(self):
        return self.name or str(self.id)

    @property
    def full_image_url(self):
        return self.image_url