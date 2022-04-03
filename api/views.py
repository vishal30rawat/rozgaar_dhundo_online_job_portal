from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q, Exists, OuterRef, Subquery
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import ListView, TemplateView, DetailView
from django.contrib.auth import authenticate, login, user_logged_out

from api.choices import JobApplicationStatus
from api.models import JobPost, CustomUser, Skill, City, Company, JobApplication, SavedJob

from strings import *


class HomepageView(TemplateView):
    template_name = 'api/home_page.html'

    def get_context_data(self, **kwargs):
        context_data = super(HomepageView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data


class CandidateProfileView(LoginRequiredMixin, TemplateView):
    template_name = 'api/profile.html'
    login_url = '/signin/'

    def get_context_data(self, **kwargs):
        context_data = super(CandidateProfileView, self).get_context_data(**kwargs)
        skills = Skill.objects.all().annotate(is_added=Exists(self.request.user.skills.filter(id=OuterRef('id'))))
        cities = City.objects.all().annotate(
            is_added=Exists(self.request.user.preferred_locations.filter(id=OuterRef('id'))))
        extra_context = {
            'skills': skills.values('id', 'name', 'is_added'),
            'cities': cities.values('id', 'name', 'is_added'),
        }
        context_data.update(extra_context)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data

    @transaction.atomic
    def post(self, request):
        user = self.request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.mobile_number = request.POST.get('mobile_number', user.mobile_number)
        user.can_work_remotely = str(request.POST.get('first_name', user.first_name)).lower() in (
            "yes", "true", "t", "1")
        user.resume = request.FILES.get('resume', user.resume)
        user.profile_picture = request.FILES.get('profile_picture', user.profile_picture)
        user.save(update_fields=['first_name', 'last_name', 'mobile_number',
                                 'profile_picture', 'resume', 'can_work_remotely'])
        skills = Skill.objects.filter(id__in=request.POST.getlist('skill'))
        preferred_locations = City.objects.filter(id__in=request.POST.getlist('location'))
        user.skills.set(skills)
        user.preferred_locations.set(preferred_locations)
        return redirect('profile')


class CandidateSignUpView(TemplateView):
    template_name = 'api/sign_up.html'

    def get_context_data(self, **kwargs):
        context_data = super(CandidateSignUpView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data

    @transaction.atomic
    def post(self, request):
        try:
            user = CustomUser.objects.create_user(
                email=request.POST['email'],
                password=request.POST['password'],
                **{
                    'first_name': request.POST['first_name'],
                    'last_name': request.POST['last_name'],
                }
            )
            if user is not None:
                login(request, user)
                current_date_time = timezone.now()
                CustomUser.objects.filter(id=user.id).update(last_login=current_date_time,
                                                             date_joined=current_date_time)
                return redirect('profile')
        except Exception as e:
            message = getattr(e, 'message', GENERIC_ERROR)
            return render(request, self.template_name, context={'message': message})


class CandidateSignInView(TemplateView):
    template_name = 'api/sign_in.html'

    def get_context_data(self, **kwargs):
        context_data = super(CandidateSignInView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data

    def post(self, request):
        user = authenticate(
            email=request.POST['email'],
            password=request.POST['password'],
        )
        if user is not None:
            login(request, user)
            CustomUser.objects.filter(id=user.id).update(last_login=timezone.now())
            return redirect('joblist')
        message = FAILED_LOGIN
        return render(request, self.template_name, context={'message': message})


class CandidateSignOutView(LoginRequiredMixin, TemplateView):
    template_name = 'api/home_page.html'
    login_url = '/signin/'

    def get(self, request, *args, **kwargs):
        user = getattr(request, 'user', None)
        if not getattr(user, 'is_authenticated', False):
            user = None
        user_logged_out.send(sender=user.__class__, request=request, user=user)
        request.session.flush()
        if hasattr(request, 'user'):
            request.user = None
        return redirect('home_page')


class JobPostListView(LoginRequiredMixin, ListView):
    login_url = '/signin/'
    template_name = 'api/job_list.html'
    model = JobPost
    paginate_by = 10
    context_object_name = 'job_posts'
    queryset = JobPost.objects.all()
    extra_context = {
        'skills': Skill.objects.all().values('id', 'name'),
        'cities': City.objects.all().values('id', 'name'),
        'companies': Company.objects.all().values('id', 'name'),
    }

    def get_queryset(self):
        qs = super(JobPostListView, self).get_queryset()
        qs = qs.filter(expired_at__gte=timezone.now()).defer('description').select_related('company')
        skills = self.request.GET.getlist("skill")
        cities = self.request.GET.getlist("city")
        companies = self.request.GET.getlist("company")
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        search = self.request.GET.get('search')

        if from_date:
            qs = qs.filter(created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(created_at__date__lte=to_date)
        if self.request.GET.get("is_remote", None):
            is_remote = self.request.GET.get("is_remote").lower() in ("yes", "true", "t", "1")
            qs = qs.filter(can_be_remote=is_remote)
        if skills:
            qs = qs.filter(skills__in=skills)
        if cities:
            qs = qs.filter(cities__in=cities)
        if companies:
            qs = qs.filter(company_id__in=companies)
        if search:
            qs = qs.filter(Q(title__icontains=search) |
                           Q(company__name__icontains=search) |
                           Q(description__icontains=search))
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context_data = super(JobPostListView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data


class JobPostDetailView(LoginRequiredMixin, DetailView):
    login_url = '/signin/'
    template_name = 'api/job_detail.html'
    model = JobPost
    context_object_name = 'job_post'
    queryset = JobPost.objects.all().select_related('company')

    def get_queryset(self):
        qs = super(JobPostDetailView, self).get_queryset()
        qs = qs.annotate(
            is_applied=Exists(JobApplication.objects.filter(job_post_id=OuterRef('id'),
                                                            applicant_id=self.request.user.id)),
            is_saved=Exists(SavedJob.objects.filter(job_post_id=OuterRef('id'),
                                                    applicant_id=self.request.user.id)))
        return qs

    def get_context_data(self, **kwargs):
        context_data = super(JobPostDetailView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data


class JobApplicationListView(LoginRequiredMixin, ListView):
    login_url = '/signin/'
    template_name = 'api/application_list.html'
    model = JobPost
    paginate_by = 10
    context_object_name = 'job_posts'
    queryset = JobPost.objects.all()
    extra_context = {
        'skills': Skill.objects.all().values('id', 'name'),
        'cities': City.objects.all().values('id', 'name'),
        'companies': Company.objects.all().values('id', 'name'),
    }

    def get_queryset(self):
        qs = super(JobApplicationListView, self).get_queryset()
        qs = qs.annotate(is_applied=Exists(JobApplication.objects.filter(job_post_id=OuterRef('id'),
                                                                         applicant_id=self.request.user.id)))
        qs = qs.filter(is_applied=True, expired_at__gte=timezone.now()).defer('description').select_related('company')
        skills = self.request.GET.getlist("skill")
        cities = self.request.GET.getlist("city")
        companies = self.request.GET.getlist("company")
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        search = self.request.GET.get('search')
        status = self.request.GET.get('status')

        if from_date:
            qs = qs.filter(job_applications__created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(job_applications__created_at__date__lte=to_date)
        if status:
            qs = qs.filter(job_applications__status=status)
        if self.request.GET.get("is_remote", None):
            is_remote = self.request.GET.get("is_remote").lower() in ("yes", "true", "t", "1")
            qs = qs.filter(can_be_remote=is_remote)
        if skills:
            qs = qs.filter(skills__in=skills)
        if cities:
            qs = qs.filter(cities__in=cities)
        if companies:
            qs = qs.filter(company_id__in=companies)
        if search:
            qs = qs.filter(Q(title__icontains=search) |
                           Q(company__name__icontains=search) |
                           Q(description__icontains=search))

        applied_on = JobApplication.objects.filter(job_post_id=OuterRef('id'),
                                                   applicant_id=self.request.user.id).values('created_at')[:1]
        applied_status = JobApplication.objects.filter(job_post_id=OuterRef('id'),
                                                       applicant_id=self.request.user.id).values('status')[:1]
        qs = qs.annotate(applied_on=Subquery(applied_on), applied_status=Subquery(applied_status))
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context_data = super(JobApplicationListView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data

    @transaction.atomic
    def post(self, request):
        applicant = request.user
        job_post = request.POST['job_post']
        if request.POST.get('is_applying', 'False').lower() in ("yes", "true", "t", "1"):
            job_post = JobPost.objects.get(id=request.POST['job_post'])
            JobApplication.objects.get_or_create(applicant=applicant, job_post=job_post,
                                                 status=JobApplicationStatus.candidate_applied.value[0])
        else:
            JobApplication.objects.filter(applicant_id=applicant.id, job_post_id=job_post).delete()
        return redirect('applicationlist')


class JobSaveListView(LoginRequiredMixin, ListView):
    login_url = '/signin/'
    template_name = 'api/save_list.html'
    model = JobPost
    paginate_by = 10
    context_object_name = 'job_posts'
    queryset = JobPost.objects.all()
    extra_context = {
        'skills': Skill.objects.all().values('id', 'name'),
        'cities': City.objects.all().values('id', 'name'),
        'companies': Company.objects.all().values('id', 'name'),
    }

    def get_queryset(self):
        qs = super(JobSaveListView, self).get_queryset()
        qs = qs.annotate(is_saved=Exists(SavedJob.objects.filter(job_post_id=OuterRef('id'),
                                                                 applicant_id=self.request.user.id)))
        qs = qs.filter(is_saved=True, expired_at__gte=timezone.now()).defer('description').select_related('company')
        skills = self.request.GET.getlist("skill")
        cities = self.request.GET.getlist("city")
        companies = self.request.GET.getlist("company")
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')
        search = self.request.GET.get('search')

        if from_date:
            qs = qs.filter(saved_jobs__created_at__date__gte=from_date)
        if to_date:
            qs = qs.filter(saved_jobs__created_at__date__lte=to_date)

        if self.request.GET.get("is_remote", None):
            is_remote = self.request.GET.get("is_remote").lower() in ("yes", "true", "t", "1")
            qs = qs.filter(can_be_remote=is_remote)
        if skills:
            qs = qs.filter(skills__in=skills)
        if cities:
            qs = qs.filter(cities__in=cities)
        if companies:
            qs = qs.filter(company_id__in=companies)
        if search:
            qs = qs.filter(Q(title__icontains=search) |
                           Q(company__name__icontains=search) |
                           Q(description__icontains=search))

        saved_on = SavedJob.objects.filter(job_post_id=OuterRef('id'),
                                           applicant_id=self.request.user.id).values('created_at')[:1]
        qs = qs.annotate(saved_on=Subquery(saved_on))
        return qs.distinct()

    def get_context_data(self, **kwargs):
        context_data = super(JobSaveListView, self).get_context_data(**kwargs)
        user = self.request.user
        if not self.request.user.is_authenticated:
            user = None
        context_data.update({'user': user})
        return context_data

    @transaction.atomic
    def post(self, request):
        applicant = request.user
        job_post = request.POST['job_post']
        if request.POST.get('is_saving', 'False').lower() in ("yes", "true", "t", "1"):
            job_post = JobPost.objects.get(id=request.POST['job_post'])
            SavedJob.objects.get_or_create(applicant=applicant, job_post=job_post)
        else:
            SavedJob.objects.filter(applicant_id=applicant.id, job_post_id=job_post).delete()
        return redirect('savelist')
