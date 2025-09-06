from django.contrib import admin
from .models import SavedJob
from .models import JobApplication
from .models import CandidateCV, CandidatePremium


@admin.register(SavedJob)
class SavedJobAdmin(admin.ModelAdmin):
    list_display  = ('candidate', 'job', 'saved_at')
    list_filter   = ('candidate', 'job__industry', 'saved_at')
    search_fields = (
        'candidate__first_name',
        'candidate__last_name',
        'candidate__email',
        'job__title',
        'job__employer__company_name',
    )
    raw_id_fields = ('candidate', 'job')
    date_hierarchy = 'saved_at'




@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'candidate',
        'job',
        'status',
        'is_approved',
        'applied_at',
        'interview_at',
    )
    list_filter = (
        'status',
        'is_approved',
        'applied_at',
    )
    search_fields = (
        'candidate__first_name',
        'candidate__last_name',
        'candidate__email',
        'job__title',
        'job__employer__company_name',
    )
    raw_id_fields = (
        'candidate',
        'job',
    )
    date_hierarchy = 'applied_at'




@admin.register(CandidateCV)
class CandidateCVAdmin(admin.ModelAdmin):
    list_display    = ('candidate', 'cv_file', 'parsed_at')
    readonly_fields = ('parsed_at',)
    search_fields   = (
        'candidate__first_name',
        'candidate__last_name',
        'candidate__email',
    )
    list_filter     = ('parsed_at',)
    ordering        = ('-parsed_at',)



@admin.register(CandidatePremium)
class CandidatePremiumAdmin(admin.ModelAdmin):
    list_display = (
        'candidate',
        'is_subscribed',
        'payment_ok',
        'subscribed_at',
        'subscription_end',
    )
    list_filter = (
        'is_subscribed',
        'payment_ok',
    )
    search_fields = (
        'candidate__email',
        'candidate__first_name',
        'candidate__last_name',
    )
    readonly_fields = (
        'subscribed_at',
        'subscription_end',
    )