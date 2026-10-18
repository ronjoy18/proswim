import uuid
from decimal import Decimal
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "CLIENT", _("Client")
        COACH = "COACH", _("Coach")
        ADMIN = "ADMIN", _("Administrator")

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CLIENT)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    reset_otp = models.CharField(max_length=6, blank=True, null=True)
    reset_otp_expiry = models.DateTimeField(blank=True, null=True)
    def is_client(self):
        return self.role == self.Role.CLIENT

    def is_coach(self):
        return self.role == self.Role.COACH

    def is_internal(self):
        return self.role == self.Role.ADMIN or self.is_staff or self.is_superuser


class CoachProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="coach_profile")
    license_number = models.CharField(max_length=64, unique=True, blank=True, null=True)
    is_verified = models.BooleanField(default=True)
    profile_picture = models.ImageField(upload_to="coaches/avatars/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.license_number:
            self.license_number = f"COACH-{self.user.username[:6].upper()}-{uuid.uuid4().hex[:4].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Coach: {self.user.get_full_name() or self.user.username}"


class ClientProfile(models.Model):
    class ClientType(models.TextChoices):
        INDIVIDUAL = "INDIVIDUAL", _("Individual")
        CLUB = "CLUB", _("Club Member")

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="client_profile")
    student_name = models.CharField(max_length=150, blank=True, null=True)
    student_age = models.PositiveIntegerField(null=True, blank=True)
    client_type = models.CharField(max_length=20, choices=ClientType.choices, default=ClientType.INDIVIDUAL)
    assigned_coach = models.ForeignKey(CoachProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_clients")
    referral_code = models.CharField(max_length=32, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="referrals")
    promo_credits = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_archived_by_coach = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = f"PRO-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username}"


class Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    duration_minutes = models.PositiveIntegerField(default=60)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} (Ksh{self.price})"


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending Payment")
        PAID = "PAID", _("Paid & Scheduled")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    client = models.ForeignKey(ClientProfile, on_delete=models.PROTECT, related_name="orders")
    activity = models.ManyToManyField(Activity, related_name="orders", blank=True)
    coach = models.ForeignKey(CoachProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="booked_orders")
    custom_test_names = models.TextField(blank=True, default="")
    booking_start = models.DateTimeField(null=True, blank=True)
    booking_end = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    is_paid = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{str(self.id)[:8]} - {self.client.user.username}"

    def calculate_cost(self):
        total = Decimal("0.00")
        for item in self.activity.all():
            total += item.price
        return total


class DailyReport(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    coach = models.ForeignKey(CoachProfile, on_delete=models.CASCADE, related_name="filed_reports")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="daily_reports")
    date = models.DateField(default=timezone.now)
    performance_score = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("Rating scale 1 to 10")
    )
    coach_remarks = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "date")
        ordering = ["-date"]

    def __str__(self):
        return f"Report: {self.client} on {self.date}"


class Announcement(models.Model):
    class Audience(models.TextChoices):
        ALL = "ALL", _("All Members (Global)")
        COACHES_ONLY = "COACHES", _("Coaches Only (Internal)")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, null=True, blank=True)
    content = models.TextField(default="No new announcements")
    audience = models.CharField(max_length=20, choices=Audience.choices, default=Audience.ALL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.audience}] {self.title}"


class ReferralLedger(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    referrer = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="referrals_made")
    referred_client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="referral_source")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True)
    bonus_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("10.00"))
    created_at = models.DateTimeField(auto_now_add=True)


class LessonSchedule(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = "SCHEDULED", _("Scheduled")
        FREE = "FREE", _("Free Slot")

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="lesson_schedule")
    client = models.ForeignKey(ClientProfile, on_delete=models.CASCADE, related_name="lessons")
    coach = models.ForeignKey(CoachProfile, on_delete=models.PROTECT, related_name="scheduled_lessons")
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SCHEDULED)

    class Meta:
        indexes = [
            models.Index(fields=["coach", "start_time", "end_time"]),
        ]