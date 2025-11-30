from rest_framework import serializers
from .models import *
import re

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is deactivated")
        
        data['user'] = user
        return data

class SignupSerializer(serializers.Serializer):
    full_name = serializers.CharField(required=True, max_length=255)
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True, min_length=8)
    
    def validate_email(self, value):
        """Validate email uniqueness"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists")
        return value
    
    def validate_password(self, value):
        """Validate password strength"""
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long")
        if not re.search(r'[A-Z]', value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', value):
            raise serializers.ValidationError("Password must contain at least one digit")
        return value
    
    def create(self, validated_data):
        """Create new user"""
        user = User(
            email=validated_data['email'],
            full_name=validated_data['full_name']
        )
        user.set_password(validated_data['password'])
        user.save()
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'created_at', 'last_login', 'is_active']
        read_only_fields = fields

class AuthResponseSerializer(serializers.Serializer):
    user = UserSerializer()
    token = serializers.CharField()
    message = serializers.CharField()

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'description', 'thumbnail', 'duration_minutes', 
                 'difficulty', 'category', 'instructor']

class CourseModuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseModule
        fields = ['id', 'title', 'description', 'order', 'duration_minutes', 
                 'video_url', 'content']

class UserCourseProgressSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = UserCourseProgress
        fields = ['id', 'course', 'progress_percentage', 'completed_modules_count',
                 'total_modules_count', 'started_at', 'last_accessed_at', 
                 'completed_at', 'is_completed']

class CertificateSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    
    class Meta:
        model = Certificate
        fields = ['id', 'course', 'certificate_id', 'issued_at', 'download_url']

class LearningPathSerializer(serializers.ModelSerializer):
    class Meta:
        model = LearningPath
        fields = ['id', 'title', 'description', 'icon_name', 'color', 
                 'difficulty', 'estimated_duration_hours']

class UserLearningStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserLearningStats
        fields = ['total_learning_hours', 'total_courses_completed', 
                 'total_modules_completed', 'total_certificates_earned',
                 'total_ai_projects', 'streak_days', 'last_learning_date']

class DashboardStatsSerializer(serializers.Serializer):
    total_learning_hours = serializers.FloatField()
    total_modules_completed = serializers.IntegerField()
    total_certificates_earned = serializers.IntegerField()
    total_ai_projects = serializers.IntegerField()
    active_courses = UserCourseProgressSerializer(many=True)
    recommended_paths = LearningPathSerializer(many=True)