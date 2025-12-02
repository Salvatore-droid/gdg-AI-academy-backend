from django.utils import timezone
from adminapp.models import AdminAuditLog
import json
from datetime import timedelta  # <-- Add this import
from django.contrib.auth import get_user_model
from base.models import User, Course, UserSession  # <-- Add necessary imports

User = get_user_model()  # <-- Get the user model


class AdminAuditLogger:
    """
    Utility class for logging admin actions
    """
    @staticmethod
    def log_action(admin_user, action, model_name=None, object_id=None, 
                   details=None, request=None):
        """
        Log an admin action
        """
        audit_log = AdminAuditLog.objects.create(
            admin_user=admin_user,
            action=action,
            model_name=model_name or '',
            object_id=str(object_id) if object_id else '',
            details=details or {},
            ip_address=request.META.get('REMOTE_ADDR') if request else None,
            user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
        )
        return audit_log
    
    @staticmethod
    def log_user_management(admin_user, action, user, request=None):
        """Log user management actions"""
        return AdminAuditLogger.log_action(
            admin_user=admin_user,
            action=action,
            model_name='User',
            object_id=user.id,
            details={
                'user_email': user.email,
                'user_name': user.full_name,
                'action_taken': action
            },
            request=request
        )
    
    @staticmethod
    def log_course_management(admin_user, action, course, request=None):
        """Log course management actions"""
        return AdminAuditLogger.log_action(
            admin_user=admin_user,
            action=action,
            model_name='Course',
            object_id=course.id,
            details={
                'course_title': course.title,
                'course_category': course.category,
                'action_taken': action
            },
            request=request
        )



class AdminStatsCalculator:
    @staticmethod
    def get_dashboard_stats():
        """Calculate dashboard statistics"""
        today = timezone.now().date()
        yesterday = today - timedelta(days=1)  # <-- Now timedelta is defined
        
        # Get total users
        total_users = User.objects.filter(is_active=True).count()
        
        # Get active users today (users who logged in today)
        active_users_today = User.objects.filter(
            last_login__date=today
        ).count()
        
        # Get total courses
        total_courses = Course.objects.filter(is_active=True).count()
        total_active_courses = Course.objects.filter(is_active=True).count()
        
        # Get pending approvals
        from adminapp.models import CourseApproval
        pending_approvals = CourseApproval.objects.filter(
            status='pending'
        ).count()
        
        # Get total AI labs
        from base.models import AILab
        total_ai_labs = AILab.objects.filter(is_active=True).count()
        
        # Get certificates issued
        from base.models import Certificate
        total_certificates_issued = Certificate.objects.count()
        
        # Get total modules
        from base.models import CourseModule
        total_modules = CourseModule.objects.count()
        
        # Calculate engagement rate (simplified)
        total_sessions = UserSession.objects.filter(
            created_at__date=today
        ).count()
        total_logged_in_users = User.objects.filter(
            last_login__date=today
        ).count()
        
        engagement_rate = 0
        if total_users > 0:
            engagement_rate = (total_logged_in_users / total_users) * 100
        
        return {
            'total_users': total_users,
            'active_users_today': active_users_today,
            'total_courses': total_courses,
            'total_active_courses': total_active_courses,
            'pending_approvals': pending_approvals,
            'total_ai_labs': total_ai_labs,
            'total_certificates_issued': total_certificates_issued,
            'revenue_today': 0.00,
            'revenue_month': 0.00,
            'system_uptime': 99.9,
            'total_modules': total_modules,
            'engagement_rate': round(engagement_rate, 1),
        }
    
    @staticmethod
    def get_weekly_stats():
        """Get weekly statistics"""
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        # New users this week
        new_users_week = User.objects.filter(
            created_at__date__gte=week_ago
        ).count()
        
        # New courses this week
        from base.models import Course
        new_courses_week = Course.objects.filter(
            created_at__date__gte=week_ago
        ).count()
        
        # Course completions this week
        from base.models import UserCourseProgress
        completions_week = UserCourseProgress.objects.filter(
            is_completed=True,
            completed_at__date__gte=week_ago
        ).count()
        
        return {
            'new_users_week': new_users_week,
            'new_courses_week': new_courses_week,
            'completions_week': completions_week,
            'period_start': week_ago.isoformat(),
            'period_end': today.isoformat(),
        }