
from django.urls import path
from . import views

app_name = 'index'  

urlpatterns = [
    path('', views.home, name='home'),
    path('jobs/', views.job_list, name='jobs_list'),
    path('job_details/<int:job_id>/', views.job_details, name='job_details'),
    path('explore/<str:filter_type>/<slug:keyword>/', views.explore_jobs, name='explore_jobs'),

]
