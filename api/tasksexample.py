import google.generativeai as genai
import requests
import time
from io import BytesIO
import logging
from PIL import Image
from django.conf import settings
from django.utils import timezone
from celery import shared_task
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import EditJob, HumanModel, PageItem
logger = logging.getLogger(__name__)
# Configure the Gemini client
genai.configure(api_key=settings.GEMINI_API_KEY)

def download_image(url):
    """Downloads an image from a URL into a PIL Image object."""
    response = requests.get(url)
    response.raise_for_status()
    return Image.open(BytesIO(response.content))

def upload_image_to_storage(image_bytes, filename):
    """Uploads image bytes to the default file storage (S3/MinIO)."""

    path = default_storage.save(f"generated/{filename}", ContentFile(image_bytes))
    return default_storage.url(path)

@shared_task(bind=True, max_retries=3)
def process_single_edit(self, page_item_id, human_model_image_url):
    """Processes a single clothing item against a human model."""
    try:
        logger.info(f"Starting process_single_edit for page_item_id={page_item_id}, human_model_image_url={human_model_image_url}")
        page_item = PageItem.objects.select_related('clothing_item').get(id=page_item_id)
        model_image_url = human_model_image_url  # Already a complete S3 URL
        clothing_image_url = page_item.clothing_item.image_url  # Already a complete S3 URL
        logger.info(f"Model image URL: {model_image_url}")
        logger.info(f"Clothing image URL: {clothing_image_url}")
        
        model_image = download_image(model_image_url)
        clothing_image = download_image(clothing_image_url)

        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        prompt = """
        You are an expert virtual tailor. Your task is to composite the provided clothing image onto the human model image.
        - Preserve the person's pose, face, skin tone, and the original background.
        - Fit the clothing realistically to the person's body contours.
        - Maintain the original lighting of the human model image.
        - Output a high-quality PNG image.
        """

        response = model.generate_content([
            prompt,
            "Human model:", model_image,
            "Clothing to apply:", clothing_image
        ])
        logger.info("Received response from generative model.")
        # Add these lines to inspect the response part
        logger.info(f"Response parts[0] dir: {dir(response.parts[0])}")
        logger.info(f"Response parts[0]: {response.parts[0]}")

        # Assuming the first part of the response is the image
        img_bytes = response.parts[0].blob.data
        logger.info(f"Generated image bytes, size: {len(img_bytes)}")
        
        # Generate a unique filename
        result_filename = f"{page_item.id}_{int(time.time())}.png"
        result_url = upload_image_to_storage(img_bytes, result_filename)
        logger.info(f"Uploaded generated image to storage: {result_url}")
        return result_url
    
    except Exception as exc:
        # Exponential backoff is handled by Celery's retry mechanism
        logger.error(f"Error processing single edit for page_item_id={page_item_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)

@shared_task
def process_image_edit(job_id):
    """Main task dispatcher based on job type."""
    try:
        job = EditJob.objects.get(id=job_id)
        job.status = EditJob.JobStatus.RUNNING
        job.save()

        user = job.user
        # selected_model = HumanModel.objects.get(user=user, is_selected=True)
        # human_model_url = selected_model.image_url
        selected_model = HumanModel.objects.get(user=user, is_selected=True)
        human_model_url = selected_model.image_url         
        items_to_process = []
        if job.job_type == EditJob.JobType.SINGLE:
            items_to_process.append(job.page_item)
        elif job.job_type == EditJob.JobType.PAGE:
            items_to_process.extend(job.page.items.all())
        elif job.job_type == EditJob.JobType.ALL:
            all_pages = user.pages.prefetch_related('items').all()
            for page in all_pages:
                items_to_process.extend(page.items.all())

        if not items_to_process:
            raise ValueError("No items found to process for this job.")

        # For simplicity, we process serially. In a larger system, you'd use a Celery group.
        # For a single item job, the result is stored on the main job object.
        # For batch jobs, you might create child jobs or store results differently.
        
        if job.job_type == EditJob.JobType.SINGLE and items_to_process:
            result_url = process_single_edit(items_to_process[0].id, human_model_url)
            job.result_image_url = result_url
        else:
            # For batch jobs, this example logs completion but doesn't store individual images.
            # A better approach would be to create sub-tasks and link results.
            for item in items_to_process:
                # This could be a Celery group for parallel execution
                process_single_edit.delay(item.id, human_model_url)
            # We'll mark the main job as done, assuming sub-tasks will run.
            # A more robust system would monitor the sub-tasks.

        job.status = EditJob.JobStatus.DONE
        job.completed_at = timezone.now()
        job.save()

    except HumanModel.DoesNotExist:
        job.status = EditJob.JobStatus.FAILED
        job.error_message = "No human model selected for this user."
        job.save()
    except Exception as e:
        job.status = EditJob.JobStatus.FAILED
        job.error_message = str(e)
        job.save()