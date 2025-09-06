from django.urls import path
from . import views

app_name = 'candidate_profile'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('save-job/', views.save_job, name='save_job'),
    path('saved-jobs/', views.saved_jobs, name='saved_jobs'),
    path('applications/', views.applied_jobs, name='applied_jobs'),
    path('applications/<int:application_id>/', views.application_detail, name='application_detail'),
    path('applications/interviews/', views.interview_list, name='interview_list'),
    path('upload_cv/', views.upload_and_review_cv, name='upload_cv'),
    path('clear-cv/', views.clear_cv, name='clear_cv'),
    path('profile/', views.profile_manage, name='profile_manage'),
    path('toggle-notify/', views.toggle_notify, name='toggle_notify'),
    path('profile/location/', views.update_location, name='update_location'),
    path('skill-gap/', views.skill_gap, name='skill_gap'),
    path('premium/recommendations/', views.premium_recommendations, name='premium_recommendations'),
    path('premium/', views.premium, name='premium'),
    path('premium/subscribe/', views.subscribe_premium, name='subscribe_premium'),
    path('logout/', views.logout, name='logout'),
    
]
