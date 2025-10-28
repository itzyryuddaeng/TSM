from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login
from .forms import StudentRegistrationForm, OTPForm
from django.contrib.auth.models import User
from django.conf import settings
from .models import Profile, OTP
from django.utils import timezone
from django.core.mail import send_mail
import random
from datetime import timedelta
from django.db import IntegrityError
# from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import AppointmentForms
from django.contrib import messages
from .models import Appointment, Profile
from django.utils import timezone
from datetime import date
from .forms import CertificateRequestForm
from .models import CertificateRequest
from django.contrib.auth.decorators import login_required


@login_required
def student_dashboard(request):
    """
        Student landing page after registration or login
        shows quick link and status summary
    """

    profile = getattr(request.user, "profile", None)
    appointments = Appointment.objects.filter(student=request.user).count()
    certificates = CertificateRequest.objects.filter(student=request.user).count() if 'CertificateRequest' in globals() else 0

    # if not yet approved, redirect to pending page
    if not profile.is_approved_by_registrar:
        return redirect("core:pending_approval")
    return render(request, "core/student.dashboard.html", {"profile": profile})

    context = {
        "profile": profile,
        "appointments": appointments,
        "certificates": certificates,
    }
    return render(request, "core/student_dashboard.html", context)

def generate_otp_code(length=6):
    return "".join(str(random.randint(0,9)) for _ in range(length))


def register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            username = form.cleaned_data["username"]
            email = form.cleaned_data["email"]
            password = form.cleaned_data["password"]
            first_name = form.cleaned_data["first_name"]
            last_name = form.cleaned_data["last_name"]
            student_number = form.cleaned_data["student_number"]
            course = form.cleaned_data.get("course", "")
            year_level = form.cleaned_data.get("year_level", "")
            document = request.FILES.get("document")

            #create inactive user
            user = User.objects.create_user(username=username, 
                                            email=email, 
                                            password=password,
                                            first_name = first_name,
                                            last_name = last_name, 
                                            is_active=False,
                                            )
            

            # Attack Profile
            # Allows for safer updating of the profile and only allowing to create once
            Profile.objects.create(
                user = user,
                student_number = student_number,
                course = course,
                year_level = year_level,
                document = document,
                submitted_at = timezone.now(),
                is_verified_email = False,
                is_approved_by_registrar = False

            )

            """
                # This line of code is at risk of having multiple integrity error if a profile is already existing with the same student number

            #attach profile
           
            profile = Profile.objects.get_or_create(user=user)

            profile.student_number = student_number
            profile.course = course
            profile.year_level = year_level
            profile.document = document
            profile.submitted_at = timezone.now()
            profile.is_verified_email = False
            profile.is_approved_by_registrar = False
            profile.save()
            """
            # Create OTP
            code = generate_otp_code()
            expires = timezone.now() + timedelta(minutes=20)
            OTP.objects.create(user=user, code=code, expires_at=expires)

            # send email
            subject = "Your Verification Code"
            message = f"Hi {username}, your OTP code is {code}. It expires in {expires}. Thank you"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [email]
            send_mail(subject, message, from_email,recipient_list, fail_silently=False)

            # save username in session to be used by verify page
            request.session["verify_user_id"] = user.id
            return redirect("core:verify_otp")
        else:
            print("Form Errors:", form.errors)
        
    else:
        form = StudentRegistrationForm()
        #allows to always return a response (for GET or invalid type of form)
    return render(request, "core/register.html", {"form": form})
    
def login_view(request):
    return render(request, 'core/login.html')

def register(request):
    return render(request, "core/register.html")

def verify_otp(request):
    """ request session 
    
    * allows to get for approval before finalization of the account
    * create a verification of legitmacy of being a student of the campus
    * registrar will track documents before approving the account
    """
    user_id = request.session.get("verify_user_id")
    if not user_id:
        return redirect("core:register")
    user = get_object_or_404(User, id=user_id)

    if request.method == "POST":
        form = OTPForm(request.POST)
        if form.is_valid():
            code = form.cleaned_data["code"].strip()
            # check last unexpired OTP
            # in-case it double request of OTP
            otp_qs = OTP.objects.filter(user=user, code=code).order_by("-created_at")
            if not otp_qs.exists():
                form.add_error("code", "Invalid code")
            else:
                otp = otp_qs.first()
                if otp.is_expired():
                    form.add_error("code", "Code expired. Request a new Code!")
                else:
                    # marking each profile as verified
                    profile = user.profile
                    profile.is_verified_email = True
                    profile.save()

                    # optionally allows to delete OTP's
                    OTP.objects.filter(user=user).delete()

                    #log user in
                    login(request, user)
                    return redirect("core:pending_approval")
    else:
        form = OTPForm()
    return render(request, "core/verify_otp.html", {"form": form, "email":user.email})




def pending_approval(request):
    """
        This code handles the pending request of the accounts
    
    """

    #after verification, show pending screen until registrar approves
    return render(request, "core/pending_approval.html")

# registrar can view the list of pending verifications
# but this will required the login for the staff
from django.contrib.auth.decorators import user_passes_test

def staff_check(user):
    return user.is_staff or user.is_superuser

@user_passes_test(staff_check)
def approval_list(request):
    profiles = Profile.objects.filter(is_verified_email=True, is_approved_by_registrar=False)
    return render(request, "core/approval_list.html", {"profiles": profiles})

@user_passes_test(staff_check)
def approve_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    profile.is_approved_by_registrar = True
    profile.save()
    # sending a mail for notifying as approved account
    send_mail(
        "Account Approved",
        f"Hello {profile.user.username}, you account has been approved by the Registrar",
        settings.DEFAULT_FROM_EMAIL,
        [profile.user.email],
        fail_silently=True,
    )
    return redirect("core:approval_list")

@user_passes_test(staff_check)
def reject_profile(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)

    # option for deactivating user or deleting user's account
    # can be implemented if the user already graduated/transfers
    user = profile.user
    user.is_active = False
    user.save()
    profile.is_approved_by_registrar = False
    profile.save()
    send_mail(
        "Account Rejected",
        f"Hello {profile.user.username}, your account registration has been rejected by the Registrar.",
        settings.DEFAULT_FROM_EMAIL,
        {profile.user.email},
        fail_silently=True,
    )
    return redirect("core:approval_list")


# helping the function to check if the user is staff
def is_registrar(user):
    return user.is_staff

# @login_required
def student_appointments(request):

    user = request.user
    today = date.today()
    # Get all appointments for the logged-in student (or all if not filtered yet)
    appointments = Appointment.objects.all().order_by('-appointment_date', '-appointment_time')


    #allows to check available schedules
    available_times = [
        "8:00 AM", "9:00 AM", "10:00 AM", "11:00 AM",
        "1:00 PM", "2:00 PM", "3:00 PM",
    ]
    
    # booked out slows for selected date 
    selected_date = request.POST.get('appointment_date', None)
    booked_times = []
    if selected_date:
        booked_times = Appointment.objects.filter(
            appointment_date = selected_date
        ).values_list('appointment_time', flat=True)

    if request.method == 'POST':
        form = AppointmentForms(request.POST)
        if form.is_valid():
            appointment_date = form.cleaned_data['appointment_date']
            appointment_time = form.cleaned_data['appointment_time']

            # prvent from double booking by the same student
            if Appointment.objects.filter(student=user, appointment_date=appointment_date).exists():
                messages.error(request, "You already booked an appointment on this date")
                return redirect('core:student_appointments')

            # prevent full schedule for the slow. ONLY allows limited slots
            # only 10 ppl will be included to take appointment in that specific date
            if Appointment.objects.filter(appointment_date=appointment_date).count() >= 10:
                messages.error(request, "All appointment slots for this day are FULL!")
                return redirect('core:student_appointments')
            
            else:
                appointment = form.save(commit=False)
                appointment.student = user
                appointment.status = 'Pending'
                appointment.save()
                messages.success(request, "Appointment Booked Successfully!")
                return redirect('core:student_appointments')
        else:
            messages.error(request, "Please coorect the errors below")
    else:
        form = AppointmentForms()

    return render(request, 'core/student_appointments.html', {
        'form': form,
        'appointments': appointments,
        'available_times': available_times,
        'booked_times': booked_times,

    })


# @user_passes_test(is_registrar)
def registrar_appointments(request):
    appointments = Appointment.objects.all().order_by("-created_at")
    return render(request, "core/registrar_appointments.html", {"appointments": appointments})


# @user_passes_test(is_registrar)
def update_appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = status
    appointment.save()
    messages.success(request, f"Appointment {status.lower()} successfully")
    return redirect("core:registrar_appointments")



# @user_passes_test(is_registrar)
def registrar_dashboard(request):
    today = date.today()
    month_start = today.replace(day=1)

    pending_profiles = Profile.objects.filter(
        is_verified_email=True, is_approved_by_registrar=False
    ).count()
    processing_appointments = Appointment.objects.filter(status="Pending").count()
    completed_today = Appointment.objects.filter(
        status="Approved", appointment_date=today
    ).count()
    total_this_month = Appointment.objects.filter(
        created_at__date__gte=month_start
    ).count()

    # Build recent activity list
    recent_profiles = Profile.objects.order_by('-submitted_at')[:3]
    recent_appointments = Appointment.objects.order_by('-created_at')[:3]

    recent_activity = []

    for p in recent_profiles:
        recent_activity.append({
            "type": "Profile",
            "text": f"New student registered: {p.user.get_full_name()} (ID: {p.student_number})",
            "time": p.submitted_at,
        })
    for a in recent_appointments:
        recent_activity.append({
            "type": "Appointment",
            "text": f"{a.purpose} appointment from {a.student.username} ({a.status})",
            "time": a.created_at,
        })

    # Sort both by most recent
    recent_activity = sorted(recent_activity, key=lambda x: x["time"], reverse=True)[:5]

    context = {
        "pending_profiles": pending_profiles,
        "processing_appointments": processing_appointments,
        "completed_today": completed_today,
        "total_this_month": total_this_month,
        "recent_activity": recent_activity,
    }

    return render(request, "core/registrar_website.html", context)


# REGISTRAR: Allows to view ll certificate request
def registrar_certificates(request):
    certificates = CertificateRequest.objects.all().order_by("-requested_at")
    return render(request, "core/registrar_certificates.html", {"certificates": certificates})

# REGISTRAR: update(approve/reject/release)
def update_certificate_status(request, cert_id, status):
    cert = get_object_or_404(CertificateRequest, id=cert_id)
    cert.status = status
    cert.save()
    messages.success(request, f"Certificate request {status.lower()} successfully")
    return redirect("core:registrar_certificates")

def certificate_request_view(request):
    user = request.user

    if request.method == "POST":
        form = CertificateRequestForm(request.POST, request.FILES)
        if form.is_valid():
            certificate = form.save(commit=False)
            certificate.student = user if user.is_authenticated else None
            certificate.save()
            messages.success(request, "Your certificate request has been submitted successfully!")
            return redirect('core:certificate_request')
        else:
            messages.error(request, "Please correct the errors below.")

    else:
        form = CertificateRequestForm()

    # show prev request
    previous_request = CertificateRequest.objects.filter(student=request.user).order_by('-requested_at')

    return render(request, 'core/certificate_request.html', {
        'form': form,
        'previous_request': previous_request,
    })







