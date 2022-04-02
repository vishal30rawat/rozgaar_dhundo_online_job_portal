import uuid
from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models

from api.choices import PayRollChoice, JobApplicationStatus
from api.upload_handlers import company_logo, applicant_resume, applicant_profile_picture
from strings import *


class BaseModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class CustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    username = None
    email = models.EmailField(
        error_messages={"unique": EMAIL_EXISTS},
        unique=True, db_index=True
    )
    mobile_number = models.CharField(max_length=50, null=True, blank=True)
    resume = models.FileField(null=True, blank=True, upload_to=applicant_resume,
                              validators=[FileExtensionValidator(allowed_extensions=['pdf'])])
    profile_picture = models.FileField(null=True, blank=True, upload_to=applicant_profile_picture,
                                       validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])])
    can_work_remotely = models.BooleanField(default=True)
    preferred_locations = models.ManyToManyField('City')
    skills = models.ManyToManyField('Skill')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    objects = CustomUserManager()

    def save(self, *args, **kwargs):
        if self.mobile_number:
            if CustomUser.objects.filter(mobile_number__iexact=self.mobile_number).exclude(id=self.id).exists():
                raise ValidationError(MOBILE_EXISTS)
        if self.email:
            if CustomUser.objects.filter(email__iexact=self.email).exclude(id=self.id).exists():
                raise ValidationError(EMAIL_EXISTS)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ('first_name',)
        verbose_name_plural = 'Users'
        verbose_name = 'User'


class Skill(BaseModel):
    name = models.CharField(max_length=250, unique=True,
                            error_messages={"unique": SKILL_EXISTS})

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Skills'
        verbose_name = 'Skills'


class City(BaseModel):
    name = models.CharField(max_length=250, unique=True,
                            error_messages={"unique": CITY_EXISTS})

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Cities'
        verbose_name = 'Cities'


class Company(BaseModel):
    name = models.CharField(max_length=250, unique=True,
                            error_messages={"unique": COMPANY_EXISTS})
    email = models.EmailField()
    mobile_number = models.CharField(max_length=10)
    logo = models.ImageField(null=True, blank=True, upload_to=company_logo,
                             validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg'])])

    # job post related stats are in subquery
    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Companies'
        verbose_name = 'Companies'


class JobPost(BaseModel):
    title = models.CharField(max_length=250)
    description = models.TextField()
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='companies_jobs')
    total_vacancies = models.PositiveIntegerField(default=1)
    expired_at = models.DateTimeField()
    payroll_method = models.CharField(max_length=1, choices=[i.value for i in PayRollChoice])
    pay_range_from = models.DecimalField(decimal_places=2, max_digits=10)
    pay_range_to = models.DecimalField(decimal_places=2, max_digits=10)
    can_be_remote = models.BooleanField(default=True)
    skills = models.ManyToManyField(Skill, blank=True)
    cities = models.ManyToManyField(City, blank=True)

    def __str__(self):
        return f'{self.title}-({self.company.name})'

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Job Posts'
        verbose_name = 'Job Posts'


class JobApplication(BaseModel):
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='job_applications')
    status = models.CharField(max_length=3, choices=[i.value for i in JobApplicationStatus],
                              default=JobApplicationStatus.candidate_applied.value[0])

    def __str__(self):
        return f'{self.applicant.email}-({self.job_post.title})'

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Job Applications'
        verbose_name = 'Job Applications'


class SavedJob(BaseModel):
    applicant = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    job_post = models.ForeignKey(JobPost, on_delete=models.CASCADE, related_name='saved_jobs')

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Saved Jobs'
        verbose_name = 'Saved Jobs'
