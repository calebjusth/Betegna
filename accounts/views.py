from django.shortcuts import redirect, render

# Create your views here.
from django.core.mail import send_mail
from .forms import *
from .models import OTP
from django.shortcuts import render, redirect
from django.contrib.auth import login
from .models import *
from .forms import UserRegistrationForm
from django.contrib import messages
from django.contrib.auth import logout
from .utils import *
from django.contrib.auth import authenticate, login


def login_with_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.generate_otp(user, purpose='login')
            
            # Send OTP via email
            send_otp_email(user.email, otp.code)
            
            messages.success(request, f"OTP sent to {email}")
            return redirect('verify_login_otp', user_id=user.id)
            
        except User.DoesNotExist:
            messages.error(request, "No account found with this email")
            return redirect('login_with_otp')
    
    return render(request, './accounts/login_with_otp.html')
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required

def verify_login_otp(request, user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        messages.error(request, "Invalid user")
        return redirect('login_with_otp')

    if request.method == 'POST':
        otp_code = request.POST.get('otp')
        
        # Check for valid unused OTP
        otp = OTP.objects.filter(
            user=user,
            code=otp_code,
            purpose='login',
            is_used=False
        ).first()

        if otp and otp.is_valid():
            otp.is_used = True
            otp.save()
            
            # Log the user in
            login(request, user)
            messages.success(request, "Logged in successfully!")
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid or expired OTP")
            return redirect('verify_login_otp', user_id=user.id)

    return render(request, './accounts/verify_login_otp.html', {'user': user})


def login_with_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.generate_otp(user, purpose='login')
            
            # Send OTP via email/SMS
            send_otp_email(user.email, otp.code)
            
            return redirect('verify_login_otp', user_id=user.id)
        except User.DoesNotExist:
            messages.error(request, "User not found")
    
    return render(request, './accounts/login_with_otp.html')

def signup(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # User must verify OTP first
            user.save()
            
            # Generate OTP for email verification
            otp = OTP.generate_otp(user, purpose='signup')
            
            # Send OTP via email (we'll implement this later)
            send_otp_email(user.email, otp.code)
            
            return redirect('verify_otp', user_id=user.id)
    else:
        form = UserRegistrationForm()
    
    return render(request, './accounts/signup.html', {'form': form})



def verify_otp(request, user_id):
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp')
        
        # Check if OTP exists and is valid
        otp = OTP.objects.filter(
            user=user,
            code=otp_code,
            purpose='signup',
            is_used=False
        ).first()
        
        if otp and otp.is_valid():
            otp.is_used = True
            otp.save()
            
            user.is_active = True
            user.is_verified = True
            user.save()
            
            login(request, user)  # Log the user in
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid or expired OTP")
    
    return render(request, './accounts/verify_otp.html', {'user': user})


def custom_logout(request):
    logout(request)
    return redirect('login')

def request_password_reset(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        
        try:
            user = User.objects.get(email=email)
            otp = OTP.generate_otp(user, purpose='reset')
            
            # Send OTP via email
            send_otp_email(user.email, otp.code)
            
            return redirect('reset_password_confirm', user_id=user.id)
        except User.DoesNotExist:
            messages.error(request, "No user found with this email")
    
    return render(request, './accounts/password_reset_request.html')

def reset_password_confirm(request, user_id):
    user = User.objects.get(id=user_id)
    
    if request.method == 'POST':
        otp_code = request.POST.get('otp')
        new_password = request.POST.get('new_password')
        
        # Verify OTP
        otp = OTP.objects.filter(
            user=user,
            code=otp_code,
            purpose='reset',
            is_used=False
        ).first()
        
        if otp and otp.is_valid():
            otp.is_used = True
            otp.save()
            
            # Set new password
            user.set_password(new_password)
            user.save()
            
            messages.success(request, "Password updated successfully")
            return redirect('login')
        else:
            messages.error(request, "Invalid or expired OTP")
    
    return render(request, './accounts/password_reset_confirm.html', {'user': user})