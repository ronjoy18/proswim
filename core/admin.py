from decimal import Decimal
from django.contrib import admin
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    
    User,
    CoachProfile,
    ClientProfile,
    Activity,
    Order,
    ReferralLedger,
    LessonSchedule,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["username", "email", "role", "is_staff", "is_active", "date_joined"]
    list_filter = ["role", "is_staff", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name", "phone_number"]


@admin.register(CoachProfile)
class CoachProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user_name",
        "created_at",
    ]
    list_filter = [ "user__is_active"]
    search_fields = [
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "license_number",
        
    ]
    actions = ["verify_coaches_and_notify"]

    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = "Coach Name"

    @admin.action(description="Verify selected coaches and send confirmation email")
    def verify_coaches_and_notify(self, request, queryset):
        for coach in queryset:
            coach.save()
            send_mail(
                subject="coach profile verified",
                message=(
                    f"Dear coach {coach.user.last_name},\n\n"
                    f"Our administrative review team has verified your credentials and license.\n"
                    f"Your profile is now active.\n\n"
                    f"proswimGlobal Review Board"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[coach.user.email],
                fail_silently=True,
            )
        self.message_user(request, f"{queryset.count()} coaches verified and notified.")


@admin.register(ClientProfile)
class ClientProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "client_type", "promo_credits", "created_at"]
    list_filter = ["client_type", "is_archived_by_coach", "assigned_coach"]
    search_fields = ["user__username", "user__first_name", "user__last_name", "user__email", "referral_code"]


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "price", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]




@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    # 1. Add your custom readable columns to list_display
    list_display = [
        "short_id",
        "client_name",
        "booked_activities",
        "assigned_coach_name",
        "status",
        "total_cost",
        "is_paid",
        "created_at",
    ]

    list_filter = ["status", "is_paid", "created_at"]
    search_fields = [
        "id",
        "client__user__username",
        "client__user__first_name",
        "client__user__last_name",
        "custom_test_names",
    ]

    # Clean display for the Order ID (first 8 chars)
    def short_id(self, obj):
        return f"#{str(obj.id)[:8]}"
    short_id.short_description = "Order ID"

    # Display the client's actual name instead of a raw profile object
    def client_name(self, obj):
        if obj.client and obj.client.user:
            return obj.client.user.get_full_name() or obj.client.user.username
        return "N/A"
    client_name.short_description = "Client"

    # Display the booked activity (Handles both ManyToMany and ForeignKey setups safely)
    def booked_activities(self, obj):
        # If activity is a ManyToMany relationship
        if hasattr(obj.activity, "all"):
            names = [a.name for a in obj.activity.all()]
            if names:
                return ", ".join(names)
        # If activity is a direct ForeignKey
        elif obj.activity:
            return obj.activity.name
        
        # Fallback to custom notes if no catalog activity was selected
        if hasattr(obj, "custom_test_names") and obj.custom_test_names:
            return f"Custom: {obj.custom_test_names[:25]}..."
        return "No Activity Assigned"
    booked_activities.short_description = "Booked Activity / Lesson"

    # Display the assigned coach's name
    def assigned_coach_name(self, obj):
        coach_obj = getattr(obj, "coach", None) or getattr(obj, "coachingcoach", None)
        if coach_obj and coach_obj.user:
            return coach_obj.user.get_full_name() or coach_obj.user.username
        return "Unassigned"
    assigned_coach_name.short_description = "Coach"

@admin.register(ReferralLedger)
class ReferralLedgerAdmin(admin.ModelAdmin):
    list_display = ["referrer", "referred_client", "created_at"]
    search_fields = ["referrer__user__username", "referred_client__user__username"]

@admin.register(LessonSchedule)
class LessonScheduleAdmin(admin.ModelAdmin):
    list_display = ["coach", "client", "activity", "start_time", "end_time", "status"]
    list_filter = ["start_time", "end_time", "status"]
    search_fields = ["lesson_name", "assigned_coach__user__username"]    
