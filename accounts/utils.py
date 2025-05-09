from django.core.mail import send_mail
from django.conf import settings

def send_otp_email(email, otp_code):
    subject = "Your OTP Code"
    message = f"Your verification code is: {otp_code}\n\nThis code expires in 5 minutes."
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )