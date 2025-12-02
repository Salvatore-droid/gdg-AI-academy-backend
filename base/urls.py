from django.urls import path
from . import views

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', views.login, name='login'),
    path('auth/signup/', views.signup, name='signup'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/profile/', views.profile, name='profile'),
    path('auth/change-password/', views.change_password, name='change-password'),
    
    path('dashboard/stats/', views.dashboard_stats, name='dashboard-stats'),
    path('dashboard/courses/', views.user_courses, name='user-courses'),
    path('dashboard/certificates/', views.user_certificates, name='user-certificates'),
    path('learning-paths/', views.learning_paths, name='learning-paths'),

    path('courses/', views.courses_list, name='courses-list'),
    path('courses/<uuid:course_id>/', views.course_detail, name='course-detail'),
    path('courses/<uuid:course_id>/enroll/', views.enroll_course, name='enroll-course'),
    path('courses/<uuid:course_id>/progress/', views.course_progress, name='course-progress'),

    path('modules/user-modules/', views.user_modules, name='user-modules'),
    path('modules/<uuid:module_id>/complete/', views.mark_module_complete, name='mark-module-complete'),

    path('ai-labs/', views.ai_labs_list, name='ai-labs-list'),
    path('ai-labs/<uuid:lab_id>/start/', views.start_ai_lab, name='start-ai-lab'),

    path('progress/stats/', views.progress_stats, name='progress-stats'),
    path('progress/achievements/', views.user_achievements, name='user-achievements'),
    path('certificates/<uuid:certificate_id>/download/', views.download_certificate, name='download-certificate'),

    path('community/stats/', views.community_stats, name='community-stats'),
    path('community/mentors/', views.mentors_list, name='mentors-list'),
    path('community/discussions/', views.discussions_list, name='discussions-list'),
    path('community/events/', views.events_list, name='events-list'),

    path('settings/', views.user_settings, name='user-settings'),
    path('settings/profile/', views.update_profile, name='update-profile'),

    path('debug-middleware/', views.debug_middleware, name='debug-middleware'),

]