from django.contrib import admin
from .models import Candidate

@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display    = ('candidate_id', 'first_name', 'last_name', 'email', 'is_active', 'joined_time')
    search_fields   = ('first_name', 'last_name', 'email')
    list_filter     = ('is_active', 'is_deleted', 'email_notify')
    readonly_fields = ('candidate_id', 'joined_time')


from .models import Employer

@admin.register(Employer)
class EmployerAdmin(admin.ModelAdmin):
    list_display    = ('employer_id', 'company_name', 'representative_name', 'email', 'is_active', 'joined_time')
    search_fields   = ('company_name', 'representative_name', 'email')
    list_filter     = ('is_active', 'is_deleted', 'email_notify')
    readonly_fields = ('employer_id', 'joined_time')
