from django.db import models
from .base import BaseModel, User
from ..utils import get_minio_url

class HumanModel(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="human_models")
    name = models.CharField(max_length=255)
    image_url = models.CharField(max_length=1024)  # stores only the object key
    is_selected = models.BooleanField(default=False)
    consent_given = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    @property
    def full_image_url(self):
        return get_minio_url(self.image_url, for_backend=False)

class ClothingItem(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clothing_items")
    name = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=1024)  # stores only the object key
    display_image_url = models.CharField(max_length=1024, blank=True)  # stores the generated try-on image object key

    def __str__(self):
        return self.name or str(self.id)

    @property
    def full_image_url(self):
        return get_minio_url(self.image_url, for_backend=False)