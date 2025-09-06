from django.urls import path
from . import views

app_name = 'employer_profile'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_manage, name='profile_manage'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/manage/', views.manage_jobs, name='manage_jobs'),
    path('profile/toggle-notify/', views.toggle_notify, name='toggle_notify'),
    path('profile/location/', views.update_employer_location, name='update_employer_location'),
    path('jobs/<int:job_id>/deactivate/', views.deactivate_job, name='job_deactivate'),
    path('edit_job/<int:job_id>/', views.edit_job, name='edit_job'),
    path('jobs/<int:job_id>/applications/', views.job_applications, name='job_applications'),
    path('application/<int:app_id>/', views.application_detail, name='application_detail'),
    path('interviews/', views.interview_applications, name='interview_applications'),
    path('interviews/send/<int:app_id>/', views.send_meeting, name='send_meeting'),
    path('premium/', views.premium, name='premium'),
    path('premium/subscribe/', views.subscribe_premium, name='subscribe_premium'),
    path('logout/', views.logout, name='logout'),
    
]
