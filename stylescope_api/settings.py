import os
from datetime import timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-local-secret-key")
DEBUG = os.getenv("DEBUG", "True") == "True"
#ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1","192.168.1.222").split(",")
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "138.68.16.227",
]

USE_S3 = os.getenv("USE_S3", "False") == "True"
# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "rest_framework",
    "corsheaders",
    "storages",
    "drf_spectacular",
    "rest_framework_simplejwt",
    # Local apps
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "stylescope_api.urls"
# CORRECT
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
WSGI_APPLICATION = "stylescope_api.wsgi.application"

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB"),
        "USER": os.getenv("POSTGRES_USER"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        "HOST": os.getenv("POSTGRES_HOST"),
        "PORT": os.getenv("POSTGRES_PORT"),
    }
}

# Auth
AUTH_USER_MODEL = "api.User"

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# REST Framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 10,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
}

# CORS
CORS_ALLOW_ALL_ORIGINS = True # For development; restrict in production

# Celery Configuration
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

# File Storage (AWS S3 or MinIO)
# if os.getenv("USE_S3") == "True":
#     AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
#     AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
#     AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
#     AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
#     #AWS_S3_ENDPOINT_URL = os.getenv("AWS_S3_ENDPOINT_URL", None) # For MinIO
#     AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
#     AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
#     DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
#     AWS_LOCATION = 'media' # All media files will be stored in a 'media' folder in the bucket
#     MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/{AWS_LOCATION}/'

AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = os.getenv('AWS_S3_REGION_NAME', 'us-east-2')
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')

# AWS_ACCESS_KEY_ID = 'minioadmin'
# AWS_SECRET_ACCESS_KEY = 'minioadmin'
# AWS_S3_REGION_NAME = os.getenv("AWS_S3_REGION_NAME")
# AWS_S3_ENDPOINT_URL = 'http://minio:9000'
# AWS_STORAGE_BUCKET_NAME = os.getenv("AWS_STORAGE_BUCKET_NAME")
#DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
#MEDIA_URL = '/media/'
#MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
DEFAULT_FILE_STORAGE = "storages.backends.s3boto3.S3Boto3Storage"

# Media URL now points to MinIO, not local /media/
#MEDIA_URL = f"{AWS_S3_ENDPOINT_URL}/{AWS_STORAGE_BUCKET_NAME}/"

#EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend' #os.getenv("EMAIL_BACKEND", 'django.core.mail.backends.console.EmailBackend')  # Use console for development
EMAIL_HOST = os.getenv("EMAIL_HOST", 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", 'your-email@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", 'your-app-password')
EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", 'True').lower() == 'true'
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)


GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = os.getenv("GOOGLE_CLOUD_LOCATION")
# Google Gemini API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

SPECTACULAR_SETTINGS = {
    'TITLE': 'Stylescope API',
    'DESCRIPTION': 'API for the Stylescope virtual try-on application.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# If you're using django-storages with MinIO (which you seem to be)
# You might also need:
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'