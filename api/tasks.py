import requests
import time
import os
import logging
from io import BytesIO
from PIL import Image as PILImage, ImageDraw, ImageFont

import google.generativeai as genai  # ✅ Gemini API
from django.conf import settings
from django.utils import timezone
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

from celery import shared_task, group

from .models import EditJob, HumanModel, PageItem

logger = logging.getLogger(__name__)

# -------------------- INIT GEMINI --------------------
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


# -------------------- HELPERS --------------------

def download_image_bytes(url):
    """Download an image and return raw bytes."""
    response = requests.get(url)
    response.raise_for_status()
    return response.content


def upload_image_to_storage(image_bytes, filename):
    """Upload image bytes to MinIO/S3 via default_storage."""
    path = default_storage.save(f"generated/{filename}", ContentFile(image_bytes))
    return default_storage.url(path)


def combine_images_side_by_side(img1_bytes, img2_bytes, max_width=768, label_left="ME", label_right="CLOTH"):
    """
    Combine two images horizontally with a vertical dotted red separator line and optional labels.
    """
    img1 = PILImage.open(BytesIO(img1_bytes)).convert("RGB")
    img2 = PILImage.open(BytesIO(img2_bytes)).convert("RGB")

    # scale down if too wide
    scale_factor = min(1.0, max_width / float(img1.width + img2.width))
    if scale_factor < 1.0:
        new_h = int(img1.height * scale_factor)
        new_w1 = int(img1.width * scale_factor)
        new_w2 = int(img2.width * scale_factor)
        img1 = img1.resize((new_w1, new_h), PILImage.LANCZOS)
        img2 = img2.resize((new_w2, new_h), PILImage.LANCZOS)

    max_height = max(img1.height, img2.height) + 50  # extra space for labels
    total_width = img1.width + img2.width + 5  # +5px separator

    combined = PILImage.new("RGB", (total_width, max_height), (255, 255, 255))
    combined.paste(img1, (0, 50))  # push down for label space
    combined.paste(img2, (img1.width + 5, 50))

    draw = ImageDraw.Draw(combined)

    # draw dotted vertical separator line in RED
    x = img1.width + 2
    dot_length = 10
    gap = 10
    for y in range(0, max_height, dot_length + gap):
        draw.line([(x, y), (x, min(y + dot_length, max_height))], fill="red", width=3)

    # load font
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()

    # add labels centered above each image
    left_x = img1.width // 2 - 20
    right_x = img1.width + 5 + (img2.width // 2) - 40
    draw.text((left_x, 10), label_left, fill="black", font=font)
    draw.text((right_x, 10), label_right, fill="black", font=font)

    buf = BytesIO()
    combined.save(buf, format="PNG")
    return buf.getvalue()

def crop_right_half(img_bytes):
    """Crop the generated image to keep only the RIGHT half."""
    img = PILImage.open(BytesIO(img_bytes)).convert("RGB")
    width, height = img.size
    right_half = img.crop((width // 2, 0, width, height))  # (x1, y1, x2, y2)

    buf = BytesIO()
    right_half.save(buf, format="PNG")
    return buf.getvalue()
# -------------------- TASKS --------------------

@shared_task(bind=True, max_retries=3)
def process_single_edit(self, page_item_id, human_model_image_url):
    """Processes a single clothing item against a human model using Gemini API."""
    try:
        logger.info(f"Starting process_single_edit for page_item_id={page_item_id}")
        page_item = PageItem.objects.select_related("clothing_item").get(id=page_item_id)

        model_image_url = human_model_image_url  # Already a complete S3 URL
        clothing_image_url = page_item.clothing_item.image_url  # Already a complete S3 URL
        logger.info(f"Model image URL: {model_image_url}")
        logger.info(f"Clothing image URL: {clothing_image_url}")

        # download both images
        model_image_bytes = download_image_bytes(model_image_url)
        clothing_image_bytes = download_image_bytes(clothing_image_url)

        # convert to PIL Images for Gemini API
        model_image = PILImage.open(BytesIO(model_image_bytes))
        clothing_image = PILImage.open(BytesIO(clothing_image_bytes))

        # Simple, clear prompt for virtual try-on
        prompt = """
        You are a virtual fashion try-on AI. Your task is to create a realistic image of the person wearing the provided clothing item.

        Instructions:
        1. Take the clothing item from the second image
        2. Realistically place it on the person from the first image
        3. Preserve the person's face, body shape, pose, and background
        4. Make the clothing fit naturally with proper draping and shadows
        5. Ensure the final result looks photorealistic
        6. Return ONLY the person wearing the new clothing - no split screens or multiple images

        The output should be a single image of the person wearing the clothing item.
        """

        logger.info("Sending request to Gemini 2.5 Flash Image API...")

        # ✅ Correct format for multiple images with google.generativeai library
        model = genai.GenerativeModel("gemini-2.5-flash-image-preview")
        response = model.generate_content([
            "Person to dress:",
            model_image,
            "Clothing item to apply:",
            clothing_image,
            prompt
        ])

        logger.info("Received response from Gemini model.")

        # extract generated image
        img_bytes = None
        if response.candidates:
            for part in response.candidates[0].content.parts:
                if part.inline_data:
                    img_bytes = part.inline_data.data
                    break

        if not img_bytes:
            logger.error(f"No image generated. Response: {response}")
            raise Exception("Model did not return an image.")

        logger.info(f"Generated image bytes, size: {len(img_bytes)}")

        # save result directly (no cropping needed)
        result_filename = f"{page_item.id}_{int(time.time())}.png"
        result_url = upload_image_to_storage(img_bytes, result_filename)
        logger.info(f"Uploaded generated image: {result_url}")

        return result_url

    except Exception as exc:
        logger.error(f"Error processing single edit for page_item_id={page_item_id}: {exc}")
        raise self.retry(exc=exc, countdown=60 * 2 ** self.request.retries)


@shared_task
def process_image_edit(job_id):
    """Main task dispatcher."""
    try:
        job = EditJob.objects.get(id=job_id)
        job.status = EditJob.JobStatus.RUNNING
        job.save()

        user = job.user
        selected_model = HumanModel.objects.get(user=user, is_selected=True)
        human_model_url = selected_model.image_url

        items_to_process = []
        if job.job_type == EditJob.JobType.SINGLE:
            items_to_process.append(job.page_item)
        elif job.job_type == EditJob.JobType.PAGE:
            items_to_process.extend(job.page.items.all())
        elif job.job_type == EditJob.JobType.ALL:
            for page in user.pages.prefetch_related("items").all():
                items_to_process.extend(page.items.all())

        if not items_to_process:
            raise ValueError("No items found to process for this job.")

        if job.job_type == EditJob.JobType.SINGLE and items_to_process:
            result_url = process_single_edit(items_to_process[0].id, human_model_url)
            job.result_image_url = result_url
        else:
            job_group = group(
                process_single_edit.s(item.id, human_model_url) for item in items_to_process
            )
            job_group.apply_async()

        job.status = EditJob.JobStatus.DONE
        job.completed_at = timezone.now()
        job.save()

    except HumanModel.DoesNotExist:
        job.status = EditJob.JobStatus.FAILED
        job.error_message = "No human model selected for this user."
        job.save()
    except Exception as e:
        logger.error(f"Error in process_image_edit: {e}")
        job.status = EditJob.JobStatus.FAILED
        job.error_message = str(e)
        job.save()
