from django.db import models
from authentication.models import Candidate
from employer_profile.models import JobPost
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from dateutil.relativedelta import relativedelta

class SavedJob(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='saved_jobs')
    job       = models.ForeignKey(JobPost, on_delete=models.CASCADE)
    saved_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-saved_at']



class JobApplication(models.Model):
    STATUS_CHOICES = [
        ('applied',   'Applied'),
        ('reviewing', 'Under Review'),
        ('interview', 'Interview Scheduled'),
        ('offered',   'Offer Extended'),
        ('rejected',  'Rejected'),
    ]

    candidate    = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='applications')
    job          = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='applications')
    applied_at   = models.DateTimeField(default=timezone.now)
    status       = models.CharField(max_length=20, choices=STATUS_CHOICES, default='applied')
    is_approved  = models.BooleanField(default=False)
    interview_at = models.DateTimeField(null=True, blank=True)
    cover_letter = models.FileField(
        upload_to='applications/cover_letters/',
        validators=[FileExtensionValidator(['pdf','doc','docx','png','jpg','jpeg'])]
    )
    meeting_message = models.TextField(null=True, blank=True)
    meeting_link    = models.URLField(null=True, blank=True)

    class Meta:
        unique_together = ('candidate', 'job')
        ordering = ['-applied_at']



class CandidateCV(models.Model):
    candidate    = models.OneToOneField(
        Candidate,
        on_delete=models.CASCADE,
        related_name='cv'
    )
    cv_file      = models.FileField(
        upload_to='cvs/',
        validators=[FileExtensionValidator(['pdf','docx','png','jpg','jpeg'])]
    )
    parsed_data  = models.JSONField(null=True, blank=True)
    parsed_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"CV for {self.candidate.email}"


class CandidatePremium(models.Model):
    candidate            = models.OneToOneField(
        Candidate,
        on_delete=models.CASCADE,
        related_name='premium'
    )
    is_subscribed        = models.BooleanField(default=False)
    subscribed_at        = models.DateTimeField(null=True, blank=True)
    subscription_end     = models.DateTimeField(null=True, blank=True)
    payment_ok           = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.candidate.email} Premium: {'Active' if self.is_subscribed else 'Inactive'}"
    
    