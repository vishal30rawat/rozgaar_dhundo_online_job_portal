from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from api.models import (CustomUser, Company, JobPost, Skill, City, JobApplication)

admin.site.site_header = 'Rozgaar Dhundo: Online Job Portal'
admin.site.site_url = None

admin.site.unregister(Group)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_logo', 'email', 'mobile_number',
                    'get_total_jobs_posted', 'get_total_active_jobs')
    search_fields = ['name', ]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.annotate(total_jobs_posted=Count('companies_jobs'),
                         total_active_jobs=Count('companies_jobs',
                                                 filter=Q(companies_jobs__expired_at__gte=timezone.now())))
        return qs

    def get_logo(self, obj):
        if obj and (getattr(obj, 'logo', None) is not None):
            return format_html(f'<img src={obj.logo.url} alt="{obj.name}" width="80" height="50">')
            # pass
        return '-'

    def get_total_jobs_posted(self, obj):
        if obj and hasattr(obj, 'total_jobs_posted'):
            return obj.total_jobs_posted
        return '-'

    def get_total_active_jobs(self, obj):
        if obj and hasattr(obj, 'total_active_jobs'):
            return obj.total_active_jobs
        return '-'

    get_logo.short_description = 'Logo'
    get_total_jobs_posted.short_description = 'Total Jobs Posted'
    get_total_active_jobs.short_description = 'Total Active Jobs'


@admin.register(JobPost)
class JobPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'total_vacancies', 'can_be_remote', 'created_at', 'expired_at')
    search_fields = ['title', 'company__name']
    list_filter = ['created_at', 'expired_at', 'can_be_remote', 'skills', 'cities']


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('applicant', 'job_post', 'created_at', 'status')
    search_fields = ['applicant__first_name', 'applicant__last_name', 'job_post__title', 'job_post__company__name']
    list_filter = ['created_at', 'status', 'job_post__company']

    # def has_add_permission(self, request):
    #     return False


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_superuser', 'is_staff'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_active',)
    list_filter = ('is_superuser', 'is_active')
    search_fields = ('first_name', 'last_name', 'email')
    ordering = ('first_name',)
