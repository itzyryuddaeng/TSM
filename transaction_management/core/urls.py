from django.urls import path, include
from . import views
from django.contrib import admin


app_name = "core"

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("login-success/", views.login_success, name="login_success"),
    path("verify/", views.verify_otp, name="verify_otp"),
    path("pending/", views.pending_approval, name="pending_approval"),
    path("approvals/", views.approval_list, name="approval_list"),
    path("approvals/approve/<int:profile_id>/", views.approve_profile, name="approve_profile"),
    path("approvals/reject/<int:profile_id>/", views.reject_profile, name="reject_profile"),
    path("appointments/", views.student_appointments, name="student_appointments"),
    path("registrar/appointments/", views.registrar_appointments, name="registrar_appointments"),
    path("registrar/appointments/update/<int:appointment_id>/<str:status>/", views.update_appointment_status, name="update_appointment_status"),
    path("schedules/", views.TimeSlotListView.as_view(), name="available_schedules"),
    path("book/", views.BookAppointmentView.as_view(), name="book_appointment"),
]