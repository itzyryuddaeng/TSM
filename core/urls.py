from django.urls import path, include
from . import views
from django.contrib import admin


app_name = "core"

urlpatterns = [
    # THESE ARE FOR WAITING AREA
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("verify/", views.verify_otp, name="verify_otp"),

    # THESE ARE FOR APPROVALS
    path("pending/", views.pending_approval, name="pending_approval"),
    path("approvals/", views.approval_list, name="approval_list"),
    path("approvals/approve/<int:profile_id>/", views.approve_profile, name="approve_profile"),
    path("approvals/reject/<int:profile_id>/", views.reject_profile, name="reject_profile"),

    

    # THESE ARE FOR APPOINTMENTS
    path("appointments/", views.student_appointments, name="student_appointments"),
    path("registrar/appointments/", views.registrar_appointments, name="registrar_appointments"),
    path("registrar/appointments/update/<int:appointment_id>/<str:status>/", views.update_appointment_status, name="update_appointment_status"),
    path("registrar/dashboard/", views.registrar_dashboard, name='registrar_dashboard'),

    # THESE ARE FOR CERTIFICATES
    path('certificates/', views.certificate_request_view, name='certificate_request'),
    path("registrar/certificates/", views.registrar_certificates, name="registrar_certificates"),
    path("registrar/certificates/update/<int:cert_id>/<str:status>/", views.update_certificate_status, name="update_certificate_status"),


    # THESE ARE THE STUDENT PATH
    path('student/dashboard/', views.student_dashboard, name="student_dashboard")


































]