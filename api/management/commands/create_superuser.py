import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Create a superuser from environment variables if none exists"

    def handle(self, *args, **options):
        # Pull values from environment with fallbacks
        username = os.environ.get("SUPERUSER_USERNAME", "admin")
        email = os.environ.get("SUPERUSER_EMAIL", "admin@stylescope.com")
        password = os.environ.get("SUPERUSER_PASSWORD") or os.environ.get("ADMIN_PASSWORD", "admin123")

        # If your custom User model has no username field, ignore it
        has_username_field = "username" in [f.name for f in User._meta.get_fields()]

        # Skip if a superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.WARNING("Superuser already exists. Skipping creation."))
            return

        # Check for existing user conflicts
        if has_username_field and User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists but is not a superuser.'))
            return

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f'User with email "{email}" already exists but is not a superuser.'))
            return

        try:
            # Create superuser depending on user model definition
            if has_username_field:
                user = User.objects.create_superuser(username=username, email=email, password=password)
            else:
                user = User.objects.create_superuser(email=email, password=password)

            self.stdout.write(self.style.SUCCESS(f'Successfully created superuser "{user.email}"'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error creating superuser: {e}"))
