

from django.db import models
from django.db.models import Max
from authentication.models import Employer
from django.utils import timezone
from dateutil.relativedelta import relativedelta


class JobPost(models.Model):
    job_id                = models.PositiveIntegerField(primary_key=True, editable=False)
    employer              = models.ForeignKey(Employer, on_delete=models.CASCADE, related_name='job_posts')
    contact_email         = models.EmailField()
    is_active             = models.BooleanField(default=True)
    posted_at             = models.DateTimeField(auto_now_add=True)
    admin_review          = models.BooleanField(default=True)
    application_deadline  = models.DateField()
    title                 = models.CharField(max_length=200)
    num_candidates_required = models.PositiveIntegerField(default=1)
    industry              = models.CharField(max_length=100)
    department            = models.CharField(max_length=100)
    work_type             = models.CharField(max_length=50)
    gender_requirement    = models.CharField(max_length=50)
    experience_min        = models.PositiveIntegerField()
    experience_max        = models.PositiveIntegerField()
    experience_level      = models.CharField(max_length=50)
    salary_type           = models.CharField(max_length=50)
    salary_frequency      = models.CharField(max_length=20)
    salary_min            = models.DecimalField(max_digits=12, decimal_places=2)
    salary_max            = models.DecimalField(max_digits=12, decimal_places=2)
    requirements          = models.JSONField(default=list, blank=True)
    preferred_skills      = models.JSONField(default=list, blank=True)
    languages             = models.JSONField(default=list, blank=True)
    benefits              = models.JSONField(default=list, blank=True)
    location_type         = models.CharField(max_length=50)
    full_location_address = models.CharField(max_length=255)
    description           = models.TextField()      
    map_location          = models.JSONField(null=True, blank=True)                  


    def save(self, *args, **kwargs):
        if not self.job_id:
            last = self.__class__.objects.aggregate(max_id=Max('job_id'))['max_id'] or 999
            self.job_id = last + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.job_id} – {self.title}"

    class Meta:
        ordering = ['-posted_at']
        verbose_name = 'Job Post'
        verbose_name_plural = 'Job Posts'



class CompanyProfile(models.Model):
    employer           = models.OneToOneField(
        Employer,
        on_delete=models.CASCADE,
        related_name='company_profile'
    )
    description        = models.TextField()
    company_size       = models.CharField(max_length=50)
    founded_date       = models.DateField(null=True)
    phone_number       = models.CharField(max_length=15)
    website            = models.URLField(blank=True)
    address            = models.CharField(max_length=255)
    facebook           = models.URLField(blank=True)
    linkedin           = models.URLField(blank=True)
    logo               = models.ImageField(upload_to='company_logos/', blank=True, null=True)
    certificate        = models.FileField(upload_to='company_certificates/', blank=True, null=True)
    certificate_submitted_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.employer.email} Profile"


class EmployerPremium(models.Model):
    employer            = models.OneToOneField(
        Employer,
        on_delete=models.CASCADE,
        related_name='premium'
    )
    is_subscribed        = models.BooleanField(default=False)
    subscribed_at        = models.DateTimeField(null=True, blank=True)
    subscription_end     = models.DateTimeField(null=True, blank=True)
    payment_ok           = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employer.email} Premium: {'Active' if self.is_subscribed else 'Inactive'}"
    
