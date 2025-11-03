from django.db import models
from .base import BaseModel, User
from .clothing import ClothingItem

class Page(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pages")
    title = models.CharField(max_length=255)
    page = models.PositiveIntegerField()  # Page number for filtering and identification
    order_index = models.PositiveIntegerField()

    class Meta:
        ordering = ["order_index"]
        unique_together = ('user', 'page')  # Ensure unique page numbers per user

    def __str__(self):
        return self.title

class PageItem(BaseModel):
    page = models.ForeignKey(Page, on_delete=models.CASCADE, related_name="items")
    clothing_item = models.ForeignKey(ClothingItem, on_delete=models.CASCADE)
    order_index = models.PositiveIntegerField()

    class Meta:
        ordering = ["order_index"]
        unique_together = ('page', 'clothing_item')