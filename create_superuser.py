import os
from django.contrib.auth import get_user_model

User = get_user_model()

SUPERUSER_NAME = os.environ.get("DJANGO_SUPERUSER_USERNAME", "dsa-admin")
SUPERUSER_EMAIL = os.environ.get("DJANGO_SUPERUSER_EMAIL", "dsa.insi.platform@gmail.com")
SUPERUSER_PASSWORD = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "admin-dsa-password")

if not User.objects.filter(username=SUPERUSER_NAME).exists():
    print("🚀 Creating superuser...")
    User.objects.create_superuser(
        username=SUPERUSER_NAME,
        email=SUPERUSER_EMAIL,
        password=SUPERUSER_PASSWORD
    )
    print("✔️ Superuser created successfully!")
else:
    print("ℹ️ Superuser already exists. Skipping...")