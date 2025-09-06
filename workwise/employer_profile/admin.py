from django.contrib import admin
from .models import JobPost, CompanyProfile

from django.utils.html import format_html
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import path, reverse
from django.core.mail import send_mail
from authentication.models import Employer
from .models import CompanyProfile
from .models import EmployerPremium

@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = (
        'job_id', 'title', 'employer', 'is_active',
        'application_deadline', 'posted_at'
    )
    list_filter = (
        'is_active', 'work_type', 'location_type', 'industry'
    )
    search_fields = (
        'title', 'description', 'department',
        'employer__company_name', 'contact_email'
    )
    ordering = ('-posted_at',)
    readonly_fields = ('job_id', 'posted_at')



@admin.register(EmployerPremium)
class EmployerPremiumAdmin(admin.ModelAdmin):
    list_display    = (
        'employer',
        'is_subscribed',
        'payment_ok',
        'subscribed_at',
        'subscription_end',
    )
    list_filter     = ('is_subscribed', 'payment_ok')
    search_fields   = (
        'employer__company_name',
        'employer__email',
    )
    readonly_fields = ('subscribed_at', 'subscription_end')



@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
    list_display = (
        'company_name',
        'representative_name',
        'employer_email',
        'certificate_submitted_at',
        'logo_preview',
        'certificate_preview',
        'row_actions',
    )
    list_filter = ('employer__is_verified',)
    ordering    = ('certificate_submitted_at',)
    actions     = ['send_message_action']
    actions_on_top    = True
    actions_on_bottom = False

    # — Data columns —
    def company_name(self, obj):
        return obj.employer.company_name
    company_name.short_description = 'Company'

    def representative_name(self, obj):
        return obj.employer.representative_name
    representative_name.short_description = 'Representative'

    def employer_email(self, obj):
        return obj.employer.email
    employer_email.short_description = 'Email'

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height:80px;border:1px solid #ccc;"/>',
                obj.logo.url
            )
        return '—'
    logo_preview.short_description = 'Logo'

    def certificate_preview(self, obj):
        if obj.certificate:
            return format_html(
                '<a href="{0}" target="_blank">'
                  '<img src="{0}" style="max-height:200px;"/>'
                '</a>',
                obj.certificate.url
            )
        return '—'
    certificate_preview.short_description = 'Certificate'

    # — Only show unverified profiles —
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return (
            qs
            .filter(employer__is_verified=False, certificate_submitted_at__isnull=False)
            .order_by('certificate_submitted_at')
        )

    # — Row-level action buttons —
    def row_actions(self, obj):
        return format_html(
            '<a class="button" style="background:#16a34a;color:#fff;padding:2px 8px;border-radius:3px;'
                       'text-decoration:none;margin-right:4px;display:inline-block" '
              'href="{}">Verify</a>'
            '<a class="button" style="background:#dc2626;color:#fff;padding:2px 8px;border-radius:3px;'
                       'text-decoration:none;margin-right:4px;display:inline-block" '
              'href="{}">Del Cert</a>'
            '<a class="button" style="background:#2563eb;color:#fff;padding:2px 8px;border-radius:3px;'
                       'text-decoration:none;display:inline-block" '
              'href="{}?selected={}">Email</a>',
            reverse('admin:employer_profile_companyprofile_verify', args=[obj.pk]),
            reverse('admin:employer_profile_companyprofile_delete_cert', args=[obj.pk]),
            reverse('admin:employer_profile_companyprofile_send_message'),
            obj.pk,
        )
    row_actions.short_description = 'Actions'
    row_actions.allow_tags = True

    # — Bulk action to launch email form —
    def send_message_action(self, request, queryset):
        selected = ",".join(str(pk) for pk in queryset.values_list('pk', flat=True))
        return redirect(
            reverse('admin:employer_profile_companyprofile_send_message')
            + f'?selected={selected}'
        )
    send_message_action.short_description = 'Send custom email to selected profiles'

    # — Hook custom URLs —
    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                '<int:pk>/verify/',
                self.admin_site.admin_view(self.verify_view),
                name='employer_profile_companyprofile_verify',
            ),
            path(
                '<int:pk>/delete-cert/',
                self.admin_site.admin_view(self.delete_cert_view),
                name='employer_profile_companyprofile_delete_cert',
            ),
            path(
                'send-message/',
                self.admin_site.admin_view(self.send_message_view),
                name='employer_profile_companyprofile_send_message',
            ),
        ]
        return custom + urls

    # — Per-row verify view —
    def verify_view(self, request, pk):
        prof = get_object_or_404(CompanyProfile, pk=pk)
        prof.employer.is_verified = True
        prof.employer.save()
        self.message_user(request, f"Verified {prof.employer.company_name}")
        return redirect(reverse('admin:employer_profile_companyprofile_changelist'))

    # — Per-row delete certificate view —
    def delete_cert_view(self, request, pk):
        prof = get_object_or_404(CompanyProfile, pk=pk)
        if prof.certificate:
            prof.certificate.delete(save=False)
            prof.certificate = None
            prof.certificate_submitted_at = None
            prof.save()
        self.message_user(request, f"Deleted certificate for {prof.employer.company_name}")
        return redirect(reverse('admin:employer_profile_companyprofile_changelist'))

    # — Email form (GET) & send (POST) —
    def send_message_view(self, request):
        if request.method == 'POST':
            pks = request.POST.get('selected', '').split(',')
            msg = request.POST.get('message', '').strip()
            count = 0
            for prof in CompanyProfile.objects.filter(pk__in=pks):
                send_mail(
                    subject="Message from Admin",
                    message=msg,
                    from_email=None,  # DEFAULT_FROM_EMAIL
                    recipient_list=[prof.employer.email],
                )
                count += 1
            self.message_user(request, f"Sent email to {count} employer(s).")
            return redirect(reverse('admin:employer_profile_companyprofile_changelist'))

        # GET => show the intermediate form
        selected = request.GET.get('selected', '')
        qs = CompanyProfile.objects.filter(pk__in=selected.split(','))
        return render(
            request,
            'admin/send_profile_message.html',
            {
                'profiles': qs,
                'selected': selected,
                'opts': self.model._meta,
            }
        )
