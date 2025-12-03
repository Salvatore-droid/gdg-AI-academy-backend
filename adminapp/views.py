from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Q, Sum, F
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from django.conf import settings
from base.models import (
    User, UserSession, Course, AILab, Certificate, 
    UserCourseProgress, UserLearningStats, LearningPath
)
from adminapp.models import AdminAuditLog, SystemConfig, CourseApproval
from adminapp.serializers import *
from adminapp.permissions import IsAdminUser, IsSuperAdmin
from adminapp.utils import AdminAuditLogger, AdminStatsCalculator
from rest_framework.authentication import SessionAuthentication, BasicAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from datetime import timedelta
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

User = get_user_model()


# ==================== Admin Authentication Views ====================
class AdminAuthView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        """Admin login"""
        serializer = AdminLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            admin_user = serializer.validated_data['admin_user']
            
            # Update last login
            admin_user.update_last_login()
            
            # Create session
            session = UserSession.create_session(admin_user)
            
            # Log the login action
            AdminAuditLogger.log_action(
                admin_user=admin_user,
                action='admin_login',
                request=request
            )
            
            # Prepare response
            response_data = {
                'admin_user': AdminUserSerializer(admin_user).data,
                'token': session.token,
                'message': 'Admin login successful',
                'is_admin': True
            }
            
            response = Response(response_data, status=status.HTTP_200_OK)
            
            # Set cookie for admin token (optional)
            response.set_cookie(
                key='admin_token',
                value=session.token,
                httponly=True,
                secure=not settings.DEBUG,
                samesite='Strict',
                max_age=7*24*60*60  # 7 days
            )
            
            return response
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class AdminLogoutView(APIView):
    permission_classes = [IsAdminUser]
    
    def post(self, request):
        """Admin logout"""
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Invalidate session
                session = UserSession.objects.get(token=token, is_active=True)
                
                # Log the logout action
                AdminAuditLogger.log_action(
                    admin_user=request.user,
                    action='admin_logout',
                    request=request
                )
                
                session.invalidate()
            except UserSession.DoesNotExist:
                pass
        
        response = Response(
            {'message': 'Admin logout successful'},
            status=status.HTTP_200_OK
        )
        
        # Clear admin token cookie
        response.delete_cookie('admin_token')
        
        return response

class AdminProfileView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get admin profile information"""
        print(f"=== AdminProfileView ===")
        print(f"User: {request.user.email}")
        print(f"Is staff: {request.user.is_staff}")
        
        return Response(
            AdminUserSerializer(request.user).data,
            status=status.HTTP_200_OK
        )

# ==================== Admin Dashboard Views ====================
class AdminDashboardView(APIView):
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    
    def get(self, request):
        """Get admin dashboard statistics"""
        print(f"=== AdminDashboardView ===")
        print(f"Request user: {request.user}")
        print(f"User email: {request.user.email}")
        print(f"Is authenticated: {request.user.is_authenticated}")
        print(f"Is staff: {request.user.is_staff}")
        print(f"Is superuser: {request.user.is_superuser}")
        print(f"Token from header: {request.headers.get('Authorization', 'No token')}")
        
        try:
            from adminapp.utils import AdminStatsCalculator
            stats = AdminStatsCalculator.get_dashboard_stats()
            serializer = AdminDashboardStatsSerializer(stats)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            print(f"Error in AdminDashboardView: {str(e)}")
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

from adminapp.authentication import CsrfExemptSessionAuthentication

class AdminUserViewSet(viewsets.ModelViewSet):
    authentication_classes = [CsrfExemptSessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated, IsAdminUser]
    serializer_class = AdminUserSerializer

    # @method_decorator(csrf_exempt, name='dispatch')
    # def dispatch(self, *args, **kwargs):
    #     return super().dispatch(*args, **kwargs)
    
    # Add this queryset attribute
    queryset = User.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AdminUserCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return AdminUserUpdateSerializer  # IMPORTANT: Use update serializer
        return AdminUserSerializer
    
    def get_queryset(self):
        """Override to add annotations for stats"""
        queryset = User.objects.all().order_by('-created_at')
        
        # Annotate with course stats
        from django.db.models import Count, Sum, Q
        from base.models import UserCourseProgress, Certificate, UserLearningStats
        
        # Get course progress counts
        course_progress = UserCourseProgress.objects.values('user').annotate(
            total_enrolled=Count('id', distinct=True),
            total_completed=Count('id', filter=Q(is_completed=True), distinct=True)
        )
        
        # Create a mapping for quick lookup
        user_stats = {}
        for stat in course_progress:
            user_stats[stat['user']] = {
                'enrolled': stat.get('total_enrolled', 0),
                'completed': stat.get('total_completed', 0)
            }
        
        # We'll handle the annotation in the serializer instead
        return queryset
    
    def list(self, request):
        """List users with filtering and pagination"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        is_active = request.query_params.get('is_active')
        is_staff = request.query_params.get('is_staff')
        search = request.query_params.get('search')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
        if search:
            queryset = queryset.filter(
                Q(email__icontains=search) |
                Q(full_name__icontains=search)
            )
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj, many=True)
        
        return Response({
            'users': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_users': paginator.count,
            'per_page': per_page
        })

        
    # @method_decorator(csrf_exempt)
    def create(self, request):
        """Create a new user (admin or regular)"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Log the action
            AdminAuditLogger.log_user_management(
                admin_user=request.user,
                action='user_created',
                user=user,
                request=request
            )
            
            return Response(
                AdminUserSerializer(user).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def activate(self, request, pk=None):
        """Activate a user account"""
        user = self.get_object()
        user.is_active = True
        user.save()
        
        AdminAuditLogger.log_user_management(
            admin_user=request.user,
            action='user_activated',
            user=user,
            request=request
        )
        
        return Response(
            {'message': 'User activated successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def deactivate(self, request, pk=None):
        """Deactivate a user account"""
        user = self.get_object()
        user.is_active = False
        user.save()
        
        # Invalidate all active sessions
        UserSession.objects.filter(user=user, is_active=True).update(is_active=False)
        
        AdminAuditLogger.log_user_management(
            admin_user=request.user,
            action='user_deactivated',
            user=user,
            request=request
        )
        
        return Response(
            {'message': 'User deactivated successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def promote_to_admin(self, request, pk=None):
        """Promote user to admin"""
        user = self.get_object()
        user.is_staff = True
        user.save()
        
        AdminAuditLogger.log_user_management(
            admin_user=request.user,
            action='user_promoted_to_admin',
            user=user,
            request=request
        )
        
        return Response(
            {'message': 'User promoted to admin successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get user statistics"""
        from django.utils import timezone
        from datetime import timedelta
        
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        admin_users = User.objects.filter(is_staff=True).count()
        
        # New users today
        today = timezone.now().date()
        new_users_today = User.objects.filter(created_at__date=today).count()
        
        # New users this week
        week_ago = timezone.now() - timedelta(days=7)
        new_users_week = User.objects.filter(created_at__gte=week_ago).count()
        
        # Total learning hours
        from base.models import UserLearningStats
        total_learning_hours = UserLearningStats.objects.aggregate(
            total_hours=Sum('total_learning_hours')
        )['total_hours'] or 0
        
        # Top learners
        top_learners = UserLearningStats.objects.select_related('user').order_by('-total_learning_hours')[:5]
        
        top_learners_data = []
        for stats in top_learners:
            top_learners_data.append({
                'id': str(stats.user.id),
                'full_name': stats.user.full_name,
                'total_learning_hours': stats.total_learning_hours,
                'courses_completed': stats.total_courses_completed,
            })
        
        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'new_users_today': new_users_today,
            'new_users_week': new_users_week,
            'total_learning_hours': total_learning_hours,
            'top_learners': top_learners_data,
        })
    
    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """Activate multiple users"""
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'error': 'No user IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(id__in=user_ids)
        updated_count = users.update(is_active=True)
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='users_bulk_activated',
            model_name='User',
            details={
                'count': updated_count,
                'user_ids': user_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully activated {updated_count} users',
            'activated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        """Deactivate multiple users"""
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'error': 'No user IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(id__in=user_ids)
        updated_count = users.update(is_active=False)
        
        # Invalidate all active sessions for deactivated users
        UserSession.objects.filter(user__in=users, is_active=True).update(is_active=False)
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='users_bulk_deactivated',
            model_name='User',
            details={
                'count': updated_count,
                'user_ids': user_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deactivated {updated_count} users',
            'deactivated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Delete multiple users"""
        user_ids = request.data.get('user_ids', [])
        
        if not user_ids:
            return Response(
                {'error': 'No user IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        users = User.objects.filter(id__in=user_ids)
        deleted_count = users.count()
        
        # Soft delete (deactivate) instead of actual delete
        users.update(is_active=False)
        
        # Invalidate all sessions
        UserSession.objects.filter(user__in=users, is_active=True).update(is_active=False)
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='users_bulk_deleted',
            model_name='User',
            details={
                'count': deleted_count,
                'user_ids': user_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deleted {deleted_count} users',
            'deleted_count': deleted_count
        })
    
    @action(detail=False, methods=['post'])
    def send_welcome(self, request):
        """Send welcome email to user"""
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'User ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(id=user_id)
            # TODO: Implement email sending logic
            # send_welcome_email(user.email, user.full_name)
            
            AdminAuditLogger.log_action(
                admin_user=request.user,
                action='welcome_email_sent',
                model_name='User',
                object_id=user_id,
                details={'email': user.email},
                request=request
            )
            
            return Response(
                {'message': 'Welcome email sent successfully'},
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'},
                status=status.HTTP_404_NOT_FOUND
            )

# ==================== Course Management Views ====================
# In your views.py, modify the AdminCourseViewSet list method:

class AdminCourseViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    queryset = Course.objects.all().order_by('-created_at')
    serializer_class = AdminCourseSerializer
    
    def list(self, request):
        """List courses with statistics"""
        print(f"=== AdminCourseViewSet.list() ===")
        print(f"Request user: {request.user}")
        print(f"User email: {request.user.email if request.user else 'No user'}")
        print(f"Is authenticated: {request.user.is_authenticated if request.user else False}")
        print(f"Authorization header: {request.headers.get('Authorization', 'No header')}")
        
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        is_active = request.query_params.get('is_active')
        is_staff = request.query_params.get('is_staff')
        search = request.query_params.get('search')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if is_staff is not None:
            queryset = queryset.filter(is_staff=is_staff.lower() == 'true')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj, many=True)
        
        # Add course statistics to each course
        courses_with_stats = []
        for course in page_obj:
            course_data = serializer.data
            # You'll need to fetch these from your serializer or calculate here
            courses_with_stats.append(course_data)
        
        return Response({
            'courses': courses_with_stats,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_courses': paginator.count,
            'per_page': per_page
        })
    
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """Approve a course"""
        course = self.get_object()
        
        approval, created = CourseApproval.objects.get_or_create(course=course)
        approval.status = 'approved'
        approval.reviewed_by = request.user
        approval.review_notes = request.data.get('notes', '')
        approval.reviewed_at = timezone.now()
        approval.save()
        
        # Activate the course if it was inactive
        if not course.is_active:
            course.is_active = True
            course.save()
        
        AdminAuditLogger.log_course_management(
            admin_user=request.user,
            action='course_approved',
            course=course,
            request=request
        )
        
        return Response(
            {'message': 'Course approved successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """Reject a course"""
        course = self.get_object()
        
        approval, created = CourseApproval.objects.get_or_create(course=course)
        approval.status = 'rejected'
        approval.reviewed_by = request.user
        approval.review_notes = request.data.get('notes', '')
        approval.reviewed_at = timezone.now()
        approval.save()
        
        # Deactivate the course
        course.is_active = False
        course.save()
        
        AdminAuditLogger.log_course_management(
            admin_user=request.user,
            action='course_rejected',
            course=course,
            request=request
        )
        
        return Response(
            {'message': 'Course rejected successfully'},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """Activate multiple courses"""
        course_ids = request.data.get('course_ids', [])
        
        if not course_ids:
            return Response(
                {'error': 'No course IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        courses = Course.objects.filter(id__in=course_ids)
        updated_count = courses.update(is_active=True)
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='courses_bulk_activated',
            model_name='Course',
            details={
                'count': updated_count,
                'course_ids': course_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully activated {updated_count} courses',
            'activated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        """Deactivate multiple courses"""
        course_ids = request.data.get('course_ids', [])
        
        if not course_ids:
            return Response(
                {'error': 'No course IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        courses = Course.objects.filter(id__in=course_ids)
        updated_count = courses.update(is_active=False)
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='courses_bulk_deactivated',
            model_name='Course',
            details={
                'count': updated_count,
                'course_ids': course_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deactivated {updated_count} courses',
            'deactivated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Delete multiple courses (soft delete)"""
        course_ids = request.data.get('course_ids', [])
        
        if not course_ids:
            return Response(
                {'error': 'No course IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete by deactivating
        courses = Course.objects.filter(id__in=course_ids)
        deleted_count = courses.count()
        courses.update(is_active=False)
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='courses_bulk_deleted',
            model_name='Course',
            details={
                'count': deleted_count,
                'course_ids': course_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deleted {deleted_count} courses',
            'deleted_count': deleted_count
        })

# ==================== System Management Views ====================
class SystemConfigView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Get all system configurations"""
        configs = SystemConfig.objects.all()
        serializer = SystemConfigSerializer(configs, many=True)
        return Response(serializer.data)
    
    def put(self, request):
        """Update system configurations"""
        configs_data = request.data
        
        for key, value in configs_data.items():
            config, created = SystemConfig.objects.update_or_create(
                key=key,
                defaults={
                    'value': value,
                    'updated_by': request.user
                }
            )
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='system_config_updated',
            details={'updated_keys': list(configs_data.keys())},
            request=request
        )
        
        return Response(
            {'message': 'System configurations updated successfully'},
            status=status.HTTP_200_OK
        )

class AuditLogView(APIView):
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Get audit logs with filtering"""
        logs = AdminAuditLog.objects.all().order_by('-created_at')
        
        # Apply filters
        admin_user_id = request.query_params.get('admin_user_id')
        action = request.query_params.get('action')
        model_name = request.query_params.get('model_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        if admin_user_id:
            logs = logs.filter(admin_user_id=admin_user_id)
        if action:
            logs = logs.filter(action=action)
        if model_name:
            logs = logs.filter(model_name=model_name)
        if start_date:
            logs = logs.filter(created_at__date__gte=start_date)
        if end_date:
            logs = logs.filter(created_at__date__lte=end_date)
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 50)
        
        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = AuditLogSerializer(page_obj, many=True)
        
        return Response({
            'logs': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_logs': paginator.count,
            'per_page': per_page
        })

# ==================== Analytics Views ====================
class AnalyticsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get analytics data"""
        from datetime import datetime, timedelta
        
        # Get date range
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        
        # User growth data
        user_growth = []
        current_date = start_date
        while current_date <= end_date:
            count = User.objects.filter(
                created_at__date__lte=current_date
            ).count()
            user_growth.append({
                'date': current_date.isoformat(),
                'count': count
            })
            current_date += timedelta(days=1)
        
        # Course enrollment data
        course_enrollment = []
        courses = Course.objects.filter(is_active=True)[:10]
        for course in courses:
            enrolled = UserCourseProgress.objects.filter(course=course).count()
            completed = UserCourseProgress.objects.filter(
                course=course, 
                is_completed=True
            ).count()
            course_enrollment.append({
                'course_id': str(course.id),
                'course_title': course.title,
                'enrolled': enrolled,
                'completed': completed,
                'completion_rate': (completed / enrolled * 100) if enrolled > 0 else 0
            })
        
        # Active users by day
        active_users = []
        current_date = end_date - timedelta(days=7)
        while current_date <= end_date:
            count = User.objects.filter(
                last_login__date=current_date
            ).count()
            active_users.append({
                'date': current_date.isoformat(),
                'count': count
            })
            current_date += timedelta(days=1)
        
        return Response({
            'user_growth': user_growth,
            'course_enrollment': course_enrollment,
            'active_users': active_users,
            'time_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        })

# ==================== Course Module Management Views ====================
class AdminCourseModuleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    serializer_class = AdminCourseModuleSerializer

    def get_queryset(self):
        return CourseModule.objects.filter(
            course_id=self.kwargs.get('course_pk')
        ).select_related('course').order_by('order')
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseModuleCreateSerializer
        return CourseModuleSerializer
    
    def list(self, request, course_pk=None):
        """List all modules for a specific course"""
        try:
            course = Course.objects.get(id=course_pk)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        modules = self.get_queryset()
        serializer = self.get_serializer(modules, many=True)
        
        return Response({
            'course': {
                'id': str(course.id),
                'title': course.title,
            },
            'modules': serializer.data
        })
    
    def create(self, request, course_pk=None):
        """Create a new module for a course"""
        try:
            course = Course.objects.get(id=course_pk)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            module = serializer.save(course=course)
            
            # Log the action
            AdminAuditLogger.log_action(
                admin_user=request.user,
                action='module_created',
                model_name='CourseModule',
                object_id=module.id,
                details={
                    'course_title': course.title,
                    'module_title': module.title,
                },
                request=request
            )
            
            return Response(
                CourseModuleSerializer(module).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# ==================== Course Management Enhanced Views ====================
class AdminCourseStatsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get course statistics for admin dashboard"""
        from datetime import datetime, timedelta
        
        today = timezone.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Total courses
        total_courses = Course.objects.count()
        active_courses = Course.objects.filter(is_active=True).count()
        
        # New courses in last 30 days
        new_courses = Course.objects.filter(created_at__date__gte=last_30_days).count()
        
        # Course enrollment stats
        course_enrollment = Course.objects.annotate(
            enrolled_count=Count('user_progress')
        ).order_by('-enrolled_count')[:10]
        
        enrollment_data = []
        for course in course_enrollment:
            enrollment_data.append({
                'id': str(course.id),
                'title': course.title,
                'enrolled': course.enrolled_count,
                'category': course.category,
            })
        
        # Course completion stats
        completion_stats = []
        for course in Course.objects.all()[:10]:
            total_enrolled = UserCourseProgress.objects.filter(course=course).count()
            completed = UserCourseProgress.objects.filter(course=course, is_completed=True).count()
            completion_rate = (completed / total_enrolled * 100) if total_enrolled > 0 else 0
            
            completion_stats.append({
                'id': str(course.id),
                'title': course.title,
                'total_enrolled': total_enrolled,
                'completed': completed,
                'completion_rate': round(completion_rate, 1)
            })
        
        return Response({
            'total_courses': total_courses,
            'active_courses': active_courses,
            'new_courses': new_courses,
            'top_enrolled_courses': enrollment_data,
            'completion_stats': completion_stats,
        })

class AdminModuleViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    queryset = CourseModule.objects.all().select_related('course').order_by('course', 'order')
    serializer_class = AdminCourseModuleSerializer
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return CourseModuleCreateSerializer
        return AdminCourseModuleSerializer
    
    def list(self, request):
        """List modules with filtering"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        course_id = request.query_params.get('course_id')
        content_type = request.query_params.get('content_type')
        is_active = request.query_params.get('is_active')
        search = request.query_params.get('search')
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if content_type:
            queryset = queryset.filter(content_type=content_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj, many=True)
        
        return Response({
            'modules': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_modules': paginator.count,
            'per_page': per_page
        })
    
    def create(self, request):
        """Create a new module"""
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            module = serializer.save(course_id=request.data.get('course_id'))
            
            AdminAuditLogger.log_action(
                admin_user=request.user,
                action='module_created',
                model_name='CourseModule',
                object_id=module.id,
                details={
                    'course_title': module.course.title,
                    'module_title': module.title,
                },
                request=request
            )
            
            return Response(
                AdminCourseModuleSerializer(module).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def reorder(self, request, pk=None):
        """Reorder module position"""
        module = self.get_object()
        direction = request.data.get('direction')
        
        if direction == 'up' and module.order > 1:
            # Swap with module above
            prev_module = CourseModule.objects.filter(
                course=module.course,
                order=module.order - 1
            ).first()
            if prev_module:
                prev_module.order, module.order = module.order, prev_module.order
                prev_module.save()
                module.save()
        elif direction == 'down':
            # Swap with module below
            next_module = CourseModule.objects.filter(
                course=module.course,
                order=module.order + 1
            ).first()
            if next_module:
                next_module.order, module.order = module.order, next_module.order
                next_module.save()
                module.save()
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='module_reordered',
            model_name='CourseModule',
            object_id=module.id,
            details={
                'direction': direction,
                'new_order': module.order,
            },
            request=request
        )
        
        return Response(
            {'message': 'Module order updated', 'order': module.order},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['post'])
    def bulk_activate(self, request):
        """Activate multiple modules"""
        module_ids = request.data.get('module_ids', [])
        
        if not module_ids:
            return Response(
                {'error': 'No module IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        modules = CourseModule.objects.filter(id__in=module_ids)
        updated_count = modules.update(is_active=True)
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='modules_bulk_activated',
            model_name='CourseModule',
            details={
                'count': updated_count,
                'module_ids': module_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully activated {updated_count} modules',
            'activated_count': updated_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_deactivate(self, request):
        """Deactivate multiple modules"""
        module_ids = request.data.get('module_ids', [])
        
        if not module_ids:
            return Response(
                {'error': 'No module IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        modules = CourseModule.objects.filter(id__in=module_ids)
        updated_count = modules.update(is_active=False)
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='modules_bulk_deactivated',
            model_name='CourseModule',
            details={
                'count': updated_count,
                'module_ids': module_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deactivated {updated_count} modules',
            'deactivated_count': updated_count
        })
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Delete multiple modules"""
        module_ids = request.data.get('module_ids', [])
        
        if not module_ids:
            return Response(
                {'error': 'No module IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        modules = CourseModule.objects.filter(id__in=module_ids)
        deleted_count = modules.count()
        modules.delete()
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='modules_bulk_deleted',
            model_name='CourseModule',
            details={
                'count': deleted_count,
                'module_ids': module_ids,
            },
            request=request
        )
        
        return Response({
            'message': f'Successfully deleted {deleted_count} modules',
            'deleted_count': deleted_count
        })


class ModuleStatsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get module statistics"""
        total_modules = CourseModule.objects.count()
        active_modules = CourseModule.objects.filter(is_active=True).count()
        
        # Calculate total duration
        total_duration = CourseModule.objects.aggregate(
            total_duration=Sum('duration_minutes')
        )['total_duration'] or 0
        
        # Modules by content type
        modules_by_type = CourseModule.objects.values('content_type').annotate(
            count=Count('id')
        )
        
        type_stats = {}
        for item in modules_by_type:
            type_stats[item['content_type']] = item['count']
        
        return Response({
            'total_modules': total_modules,
            'active_modules': active_modules,
            'total_duration': total_duration,
            'modules_by_type': type_stats,
        })

from base.models import Discussion, CommunityEvent, EventAttendance
from django.db.models import Count, Q
from datetime import datetime, timedelta

class DiscussionViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    queryset = Discussion.objects.all().select_related('author', 'course').order_by('-created_at')
    serializer_class = DiscussionSerializer
    
    def list(self, request):
        """List discussions with filtering"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        status = request.query_params.get('status')
        is_flagged = request.query_params.get('is_flagged')
        course_id = request.query_params.get('course_id')
        search = request.query_params.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if is_flagged is not None:
            queryset = queryset.filter(is_flagged=is_flagged.lower() == 'true')
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(content__icontains=search) |
                Q(author__full_name__icontains=search)
            )
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj, many=True)
        
        return Response({
            'discussions': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_discussions': paginator.count,
            'per_page': per_page
        })
    
    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        """Flag a discussion"""
        discussion = self.get_object()
        reason = request.data.get('reason', '')
        action = request.data.get('action', 'warn')
        message = request.data.get('message', '')
        
        discussion.is_flagged = True
        discussion.flag_reason = reason
        
        if action == 'lock':
            discussion.status = 'locked'
        elif action == 'archive':
            discussion.status = 'archived'
        
        discussion.save()
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='discussion_flagged',
            model_name='Discussion',
            object_id=discussion.id,
            details={
                'reason': reason,
                'action_taken': action,
                'message': message,
            },
            request=request
        )
        
        return Response(
            {'message': 'Discussion flagged successfully'},
            status=status.HTTP_200_OK
        )
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Delete multiple discussions"""
        discussion_ids = request.data.get('ids', [])
        
        if not discussion_ids:
            return Response(
                {'error': 'No discussion IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discussions = Discussion.objects.filter(id__in=discussion_ids)
        deleted_count = discussions.count()
        discussions.delete()
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='discussions_bulk_deleted',
            model_name='Discussion',
            details={'count': deleted_count},
            request=request
        )
        
        return Response({
            'message': f'Successfully deleted {deleted_count} discussions',
            'deleted_count': deleted_count
        })
    
    @action(detail=False, methods=['post'])
    def bulk_approve(self, request):
        """Approve multiple discussions"""
        discussion_ids = request.data.get('ids', [])
        
        if not discussion_ids:
            return Response(
                {'error': 'No discussion IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        discussions = Discussion.objects.filter(id__in=discussion_ids)
        updated_count = discussions.update(is_flagged=False, status='active')
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='discussions_bulk_approved',
            model_name='Discussion',
            details={'count': updated_count},
            request=request
        )
        
        return Response({
            'message': f'Successfully approved {updated_count} discussions',
            'approved_count': updated_count
        })

class CommunityEventViewSet(viewsets.ModelViewSet):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    queryset = CommunityEvent.objects.all().select_related('host').order_by('start_date')
    serializer_class = CommunityEventSerializer
    
    def list(self, request):
        """List community events with filtering"""
        queryset = self.filter_queryset(self.get_queryset())
        
        # Apply filters
        status = request.query_params.get('status')
        event_type = request.query_params.get('event_type')
        search = request.query_params.get('search')
        
        if status:
            queryset = queryset.filter(status=status)
        if event_type:
            queryset = queryset.filter(event_type=event_type)
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(host__full_name__icontains=search)
            )
        
        # Pagination
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 20)
        
        paginator = Paginator(queryset, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = self.get_serializer(page_obj, many=True)
        
        return Response({
            'events': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_events': paginator.count,
            'per_page': per_page
        })
    
    @action(detail=False, methods=['delete'])
    def bulk_delete(self, request):
        """Delete multiple events"""
        event_ids = request.data.get('ids', [])
        
        if not event_ids:
            return Response(
                {'error': 'No event IDs provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        events = CommunityEvent.objects.filter(id__in=event_ids)
        deleted_count = events.count()
        events.delete()
        
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='events_bulk_deleted',
            model_name='CommunityEvent',
            details={'count': deleted_count},
            request=request
        )
        
        return Response({
            'message': f'Successfully deleted {deleted_count} events',
            'deleted_count': deleted_count
        })

class CommunityStatsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get community statistics"""
        # Discussion stats
        total_discussions = Discussion.objects.count()
        active_discussions = Discussion.objects.filter(status='active').count()
        reported_discussions = Discussion.objects.filter(is_flagged=True).count()
        
        # Event stats
        total_events = CommunityEvent.objects.count()
        upcoming_events = CommunityEvent.objects.filter(
            status='upcoming',
            start_date__gte=datetime.now()
        ).count()
        
        # Active users (users who participated in discussions/events in last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        active_users = User.objects.filter(
            Q(discussions__created_at__gte=week_ago) |
            Q(hosted_events__start_date__gte=week_ago) |
            Q(event_attendance__joined_at__gte=week_ago)
        ).distinct().count()
        
        # Popular topics (from discussion titles)
        popular_topics = Discussion.objects.values('title').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        return Response({
            'total_discussions': total_discussions,
            'active_discussions': active_discussions,
            'reported_discussions': reported_discussions,
            'total_events': total_events,
            'upcoming_events': upcoming_events,
            'active_users': active_users,
            'popular_topics': [
                {'topic': item['title'], 'discussion_count': item['count']}
                for item in popular_topics
            ],
        })

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import connection
from django.db.models import Count
import psutil
import time
from datetime import datetime, timedelta

class SystemConfigView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Get all system configurations"""
        configs = SystemConfig.objects.all()
        serializer = SystemConfigSerializer(configs, many=True)
        return Response(serializer.data)
    
    def put(self, request):
        """Update system configurations"""
        configs_data = request.data
        
        if not isinstance(configs_data, dict):
            return Response(
                {'error': 'Invalid data format. Expected dictionary of key-value pairs.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        updated_configs = []
        errors = []
        
        for key, value in configs_data.items():
            try:
                config = SystemConfig.objects.get(key=key)
                
                # Validate based on data type
                if config.data_type == 'boolean':
                    if str(value).lower() not in ['true', 'false', '1', '0']:
                        errors.append(f'{key}: Invalid boolean value')
                        continue
                    value = 'true' if str(value).lower() in ['true', '1'] else 'false'
                elif config.data_type == 'integer':
                    try:
                        value = str(int(value))
                    except ValueError:
                        errors.append(f'{key}: Must be an integer')
                        continue
                
                config.value = str(value)
                config.updated_by = request.user
                config.save()
                updated_configs.append(key)
                
            except SystemConfig.DoesNotExist:
                errors.append(f'{key}: Configuration key not found')
        
        if errors:
            return Response(
                {'error': 'Some configurations failed to update', 'details': errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='system_config_updated',
            details={'updated_keys': updated_configs},
            request=request
        )
        
        return Response({
            'message': f'Successfully updated {len(updated_configs)} configurations',
            'updated_configs': updated_configs
        }, status=status.HTTP_200_OK)

class SystemHealthView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Get system health information"""
        try:
            # Check database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                database_status = 'connected'
        except Exception as e:
            database_status = f'error: {str(e)}'
        
        # Check disk usage
        try:
            disk_usage = psutil.disk_usage('/')
            storage_usage = round((disk_usage.used / disk_usage.total) * 100, 2)
        except Exception:
            storage_usage = 0.0
        
        # Check CPU and memory
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
        except Exception:
            cpu_percent = 0
            memory = None
        
        # Get active users (users who logged in last 5 minutes)
        from django.utils import timezone
        from base.models import User
        active_users = User.objects.filter(
            last_login__gte=timezone.now() - timedelta(minutes=5)
        ).count()
        
        # Get latest health record or create new one
        from adminapp.models import SystemHealth
        
        health = SystemHealth.objects.create(
            status='healthy',
            uptime=100.0,  # You would calculate this from uptime monitoring
            database_status=database_status,
            storage_usage=storage_usage,
            active_users=active_users,
            api_response_time=0.0,  # Calculate from API monitoring
            last_backup=None  # Set this from backup system
        )
        
        serializer = SystemHealthSerializer(health)
        return Response(serializer.data)

class SettingCategoriesView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        """Get all setting categories with counts"""
        from django.db.models import Count
        
        categories = SystemConfig.objects.values('category').annotate(
            settings_count=Count('id')
        ).order_by('category')
        
        # Map categories to display names
        category_map = {
            'general': 'General',
            'security': 'Security',
            'email': 'Email',
            'features': 'Features',
            'database': 'Database',
            'notifications': 'Notifications',
            'performance': 'Performance',
            'maintenance': 'Maintenance',
        }
        
        result = []
        for cat in categories:
            category_id = cat['category']
            result.append({
                'id': category_id,
                'name': category_map.get(category_id, category_id.title()),
                'description': f'Configure {category_map.get(category_id, category_id)} settings',
                'settings_count': cat['settings_count'],
                'icon': category_id,  # Use category as icon identifier
            })
        
        return Response(result)

class ResetConfigDefaultsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsSuperAdmin]
    
    def post(self, request):
        """Reset all configurations to default values"""
        from adminapp.default_configs import DEFAULT_CONFIGS
        
        updated_count = 0
        for key, default_config in DEFAULT_CONFIGS.items():
            try:
                config = SystemConfig.objects.get(key=key)
                config.value = default_config['value']
                config.updated_by = request.user
                config.save()
                updated_count += 1
            except SystemConfig.DoesNotExist:
                # Create missing config
                SystemConfig.objects.create(
                    key=key,
                    value=default_config['value'],
                    description=default_config['description'],
                    category=default_config['category'],
                    data_type=default_config['data_type'],
                    updated_by=request.user
                )
                updated_count += 1
        
        # Log the action
        AdminAuditLogger.log_action(
            admin_user=request.user,
            action='system_config_reset',
            details={'reset_count': updated_count},
            request=request
        )
        
        return Response({
            'message': f'Successfully reset {updated_count} configurations to defaults'
        })

class SystemLogsView(APIView):
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsSuperAdmin]
    
    def get(self, request):
        """Get system logs with filtering"""
        logs = SystemLog.objects.all().select_related('user').order_by('-created_at')
        
        # Apply filters
        level = request.query_params.get('level')
        category = request.query_params.get('category')
        user_id = request.query_params.get('user_id')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        search = request.query_params.get('search')
        
        if level:
            logs = logs.filter(level=level)
        if category:
            logs = logs.filter(category=category)
        if user_id:
            logs = logs.filter(user_id=user_id)
        if start_date:
            logs = logs.filter(created_at__date__gte=start_date)
        if end_date:
            logs = logs.filter(created_at__date__lte=end_date)
        if search:
            logs = logs.filter(message__icontains=search)
        
        # Pagination
        from django.core.paginator import Paginator
        page = request.query_params.get('page', 1)
        per_page = request.query_params.get('per_page', 50)
        
        paginator = Paginator(logs, per_page)
        page_obj = paginator.get_page(page)
        
        serializer = SystemLogSerializer(page_obj, many=True)
        
        return Response({
            'logs': serializer.data,
            'page': page_obj.number,
            'total_pages': paginator.num_pages,
            'total_logs': paginator.count,
            'per_page': per_page
        })