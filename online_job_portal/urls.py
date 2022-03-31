from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from api import views

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('', views.HomepageView.as_view(), name="home_page"),
                  path('signup/', views.CandidateSignUpView.as_view(), name="signup"),
                  path('signin/', views.CandidateSignInView.as_view(), name="signin"),
                  path('logout/', views.CandidateSignOutView.as_view(), name="logout"),
                  path('profile/', views.CandidateProfileView.as_view(), name="profile"),
                  path('joblist/', views.JobPostListView.as_view(), name="joblist"),
                  path('jobdetail/<str:pk>/', views.JobPostDetailView.as_view(), name="jobdetail"),
                  path('applicationlist/', views.JobApplicationListView.as_view(), name="applicationlist"),
                  path('savelist/', views.JobSaveListView.as_view(), name="savelist"),

              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
