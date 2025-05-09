from django.urls import path

from accounts.forms import EmailAuthenticationForm
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Registration
    path('signup/', views.signup, name='signup'),
    path('verify-otp/<int:user_id>/', views.verify_otp, name='verify_otp'),

    # Login/Logout
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        form_class=EmailAuthenticationForm
    ), name='login'),
    path('logout/', views.custom_logout, name='logout'),

    # Password Reset
    path('password-reset/', views.request_password_reset, name='password_reset'),
    path('password-reset-confirm/<int:user_id>/', 
         views.reset_password_confirm, name='password_reset_confirm'),

    # OTP Login
    path('login-with-otp/', views.login_with_otp, name='login_with_otp'),
    path('verify-login-otp/<int:user_id>/', views.verify_login_otp, name='verify_login_otp'),
]