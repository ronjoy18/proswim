from django.db import transaction
from rest_framework import serializers
from .models import (
    Activity,
    Announcement,
    ClientProfile,
    CoachProfile,
    DailyReport,
    Order,
    ReferralLedger,
    User,
    LessonSchedule,
)


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={"input_type": "password"})
    password_confirmation = serializers.CharField(write_only=True, required=False)
    license_number = serializers.CharField(required=False, allow_blank=True, default="")
    referral_code = serializers.CharField(required=False, allow_blank=True, default="")

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "role", "password", "password_confirmation",
            "license_number", "referral_code",
        ]
        extra_kwargs = {
            "first_name": {"required": False, "allow_blank": True},
            "last_name": {"required": False, "allow_blank": True},
            "email": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if "role" in attrs:
            attrs["role"] = str(attrs["role"]).upper()

        password = attrs.get("password")
        password_confirm = attrs.get("password_confirmation")
        if password_confirm and password != password_confirm:
            raise serializers.ValidationError({"password_confirmation": "Passwords do not match."})

        if len(password) < 8:
            raise serializers.ValidationError({"password": "Password must be at least 8 characters long."})

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirmation", None)
        lic_num = validated_data.pop("license_number", "").strip()
        ref_code = validated_data.pop("referral_code", "").strip()
        password = validated_data.pop("password")
        role = validated_data.get("role", User.Role.CLIENT)

        with transaction.atomic():
            user = User(**validated_data)
            user.set_password(password)
            user.save()  # Triggers auto_create_user_profile signal

            # Apply any extra details passed in the form
            if role == User.Role.COACH and lic_num:
                profile = getattr(user, "coach_profile", None)
                if profile:
                    profile.license_number = lic_num
                    profile.save(update_fields=["license_number"])

            elif role == User.Role.CLIENT and ref_code:
                try:
                    referrer = ClientProfile.objects.get(referral_code=ref_code)
                    profile = getattr(user, "client_profile", None)
                    if profile and profile != referrer:
                        profile.referred_by = referrer
                        profile.save(update_fields=["referred_by"])
                except ClientProfile.DoesNotExist:
                    pass

        return user


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["id", "name", "code", "description", "price", "duration_minutes"]


class OrderSerializer(serializers.ModelSerializer):
    activity_name = serializers.SerializerMethodField()
    coach_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id", "client", "client_name", "activity", "activity_name",
            "coach", "coach_name", "booking_start", "booking_end",
            "total_cost", "is_paid", "status", "created_at"
        ]
        read_only_fields = ["id", "total_cost", "is_paid", "status", "coach", "created_at"]

    def get_client_name(self, obj):
        if obj.client and obj.client.user:
            return obj.client.user.get_full_name() or obj.client.user.username
        return "N/A"

    def get_coach_name(self, obj):
        if obj.coach and obj.coach.user:
            return obj.coach.user.get_full_name() or obj.coach.user.username
        return "Unassigned"

    def get_activity_name(self, obj):
        activities = obj.activity.all()
        if activities.exists():
            return ", ".join([a.name for a in activities])
        return obj.custom_test_names or "Swimming Lesson"


class DailyReportSerializer(serializers.ModelSerializer):
    coach_name = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()

    class Meta:
        model = DailyReport
        fields = [
            "id", "client", "coach_name", "date",
            "performance_score", "coach_remarks", "created_at"
        ]
        read_only_fields = ["id", "coach_name", "created_at"]

    def get_coach_name(self, obj):
        if obj.coach and obj.coach.user:
            return obj.coach.user.get_full_name() or obj.coach.user.username
        return "Assigned Coach"

    def get_date(self, obj):
        return str(obj.date) if obj.date else obj.created_at.strftime("%Y-%m-%d")


class AnnouncementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Announcement
        fields = ["id", "title", "content", "audience", "created_at"]


class ReferralLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReferralLedger
        fields = ["id", "referrer", "referred_client", "bonus_amount", "created_at"]

class LessonScheduleSerializer(serializers.ModelSerializer):
    coach_name = serializers.SerializerMethodField()
    client_name = serializers.SerializerMethodField()
    activity_name = serializers.CharField(source="activity.name", read_only=True)

    class Meta:
        model = LessonSchedule
        fields = [
            "id", "order", "client", "client_name", "coach",
            "coach_name", "activity", "activity_name",
            "start_time", "end_time", "status",
        ]

    def get_coach_name(self, obj):
        if obj.coach and obj.coach.user:
            return obj.coach.user.get_full_name() or obj.coach.user.username
        return "Unassigned"

    def get_client_name(self, obj):
        if obj.client and obj.client.user:
            return obj.client.user.get_full_name() or obj.client.user.username
        return "N/A"