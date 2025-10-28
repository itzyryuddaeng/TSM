from django import forms
from django.contrib.auth.models import User
from .models import Profile
from django.core.exceptions import ValidationError
from .models import Appointment
from .models import CertificateRequest


YEAR_LEVEL_CHOICES = [
    ("1st Year", "1st Year"),
    ("2nd Year", "2nd Year"),
    ("3rd Year", "3rd Year"),
    ("4th Year", "4th Year"),
]

class StudentRegistrationForm(forms.ModelForm):
    # Add custome fields on top of django built-in User model field
    password = forms.CharField(widget=forms.PasswordInput(attrs={"id": "id_password"}), label="Password") #password input
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={"id": "id_confirm_password"}), label="confirm_password") #confirmation of password field
    student_number = forms.CharField(max_length=50, label="Student Number") #student number field
    course = forms.CharField(max_length=100, required=True, label="Course") #course field
    year_level = forms.ChoiceField(choices=YEAR_LEVEL_CHOICES, required=True, label="Year Level") #year level field
    document = forms.FileField(required=True, label="Upload COR/ID") #uploading document
    first_name = forms.CharField(max_length=30)
    last_name = forms.CharField(max_length=30)


    class Meta:
        model = User
        #including both user fields and custom field
        fields = ["username", "email", "first_name", "last_name","password", "confirm_password", "course", "year_level", "document"]
        # fields = ["username", "email", "password"]

    #validating of registration 
    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")

        #checking if password match
        if pw and cpw and pw != cpw:
            raise forms.ValidationError("Password Don't Match!!!")
        return cleaned
    

    # This function allows to check the user inputted email address
    def clean_email(self):
        email = self.cleaned_data.get("email") # get the email of the user

        # checking if the user put the expected extenstion of the campus given email
        if not email.endswith("@cvsu.edu.ph"):
            raise ValidationError("You must user your school email (@cvsu.edu.ph)")
        
        # checking if the user is already registered with that email, and will not be able to register again
        if User.objects.filter(email=email).exists():
            raise ValidationError("This email is already registered")
        return email

    #validating the unique student number
    def clean_student_number(self):
        """
            checking if the inputted student number is already registered to avoid multiple accounts
        """
        student_number = self.cleaned_data.get("student_number")
        from .models import Profile
        if Profile.objects.filter(student_number=student_number).exists():
            raise forms.ValidationError("This student number is already registered")
        return student_number
    
# Form for verifying OTP input
class OTPForm(forms.Form):
    code = forms.CharField(max_length=6)


# Creating the appointment form
class AppointmentForms(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ["purpose", "appointment_date", "appointment_time"]
        widgets = {
            "appointment_date": forms.DateInput(attrs={"type": "date"}),
            "appointment_time": forms.TimeInput(attrs={"type": "time"})
        }

class CertificateRequestForm(forms.ModelForm):
    class Meta:
        model = CertificateRequest
        fields = ['certificate_type', 'purpose', 'supporting_document']
        widgets = {
            'certificate_type': forms.Select(attrs={'class': 'form-control'}),
            'purpose': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter purpose for this certificate.'}),
        }