from django.urls import path
from . import views

urlpatterns = [
    # Static Entry & Landing UI routes
    path("", views.index_view, name="index-page"),
    path("auth/", views.auth_view, name="auth-page"),
    path("portal/internal-auth/", views.internal_login_view, name="internal-auth-page"),
    path("dashboard/", views.dashboard_dispatcher, name="dashboard-dispatcher"),
    
    # REST Framework Endpoints
    path("api/v1/auth/register/", views.PublicRegisterAPIView.as_view(), name="api-register"),
    path("api/v1/auth/login/", views.SessionLoginAPIView.as_view(), name="api-login"),
    path("api/v1/auth/internal-login/", views.InternalSecureLoginAPIView.as_view(), name="api-internal-login"),
    path("api/v1/auth/logout/", views.SessionLogoutAPIView.as_view(), name="api-logout"),
    
    # Catalog & Orders
    path("api/v1/catalog/", views.PublicCatalogAPIView.as_view(), name="api-catalog"),
    path("api/v1/orders/", views.OrderListCreateAPIView.as_view(), name="api-orders"),
    path("api/v1/orders/<uuid:order_id>/pay/", views.SimulatePaymentAPIView.as_view(), name="api-simulate-pay"),
    path("orders/<uuid:order_id>/pay/", views.payment_checkout_view, name="order-payment-page"),

    # Coach & Client Interactions
    path("api/v1/coach/my-clients/", views.CoachMyclientsAPIView.as_view(), name="api-coach-my-clients"),
    path("api/v1/coach/my-clients/<uuid:client_id>/", views.CoachClientDetailAPIView.as_view(), name="api-coach-client-detail"),
    path("api/v1/coach/reports/", views.CoachDailyReportCreateAPIView.as_view(), name="api-coach-create-report"),
    path("api/v1/client/me/", views.ClientProfileDetailAPIView.as_view(), name="api-client-me"),
    path("api/v1/client/my-reports/", views.ClientDailyReportListAPIView.as_view(), name="api-client-my-reports"),
    path("api/v1/schedules/", views.LessonScheduleListCreateAPIView.as_view(), name="api-schedules"),
    # Announcements
    path("api/v1/announcements/", views.AnnouncementListAPIView.as_view(), name="api-announcements"),
]