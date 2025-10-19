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
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Appointment, TimeSlot
from .forms import AppointmentForm
from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin

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
    profiles = Profile.objects.filter(is_verified_email=True, is_approve_by_registrar=False)
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

@login_required
def student_appointments(request):
    # Get all appointments for the logged-in student (or all if not filtered yet)
    appointments = Appointment.objects.all().order_by('-appointment_date', '-appointment_time')

    if request.method == 'POST':
        form = AppointmentForm(request.POST)
        if form.is_valid():
            appointment = form.save(commit=False)
            # Optionally tie it to a student if you have a user relation
            # appointment.student = request.user  
            appointment.status = 'pending'
            appointment.save()
            messages.success(request, "Appointment booked successfully!")
            return redirect('core:student_appointments')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = AppointmentForms()

    # ✅ Always return an HttpResponse
    return render(request, 'core/student_appointments.html', {
        'form': form,
        'appointments': appointments,
    })

@user_passes_test(is_registrar)
def registrar_appointments(request):
    appointments = Appointment.objects.all().order_by("-created_at")
    return render(request, "core/registrar_appointments.html", {"appointments": appointments})


@user_passes_test(is_registrar)
def update_appointment_status(request, appointment_id, status):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    appointment.status = status
    appointment.save()
    messages.success(request, f"Appointment {status.lower()} successfully")
    return redirect("registrar_appointments")


class TimeSlotListView(ListView):
    model = TimeSlot
    template_name = "core/available_schedules.html"
    context_object_name = "timeslots"

    def get_queryset(self):
        return [ts for ts in TimeSlot.objects.filter(is_active=True).order_by('start') if ts.available()]

class BookAppointmentView(LoginRequiredMixin, CreateView):
    model = Appointment
    form_class = AppointmentForm
    template_name = "core/book_appointment.html"
    success_url = reverse_lazy('core:student_appointments')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        # prevent double booking and capacity race condition (simple check)
        form.instance.student = self.request.user
        ts = form.cleaned_data['timeslot']
        if not ts.available():
            form.add_error('timeslot', 'This timeslot is no longer available.')
            return self.form_invalid(form)
        # extra check: whether student already has an appointment at same time
        if Appointment.objects.filter(student=self.request.user, timeslot=ts).exists():
            form.add_error(None, 'You already have an appointment for this timeslot.')
            return self.form_invalid(form)

        response = super().form_valid(form)
        messages.success(self.request, "Appointment requested. You will be notified when confirmed.")
        return response

def login_success(request):
    return render(request, 'core/Login_Successfully.html')















