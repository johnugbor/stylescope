# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_CACHE_DIR=/tmp/poetry_cache

# Set the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install poetry
RUN pip install poetry==1.8.3

# Copy poetry files
COPY pyproject.toml poetry.lock* ./

# Configure poetry: Don't create virtual env, install to system python
RUN poetry config virtualenvs.create false \
    && poetry config virtualenvs.in-project false \
    && poetry install --only=main --no-interaction --no-ansi \
    && rm -rf $POETRY_CACHE_DIR

# Copy the rest of the application
COPY . .

# Create a non-root user
RUN addgroup --system app && adduser --system --group app \
    && chown -R app:app /app

# Switch to the non-root user
USER app

# Verify Django and Celery are installed
RUN python -c "import django; print('Django version:', django.VERSION)" \
    && python -c "import celery; print('Celery version:', celery.__version__)"

# Expose port
EXPOSE 8000

# Default command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]