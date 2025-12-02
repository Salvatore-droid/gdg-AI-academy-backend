from rest_framework import serializers
from base.models import *
from adminapp.models import *

# Import specific serializers from base app instead of *
from base.serializers import (
    LoginSerializer, SignupSerializer, UserSerializer, 
    AuthResponseSerializer, CourseSerializer, 
    CourseModuleSerializer as BaseCourseModuleSerializer,
    UserCourseProgressSerializer, CertificateSerializer,
    LearningPathSerializer, UserLearningStatsSerializer,
    DashboardStatsSerializer
)

# Admin Auth Serializers
class AdminLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = User.objects.get(email=email, is_staff=True, is_active=True)
        except User.DoesNotExist:
            raise serializers.ValidationError({
                'email': 'No admin account found with this email'
            })
        
        if not user.check_password(password):
            raise serializers.ValidationError({
                'password': 'Invalid password'
            })
        
        data['admin_user'] = user
        return data

# Admin User Management Serializers
class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'is_active', 'is_staff', 
                 'last_login', 'created_at', 'bio']
        read_only_fields = ['id', 'created_at']

class AdminUserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    
    class Meta:
        model = User
        fields = ['email', 'full_name', 'password', 'is_staff', 'is_active']
    
    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=validated_data['password']
        )
        user.is_staff = validated_data.get('is_staff', False)
        user.is_active = validated_data.get('is_active', True)
        user.save()
        return user

# Course Management Serializers
class AdminCourseSerializer(serializers.ModelSerializer):
    approval_status = serializers.SerializerMethodField()
    enrolled_users = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'category', 'difficulty',
                 'duration_minutes', 'is_active', 'created_at', 'updated_at',
                 'approval_status', 'enrolled_users', 'completion_rate']
    
    def get_approval_status(self, obj):
        try:
            approval = CourseApproval.objects.get(course=obj)
            return approval.status
        except CourseApproval.DoesNotExist:
            return 'not_required'
    
    def get_enrolled_users(self, obj):
        return UserCourseProgress.objects.filter(course=obj).count()
    
    def get_completion_rate(self, obj):
        total_enrolled = UserCourseProgress.objects.filter(course=obj).count()
        if total_enrolled == 0:
            return 0
        completed = UserCourseProgress.objects.filter(course=obj, is_completed=True).count()
        return (completed / total_enrolled) * 100

# Audit Log Serializer
class AuditLogSerializer(serializers.ModelSerializer):
    admin_user_name = serializers.CharField(source='admin_user.full_name', read_only=True)
    admin_user_email = serializers.CharField(source='admin_user.email', read_only=True)
    
    class Meta:
        model = AdminAuditLog
        fields = ['id', 'admin_user_name', 'admin_user_email', 'action', 
                 'model_name', 'object_id', 'details', 'ip_address',
                 'user_agent', 'created_at']
        read_only_fields = fields

# System Config Serializer
class SystemConfigSerializer(serializers.ModelSerializer):
    updated_by_name = serializers.CharField(source='updated_by.full_name', read_only=True)
    
    class Meta:
        model = SystemConfig
        fields = ['key', 'value', 'description', 'updated_by_name', 'updated_at']
        read_only_fields = ['updated_by_name', 'updated_at']

# Statistics Serializers
class AdminDashboardStatsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users_today = serializers.IntegerField()
    total_courses = serializers.IntegerField()
    total_active_courses = serializers.IntegerField()
    pending_approvals = serializers.IntegerField()
    total_ai_labs = serializers.IntegerField()
    total_certificates_issued = serializers.IntegerField()
    revenue_today = serializers.DecimalField(max_digits=10, decimal_places=2)
    revenue_month = serializers.DecimalField(max_digits=10, decimal_places=2)
    system_uptime = serializers.FloatField()
    
    class Meta:
        fields = '__all__'


# adminapp/serializers.py - Add these serializers
class CourseCreateUpdateSerializer(serializers.ModelSerializer):
    """Serializer for creating and updating courses"""
    class Meta:
        model = Course
        fields = [
            'title', 'description', 'category', 'difficulty',
            'duration_minutes', 'thumbnail', 'instructor', 'is_active'
        ]
        extra_kwargs = {
            'title': {'required': True},
            'description': {'required': True},
            'category': {'required': True},
            'difficulty': {'required': True},
        }

class CourseDetailSerializer(serializers.ModelSerializer):
    """Detailed course serializer for admin"""
    enrolled_students = serializers.SerializerMethodField()
    modules_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'title', 'description', 'category', 'difficulty',
            'duration_minutes', 'thumbnail', 'instructor', 'is_active',
            'created_at', 'updated_at', 'enrolled_students',
            'modules_count', 'completion_rate', 'approval_status'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_enrolled_students(self, obj):
        return UserCourseProgress.objects.filter(course=obj).count()
    
    def get_modules_count(self, obj):
        return CourseModule.objects.filter(course=obj).count()
    
    def get_completion_rate(self, obj):
        total = UserCourseProgress.objects.filter(course=obj).count()
        if total == 0:
            return 0
        completed = UserCourseProgress.objects.filter(course=obj, is_completed=True).count()
        return round((completed / total) * 100, 1)
    
    def get_approval_status(self, obj):
        try:
            approval = CourseApproval.objects.get(course=obj)
            return approval.status
        except CourseApproval.DoesNotExist:
            return 'approved'  # Default for existing courses

# Admin-specific Course Module Serializer
class AdminCourseModuleSerializer(serializers.ModelSerializer):
    course = serializers.CharField(source='course.title', read_only=True)
    course_id = serializers.UUIDField(source='course.id', read_only=True)
    lesson_count = serializers.SerializerMethodField()
    total_duration = serializers.SerializerMethodField()
    
    class Meta:
        model = CourseModule
        fields = [
            'id', 'title', 'description', 'course', 'course_id',
            'order', 'duration_minutes', 'content_type', 'content_url',
            'is_active', 'created_at', 'updated_at', 'lesson_count', 'total_duration'
        ]
    
    def get_lesson_count(self, obj):
        return obj.lessons.count()
    
    def get_total_duration(self, obj):
        return obj.duration_minutes

class CourseModuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = [
            'title', 'description', 'order', 'duration_minutes',
            'content_type', 'content_url', 'is_active'
        ]

from base.models import Discussion, CommunityEvent, EventAttendance

class DiscussionSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.full_name', read_only=True)
    author_id = serializers.UUIDField(source='author.id', read_only=True)
    course_title = serializers.CharField(source='course.title', read_only=True, allow_null=True)
    course_id = serializers.UUIDField(source='course.id', read_only=True, allow_null=True)
    
    class Meta:
        model = Discussion
        fields = [
            'id', 'title', 'content', 'author_name', 'author_id',
            'course_title', 'course_id', 'replies_count', 'views_count',
            'likes_count', 'status', 'is_flagged', 'flag_reason',
            'created_at', 'updated_at', 'last_activity_at'
        ]

class CommunityEventSerializer(serializers.ModelSerializer):
    host_name = serializers.CharField(source='host.full_name', read_only=True)
    host_id = serializers.UUIDField(source='host.id', read_only=True)
    current_attendees = serializers.SerializerMethodField()
    
    class Meta:
        model = CommunityEvent
        fields = [
            'id', 'title', 'description', 'event_type', 'host_name', 'host_id',
            'start_date', 'end_date', 'max_attendees', 'current_attendees',
            'status', 'location', 'is_virtual', 'meeting_link', 'created_at'
        ]
    
    def get_current_attendees(self, obj):
        return obj.attendees.count()

class CommunityStatsSerializer(serializers.Serializer):
    total_discussions = serializers.IntegerField()
    active_discussions = serializers.IntegerField()
    reported_discussions = serializers.IntegerField()
    total_events = serializers.IntegerField()
    upcoming_events = serializers.IntegerField()
    active_users = serializers.IntegerField()
    popular_topics = serializers.ListField(child=serializers.DictField())


class SystemConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemConfig
        fields = [
            'id', 'key', 'value', 'description', 
            'category', 'data_type', 'updated_at', 'updated_by'
        ]
        read_only_fields = ['id', 'updated_at', 'updated_by']

class SystemHealthSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemHealth
        fields = '__all__'

class SystemLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    
    class Meta:
        model = SystemLog
        fields = '__all__'