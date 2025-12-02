from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'users', views.AdminUserViewSet, basename='admin-user')
router.register(r'courses', views.AdminCourseViewSet, basename='admin-course')
router.register(r'courses/(?P<course_pk>[^/.]+)/modules', views.AdminCourseModuleViewSet, basename='admin-course-module')
router.register(r'modules', views.AdminModuleViewSet, basename='admin-module')
router.register(r'users', views.AdminUserViewSet, basename='admin-user')
router.register(r'community/discussions', views.DiscussionViewSet, basename='admin-discussion')
router.register(r'community/events', views.CommunityEventViewSet, basename='admin-event')



urlpatterns = [
    # Authentication
    path('auth/login/', views.AdminAuthView.as_view(), name='admin-login'),
    path('auth/logout/', views.AdminLogoutView.as_view(), name='admin-logout'),
    # Make sure you have this in adminapp/urls.py
    path('auth/profile/', views.AdminProfileView.as_view(), name='admin-profile'),
    
    # Dashboard
    path('dashboard/', views.AdminDashboardView.as_view(), name='admin-dashboard'),
    path('dashboard/course-stats/', views.AdminCourseStatsView.as_view(), name='admin-course-stats'),

    path('api/admin/modules/stats/', views.ModuleStatsView.as_view(), name='module-stats'),

    path('api/admin/community/stats/', views.CommunityStatsView.as_view(), name='community-stats'),
    
    # Analytics
    path('analytics/', views.AnalyticsView.as_view(), name='admin-analytics'),
    
    # System Management
    path('system/config/', views.SystemConfigView.as_view(), name='system-config'),
    path('system/audit-logs/', views.AuditLogView.as_view(), name='audit-logs'),
    
    # Include router URLs
    path('', include(router.urls)),
]