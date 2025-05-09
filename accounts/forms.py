from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import *
from django.contrib.auth.forms import AuthenticationForm


User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ('email', 'phone', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email


class OTPVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6, required=True)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if not OTP.objects.filter(user=self.user, code=otp, is_used=False).exists():
            raise forms.ValidationError("Invalid OTP")
        return otp
    


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(label="Email")


class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(required=True)

class PasswordResetConfirmForm(forms.Form):
    new_password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        if self.cleaned_data.get('new_password') != self.cleaned_data.get('confirm_password'):
            raise forms.ValidationError("Passwords don't match")
        return self.cleaned_data