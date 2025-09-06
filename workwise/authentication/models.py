from django.db import models
from django.db.models import Max

class Candidate(models.Model):
    candidate_id  = models.PositiveIntegerField(primary_key=True)
    first_name    = models.CharField(max_length=50)
    last_name     = models.CharField(max_length=50)
    email         = models.EmailField(unique=True, max_length=254)
    password      = models.CharField(max_length=128)                 
    email_notify  = models.BooleanField(default=False)
    agree_terms   = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=False)
    is_deleted    = models.BooleanField(default=False)
    joined_time   = models.DateTimeField(auto_now_add=True)
    ip_address    = models.GenericIPAddressField(null=True, blank=True, protocol='both', unpack_ipv4=False)
    location      = models.JSONField(null=True, blank=True)  
    profile_picture   = models.ImageField(
        upload_to='profile_pictures/',
        blank=True,
        null=True
    )          

    def save(self, *args, **kwargs):
        if not self.candidate_id:
            last = self.__class__.objects.aggregate(max_id=Max('candidate_id'))['max_id'] or 999
            self.candidate_id = last + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-joined_time']
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

    def __str__(self):
        return f"{self.first_name} {self.last_name} <{self.email}>"




class Employer(models.Model):
    employer_id         = models.PositiveIntegerField(primary_key=True)
    company_name        = models.CharField(max_length=150)
    representative_name = models.CharField(max_length=100)
    email               = models.EmailField(unique=True, max_length=254)
    password            = models.CharField(max_length=128)                  
    email_notify        = models.BooleanField(default=False)
    agree_terms         = models.BooleanField(default=False)
    is_active           = models.BooleanField(default=False)
    is_deleted          = models.BooleanField(default=False)
    is_verified         = models.BooleanField(default=False)
    joined_time         = models.DateTimeField(auto_now_add=True)
    ip_address          = models.GenericIPAddressField(null=True, blank=True,
                                                      protocol='both',
                                                      unpack_ipv4=False)
    location            = models.JSONField(null=True, blank=True)           

    def save(self, *args, **kwargs):
        if not self.employer_id:
            last = self.__class__.objects.aggregate(max_id=Max('employer_id'))['max_id'] or 999
            self.employer_id = last + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['-joined_time']
        verbose_name = 'Employer'
        verbose_name_plural = 'Employers'

    def __str__(self):
        return f"{self.company_name} ({self.representative_name}) <{self.email}>"
