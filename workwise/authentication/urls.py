from django.urls import path
from . import views

app_name = 'authentication'  

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('signup/candidate/', views.signup_candidate, name='signup_candidate'),
    path('signup/candidate/verify/', views.verify_email_candidate, name='verify_email_candidate'),
    path('verify/candidate/resend/', views.resend_code_candidate, name='resend_code_candidate'),
    path('signup/employer/', views.signup_employer, name='signup_employer'),
    path('signup/employer/verify/', views.verify_email_employer, name='verify_email_employer'),
    path('verify/employer/resend/', views.resend_code_employer, name='resend_code_employer'),
    path('login/', views.login, name='login'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('reset-password/verify/', views.reset_verify, name='reset_password_verify'),

]