import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "proswim.settings")
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Production Admin Credentials
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@proswim.com")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "ProswimAdmin2026!")

if not User.objects.filter(username=ADMIN_USERNAME).exists():
    user = User.objects.create_superuser(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password=ADMIN_PASSWORD,
    )
    # Ensure all privileged flags are explicitly active
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    
    # If your custom model defines an INTERNAL role, set it here:
    if hasattr(User.Role, "INTERNAL"):
        user.role = User.Role.INTERNAL
    elif hasattr(User.Role, "ADMIN"):
        user.role = User.Role.ADMIN
        
    user.save()
    print(f"[PROSWIM] Successfully created superuser: {ADMIN_USERNAME}")
else:
    # Update existing user to ensure passwords and flags match
    user = User.objects.get(username=ADMIN_USERNAME)
    user.set_password(ADMIN_PASSWORD)
    user.is_staff = True
    user.is_superuser = True
    user.is_active = True
    if hasattr(User.Role, "INTERNAL"):
        user.role = User.Role.INTERNAL
    user.save()
    print(f"[PROSWIM] Superuser {ADMIN_USERNAME} password and privileges refreshed.")