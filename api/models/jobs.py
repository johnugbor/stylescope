from django.db import models
from .base import BaseModel, User
from .pages import Page, PageItem

class EditJob(BaseModel):
    class JobType(models.TextChoices):
        SINGLE = "SINGLE", "Single"
        PAGE = "PAGE", "Page"
        ALL = "ALL", "All Pages"

    class JobStatus(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        RUNNING = "RUNNING", "Running"
        DONE = "DONE", "Done"
        FAILED = "FAILED", "Failed"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="edit_jobs")
    job_type = models.CharField(max_length=10, choices=JobType.choices)
    status = models.CharField(max_length=10, choices=JobStatus.choices, default=JobStatus.QUEUED)
    
    # Can link to a single item, a whole page, or be null for "all pages" job
    page_item = models.ForeignKey(PageItem, on_delete=models.CASCADE, null=True, blank=True)
    page = models.ForeignKey(Page, on_delete=models.CASCADE, null=True, blank=True)
    
    result_image_url = models.CharField(max_length=1024, blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Job {self.id} - {self.status}"