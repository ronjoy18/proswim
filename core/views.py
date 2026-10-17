import os
from django.contrib import messages
from datetime import timedelta
from decimal import Decimal
import random
from datetime import timedelta
from django.utils import timezone
from django.contrib import messages
from django.core.mail import send_mail
from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from rest_framework import generics, permissions, status, views
from rest_framework.response import Response

from .models import (
    Activity,
    Announcement,
    ClientProfile,
    CoachProfile,
    DailyReport,
    LessonSchedule,
    Order,
    User,
)
from .permissions import DocumentAccessPermission, IsClientOwner, IsCoachOwner, IsInternalStaff
from .serializers import (
    ActivitySerializer,
    AnnouncementSerializer,
    DailyReportSerializer,
    OrderSerializer,
    UserRegistrationSerializer,
    LessonScheduleSerializer,
)




def forgot_password_view(request):

    User = get_user_model()
    
    if request.method == "POST":
        email = request.POST.get("email", "").strip()
        user = User.objects.filter(email=email).first()

        if user:
            # 1. Generate 6-digit random code
            otp = f"{random.randint(100000, 999999)}"
            user.reset_otp = otp
            user.reset_otp_expiry = timezone.now() + timedelta(minutes=10) # Valid 10 mins
            user.save()

            # 2. Email the OTP
            send_mail(
                subject="Your Proswim Password Reset OTP",
                message=f"Your password reset code is: {otp}\nIt expires in 10 minutes.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            # Store user ID or email in session for the verification step
            request.session["reset_email"] = user.email
            messages.success(request, "An OTP has been sent to your email.")
            return redirect("verify_otp")
        else:
            messages.error(request, "No account found with this email.")

    return render(request, "core/forgot_password.html")


def verify_otp_view(request):
    email = request.session.get("reset_email")
    if not email:
        return redirect("forgot_password")

    if request.method == "POST":
        otp_entered = request.POST.get("otp", "").strip()
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        user = User.objects.filter(email=email).first()

        if not user or user.reset_otp != otp_entered:
            messages.error(request, "Invalid OTP code.")
        elif timezone.now() > user.reset_otp_expiry:
            messages.error(request, "OTP has expired. Please request a new one.")
        elif new_password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif len(new_password) < 8:
            messages.error(request, "Password must be at least 8 characters long.")
        else:
            # Valid OTP: Set new password and clean up OTP
            user.set_password(new_password)
            user.reset_otp = None
            user.reset_otp_expiry = None
            user.save()

            del request.session["reset_email"]
            messages.success(request, "Password reset successful! Please log in.")
            return redirect("login")

    return render(request, "core/verify_otp.html")

def index_view(request):
    activities = Activity.objects.filter(is_active=True)
    return render(request, "index.html", {"activities": activities})


def auth_view(request):
    return render(request, "auth.html")


def internal_login_view(request):
    return render(request, "internal_login.html")


def dashboard_dispatcher(request):
    if not request.user.is_authenticated:
        return redirect("auth-page")
    if request.user.role == User.Role.CLIENT:
        return render(request, "client_dashboard.html")
    if request.user.role == User.Role.COACH:
        return render(request, "coach_dashboard.html")
    if request.user.is_internal():
        return redirect("/admin/")
    return redirect("index-page")


class PublicRegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class SessionLoginAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if not user:
            
            return Response({"detail": "Invalid authentication credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if request.data.get("portal") == "public" and user.is_internal():
            return Response({"detail": "Staff/Admin users must log in through the management portal."}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)
        return Response({
            "message": "Authentication successful.",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role,
                "full_name": user.get_full_name()
            }
        })


class InternalSecureLoginAPIView(views.APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if not user or not user.is_internal():
            return Response({"detail": "Access Denied: Non-privileged authentication source."}, status=status.HTTP_403_FORBIDDEN)

        login(request, user)
        return Response({"message": "Staff/Admin session successfully anchored."})


class SessionLogoutAPIView(views.APIView):
    def post(self, request):
        logout(request)
        return Response({"message": "Session invalidated."})


class PublicCatalogAPIView(generics.ListAPIView):
    queryset = Activity.objects.filter(is_active=True)
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]


class OrderListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = OrderSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Order.objects.none()
        if user.is_internal():
            return Order.objects.all().select_related("client__user", "coach__user")
        if user.is_client():
            return Order.objects.filter(client__user=user)
        if user.is_coach():
            return Order.objects.filter(coach__user=user)
        return Order.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_authenticated or not user.is_client():
            return Response({"detail": "Only registered clients can place lesson orders."}, status=status.HTTP_403_FORBIDDEN)

        client, _ = ClientProfile.objects.get_or_create(user=user)
        activities_ids = request.data.get("activities", [])
        custom_notes = request.data.get("custom_test_names", "").strip()

        order = Order.objects.create(
            client=client,
            custom_test_names=custom_notes,
            coach=client.assigned_coach
        )

        if activities_ids:
            activities = Activity.objects.filter(id__in=activities_ids, is_active=True)
            order.activity.set(activities)
            order.total_cost = order.calculate_cost()
            order.save(update_fields=["total_cost"])

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CoachMyclientsAPIView(views.APIView):
    permission_classes = [IsCoachOwner]

    def get(self, request):
        coach, _ = CoachProfile.objects.get_or_create(user=request.user)
        
        # Include both permanently assigned clients AND clients with lessons scheduled with this coach
        from django.db.models import Q
        clients = ClientProfile.objects.filter(
            Q(assigned_coach=coach) | Q(lessons__coach=coach),
            is_archived_by_coach=False
        ).distinct().select_related("user")

        data = []
        for c in clients:
            total_lessons = c.lessons.filter(coach=coach).count() if hasattr(c, "lessons") else 0
            data.append({
                "id": str(c.id),
                "full_name": c.user.get_full_name() or c.user.username,
                "username": c.user.username,
                "email": c.user.email,
                "phone": getattr(c.user, "phone_number", None) or "Not Provided",
                "registered_on": c.created_at.strftime("%b %d, %Y") if hasattr(c, "created_at") else "N/A",
                "total_orders": total_lessons,
            })

        return Response(data)


class CoachClientDetailAPIView(views.APIView):
    permission_classes = [IsCoachOwner]

    def delete(self, request, client_id):
        client = get_object_or_404(
            ClientProfile,
            id=client_id,
            assigned_coach=request.user.coach_profile
        )
        client.is_archived_by_coach = True
        client.save(update_fields=["is_archived_by_coach"])
        return Response({"message": "Client unlinked from active roster."})


class ClientProfileDetailAPIView(views.APIView):
    permission_classes = [IsClientOwner]

    def get(self, request):
        p, _ = ClientProfile.objects.get_or_create(user=request.user)
        base_url = getattr(settings, 'BASE_URL', 'http://127.0.0.1:8000')
        return Response({
            "referral_code": p.referral_code,
            "referral_link": f"{base_url}/auth/?ref={p.referral_code}",
            "promo_credits": str(p.promo_credits),
            "client_type": p.client_type
        })


class SimulatePaymentAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, order_id):
        order = get_object_or_404(Order, id=order_id)
        if request.user.is_client() and order.client.user != request.user:
            return Response({"detail": "Unauthorized"}, status=403)

        if order.is_paid:
            return Response({"message": "Order is already paid."})

        order.is_paid = True
        order.status = Order.Status.PAID
        order.save()

        return Response({"message": "Payment simulation successful.", "status": "PAID"})


def payment_checkout_view(request, order_id):
    if not request.user.is_authenticated:
        return redirect("auth-page")
    order = get_object_or_404(Order, id=order_id)

    if request.user.is_staff or request.user.is_superuser or request.user.is_internal():
        return render(request, "payment_checkout.html", {"order": order})

    if request.user.is_client():
        if order.client.user != request.user:
            raise Http404("Unauthorized order reference.")
        return render(request, "payment_checkout.html", {"order": order})

    raise Http404("Unauthorized order reference.")


class CoachDailyReportCreateAPIView(generics.CreateAPIView):
    serializer_class = DailyReportSerializer
    permission_classes = [IsCoachOwner]

    def perform_create(self, serializer):
        coach, _ = CoachProfile.objects.get_or_create(user=self.request.user)
        serializer.save(coach=coach)


class ClientDailyReportListAPIView(generics.ListAPIView):
    serializer_class = DailyReportSerializer
    permission_classes = [IsClientOwner]

    def get_queryset(self):
        client_profile, _ = ClientProfile.objects.get_or_create(user=self.request.user)
        return DailyReport.objects.filter(client=client_profile).order_by("-date")


class AnnouncementListAPIView(generics.ListAPIView):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_coach():
            return Announcement.objects.all().order_by("-created_at")
        return Announcement.objects.filter(audience=Announcement.Audience.ALL).order_by("-created_at")

class LessonScheduleListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = LessonScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    POOL_OPEN_HOUR = 6   # 06:00 AM
    POOL_CLOSE_HOUR = 18  # 06:00 PM

    def get_queryset(self):
        user = self.request.user
        if user.is_internal():
            return LessonSchedule.objects.all().select_related("coach__user", "client__user", "activity").order_by("-start_time")
        if user.is_coach():
            return LessonSchedule.objects.filter(coach__user=user).select_related("client__user", "activity").order_by("-start_time")
        if user.is_client():
            return LessonSchedule.objects.filter(client__user=user).select_related("coach__user", "activity").order_by("-start_time")
        return LessonSchedule.objects.none()

    def create(self, request, *args, **kwargs):
        user = request.user
        if not user.is_client():
            return Response(
                {"detail": "Only registered clients can schedule lessons."},
                status=status.HTTP_403_FORBIDDEN
            )

        client, _ = ClientProfile.objects.get_or_create(user=user)

        activity_id = request.data.get("activity_id")
        start_time_raw = request.data.get("start_time")

        if not activity_id or not start_time_raw:
            return Response(
                {"detail": "Both activity_id and start_time are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        activity = get_object_or_404(Activity, id=activity_id, is_active=True)
        start_time = parse_datetime(start_time_raw)
        if not start_time:
            return Response(
                {"detail": "Invalid start_time format. Please provide a valid timestamp."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if timezone.is_naive(start_time):
            start_time = timezone.make_aware(start_time, timezone.get_current_timezone())

        if start_time < timezone.now():
            return Response(
                {"detail": "Session bookings cannot be scheduled in the past."},
                status=status.HTTP_400_BAD_REQUEST
            )

        end_time = start_time + timedelta(minutes=activity.duration_minutes)

        local_start = timezone.localtime(start_time)
        local_end = timezone.localtime(end_time)

        if local_start.hour < self.POOL_OPEN_HOUR or (local_end.hour > self.POOL_CLOSE_HOUR or (local_end.hour == self.POOL_CLOSE_HOUR and local_end.minute > 0)):
            return Response(
                {
                    "detail": f"Pool operates from 06:00 AM to 06:00 PM. A {activity.duration_minutes}-minute lesson starting at {local_start.strftime('%I:%M %p')} ends after closing time."
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            busy_coach_ids = LessonSchedule.objects.filter(
                status=LessonSchedule.Status.SCHEDULED,
                start_time__lt=end_time,
                end_time__gt=start_time
            ).values_list("coach_id", flat=True)

            assigned_coach = None

            # 1. Preferred coach
            if client.assigned_coach and client.assigned_coach.id not in busy_coach_ids and client.assigned_coach.user.is_active:
                assigned_coach = client.assigned_coach

            # 2. Any active verified coach
            if not assigned_coach:
                assigned_coach = (
                    CoachProfile.objects
                    .filter(user__is_active=True, is_verified=True)
                    .exclude(id__in=busy_coach_ids)
                    .first()
                )

            # 3. Fallback: Any active coach
            if not assigned_coach:
                assigned_coach = (
                    CoachProfile.objects
                    .filter(user__is_active=True)
                    .exclude(id__in=busy_coach_ids)
                    .first()
                )

            if not assigned_coach:
                return Response(
                    {"detail": "All academy coaches are booked during this time window. Please pick another slot."},
                    status=status.HTTP_409_CONFLICT
                )

            # Always link the client to this coach so they show up on the coach's roster
            if client.assigned_coach != assigned_coach:
                ClientProfile.objects.filter(id=client.id).update(assigned_coach=assigned_coach)

            # Create Order
            order = Order.objects.create(
                client=client,
                coach=assigned_coach,
                booking_start=start_time,
                booking_end=end_time,
                total_cost=activity.price,
                status=Order.Status.PENDING
            )
            order.activity.set([activity])

            # Create Schedule
            schedule = LessonSchedule.objects.create(
                order=order,
                client=client,
                coach=assigned_coach,
                activity=activity,
                start_time=start_time,
                end_time=end_time,
                status=LessonSchedule.Status.SCHEDULED
            )

        serializer = self.get_serializer(schedule)
        return Response(serializer.data, status=status.HTTP_201_CREATED)