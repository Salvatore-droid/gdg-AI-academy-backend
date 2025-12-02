from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from .models import User, UserSession
from .serializers import *
from django.db.models import Sum
from django.http import HttpResponse
from datetime import timedelta

# base/views.py
from django.http import JsonResponse
from django.contrib.auth import get_user_model

def debug_middleware(request):
    """Debug view to check middleware and authentication"""
    User = get_user_model()
    
    debug_info = {
        'request.user': str(request.user),
        'request.user type': type(request.user).__name__,
        'is_authenticated': request.user.is_authenticated if hasattr(request.user, 'is_authenticated') else 'NO',
        'session_exists': hasattr(request, 'session'),
        'session_keys': list(request.session.keys()) if hasattr(request, 'session') else 'NO_SESSION',
        'middleware_classes': [str(mw) for mw in request.META.get('MIDDLEWARE', [])],
    }
    
    return JsonResponse(debug_info)

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """Handle user login"""
    serializer = LoginSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.validated_data['user']
        
        # Update last login
        user.update_last_login()
        
        # Create session
        session = UserSession.create_session(user)
        
        # Prepare response
        response_data = {
            'user': UserSerializer(user).data,
            'token': session.token,
            'message': 'Login successful'
        }
        
        return Response(
            response_data,
            status=status.HTTP_200_OK
        )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """Handle user registration with FormData support"""
    # Handle FormData (frontend might be sending this)
    if request.content_type == 'application/x-www-form-urlencoded' or request.content_type.startswith('multipart/form-data'):
        data = {
            'full_name': request.POST.get('signup-name') or request.POST.get('full_name'),
            'email': request.POST.get('signup-email') or request.POST.get('email'),
            'password': request.POST.get('signup-password') or request.POST.get('password'),
        }
    else:
        # Assume JSON
        data = request.data
    
    print("Processing signup with data:", data)
    
    # Validate required fields
    if not data.get('full_name') or not data.get('email') or not data.get('password'):
        return Response({
            'error': 'All fields are required: full_name, email, password'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = SignupSerializer(data=data)
    
    if serializer.is_valid():
        user = serializer.save()
        session = UserSession.create_session(user)
        
        response_data = {
            'user': UserSerializer(user).data,
            'token': session.token,
            'message': 'Account created successfully'
        }
        
        return Response(response_data, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """Handle user logout"""
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        
        try:
            # Invalidate session
            session = UserSession.objects.get(token=token, is_active=True)
            session.invalidate()
        except UserSession.DoesNotExist:
            pass
    
    return Response(
        {'message': 'Logout successful'},
        status=status.HTTP_200_OK
    )

@api_view(['GET'])
def profile(request):
    """Get current user profile"""
    # Get token from Authorization header
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            session = UserSession.objects.get(token=token, is_active=True)
            if session.is_valid():
                return Response(
                    UserSerializer(session.user).data,
                    status=status.HTTP_200_OK
                )
        except UserSession.DoesNotExist:
            pass
    
    return Response(
        {'error': 'Invalid token'},
        status=status.HTTP_401_UNAUTHORIZED
    )

@api_view(['POST'])
def change_password(request):
    """Change user password"""
    # Get user from token
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response(
                {'error': 'Current password and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.check_password(current_password):
            return Response(
                {'error': 'Current password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        # Invalidate all other sessions for security
        UserSession.objects.filter(user=user, is_active=True).exclude(token=token).update(is_active=False)
        
        return Response(
            {'message': 'Password updated successfully'},
            status=status.HTTP_200_OK
        )
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

from .models import (
    Course, UserCourseProgress, Certificate, LearningPath, 
    UserLearningStats, CourseModule, UserModuleProgress
)
from .serializers import (
    CourseSerializer, UserCourseProgressSerializer, CertificateSerializer,
    LearningPathSerializer, UserLearningStatsSerializer, DashboardStatsSerializer
)

@api_view(['GET'])
def dashboard_stats(request):
    """Get dashboard statistics and data for the current user"""
    # Get user from token
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        # Get user learning stats
        learning_stats, _ = UserLearningStats.objects.get_or_create(user=user)
        
        # Get active courses (in progress but not completed)
        active_courses = UserCourseProgress.objects.filter(
            user=user, 
            is_completed=False
        ).select_related('course').order_by('-last_accessed_at')[:10]
        
        # Get recommended learning paths
        recommended_paths = LearningPath.objects.filter(
            is_active=True
        ).order_by('?')[:4]  # Random 4 paths for variety
        
        # Prepare response data
        stats_data = {
            'total_learning_hours': learning_stats.total_learning_hours,
            'total_modules_completed': learning_stats.total_modules_completed,
            'total_certificates_earned': learning_stats.total_certificates_earned,
            'total_ai_projects': learning_stats.total_ai_projects,
            'active_courses': UserCourseProgressSerializer(active_courses, many=True).data,
            'recommended_paths': LearningPathSerializer(recommended_paths, many=True).data,
        }
        
        serializer = DashboardStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def user_courses(request):
    """Get all courses for the current user"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        user_courses = UserCourseProgress.objects.filter(
            user=user
        ).select_related('course').order_by('-last_accessed_at')
        
        serializer = UserCourseProgressSerializer(user_courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def user_certificates(request):
    """Get all certificates for the current user"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        certificates = Certificate.objects.filter(
            user=user
        ).select_related('course').order_by('-issued_at')
        
        serializer = CertificateSerializer(certificates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def learning_paths(request):
    """Get all available learning paths"""
    try:
        paths = LearningPath.objects.filter(is_active=True).order_by('difficulty', 'title')
        serializer = LearningPathSerializer(paths, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to fetch learning paths'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
def enroll_course(request, course_id):
    """Enroll user in a course"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            return Response(
                {'error': 'Course not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if user is already enrolled
        if UserCourseProgress.objects.filter(user=user, course=course).exists():
            return Response(
                {'error': 'Already enrolled in this course'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get total modules count
        total_modules = CourseModule.objects.filter(course=course).count()
        
        # Create user course progress
        progress = UserCourseProgress.objects.create(
            user=user,
            course=course,
            total_modules_count=total_modules
        )
        
        return Response({
            'message': 'Successfully enrolled in course',
            'course': CourseSerializer(course).data,
            'progress': UserCourseProgressSerializer(progress).data
        }, status=status.HTTP_201_CREATED)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def courses_list(request):
    """Get all available courses"""
    try:
        courses = Course.objects.filter(is_active=True).order_by('-created_at')
        serializer = CourseSerializer(courses, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response(
            {'error': 'Failed to fetch courses'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def course_detail(request, course_id):
    """Get detailed information about a specific course"""
    try:
        course = Course.objects.get(id=course_id, is_active=True)
        modules = CourseModule.objects.filter(course=course).order_by('order')
        
        course_data = CourseSerializer(course).data
        modules_data = CourseModuleSerializer(modules, many=True).data
        
        return Response({
            'course': course_data,
            'modules': modules_data
        }, status=status.HTTP_200_OK)
        
    except Course.DoesNotExist:
        return Response(
            {'error': 'Course not found'},
            status=status.HTTP_404_NOT_FOUND
        )

@api_view(['GET'])
def course_progress(request, course_id):
    """Get user progress for a specific course"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        try:
            # Get course progress
            course_progress = UserCourseProgress.objects.get(
                user=user, 
                course_id=course_id
            )
            
            # Get module progress for this course
            module_progress = UserModuleProgress.objects.filter(
                user=user,
                module__course_id=course_id
            ).select_related('module')
            
            progress_serializer = UserCourseProgressSerializer(course_progress)
            module_progress_data = []
            
            for mp in module_progress:
                module_progress_data.append({
                    'id': str(mp.id),
                    'module': str(mp.module.id),
                    'is_completed': mp.is_completed,
                    'completed_at': mp.completed_at,
                    'time_spent_minutes': mp.time_spent_minutes,
                    'last_position': mp.last_position
                })
            
            return Response({
                'progress': progress_serializer.data,
                'module_progress': module_progress_data
            }, status=status.HTTP_200_OK)
            
        except UserCourseProgress.DoesNotExist:
            return Response(
                {'error': 'Not enrolled in this course'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['POST'])
def mark_module_complete(request, module_id):
    """Mark a module as completed for the current user"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        try:
            module = CourseModule.objects.get(id=module_id)
            
            # Get or create module progress
            module_progress, created = UserModuleProgress.objects.get_or_create(
                user=user,
                module=module,
                defaults={
                    'is_completed': True,
                    'completed_at': timezone.now()
                }
            )
            
            if not created and not module_progress.is_completed:
                module_progress.is_completed = True
                module_progress.completed_at = timezone.now()
                module_progress.save()
            
            # Update course progress
            course_progress = UserCourseProgress.objects.get(
                user=user,
                course=module.course
            )
            
            # Recalculate progress
            total_modules = CourseModule.objects.filter(course=module.course).count()
            completed_modules = UserModuleProgress.objects.filter(
                user=user,
                module__course=module.course,
                is_completed=True
            ).count()
            
            course_progress.completed_modules_count = completed_modules
            course_progress.progress_percentage = (completed_modules / total_modules) * 100
            
            # Check if course is completed
            if completed_modules == total_modules:
                course_progress.is_completed = True
                course_progress.completed_at = timezone.now()
            
            course_progress.save()
            
            return Response({
                'message': 'Module marked as completed',
                'module': {
                    'id': str(module.id),
                    'title': module.title
                },
                'course_progress': UserCourseProgressSerializer(course_progress).data
            }, status=status.HTTP_200_OK)
            
        except CourseModule.DoesNotExist:
            return Response(
                {'error': 'Module not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except UserCourseProgress.DoesNotExist:
            return Response(
                {'error': 'Not enrolled in this course'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def user_modules(request):
    """Get all modules for user's enrolled courses with progress"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        # Get user's enrolled courses
        user_courses = UserCourseProgress.objects.filter(user=user).select_related('course')
        
        # Get all modules for enrolled courses
        course_ids = [uc.course.id for uc in user_courses]
        modules = CourseModule.objects.filter(course__id__in=course_ids).select_related('course').order_by('course__title', 'order')
        
        # Get module progress
        module_progress = UserModuleProgress.objects.filter(
            user=user,
            module__course__id__in=course_ids
        ).select_related('module')
        
        # Serialize modules
        modules_data = []
        for module in modules:
            modules_data.append({
                'id': str(module.id),
                'course': {
                    'id': str(module.course.id),
                    'title': module.course.title,
                    'category': module.course.category,
                    'difficulty': module.course.difficulty,
                },
                'title': module.title,
                'description': module.description,
                'order': module.order,
                'duration_minutes': module.duration_minutes,
                'video_url': module.video_url,
                'content': module.content,
            })
        
        # Serialize module progress
        module_progress_data = []
        for mp in module_progress:
            module_progress_data.append({
                'id': str(mp.id),
                'module': str(mp.module.id),
                'is_completed': mp.is_completed,
                'completed_at': mp.completed_at,
                'time_spent_minutes': mp.time_spent_minutes,
                'last_position': mp.last_position,
            })
        
        return Response({
            'modules': modules_data,
            'module_progress': module_progress_data
        }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

from rest_framework import status  # Make sure this import exists

@api_view(['GET'])
def ai_labs_list(request):
    """Get all AI labs with user progress"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        # Get all active labs
        labs = AILab.objects.filter(is_active=True).order_by('difficulty', 'created_at')
        
        # Get user progress for labs
        user_progress = UserAILabProgress.objects.filter(user=user).select_related('lab')
        
        # Create a mapping of lab ID to user progress
        progress_map = {up.lab.id: up for up in user_progress}
        
        labs_data = []
        for lab in labs:
            user_lab_progress = progress_map.get(lab.id)
            
            # Determine lab status
            if user_lab_progress:
                status_value = user_lab_progress.status
            else:
                # Check prerequisites to determine if lab should be available or locked
                has_prerequisites = check_prerequisites(user, lab.prerequisites)
                status_value = 'available' if has_prerequisites else 'locked'
                
                # Create user progress record if needed
                if status_value == 'available':
                    user_lab_progress = UserAILabProgress.objects.create(
                        user=user,
                        lab=lab,
                        status='available'
                    )
            
            labs_data.append({
                'id': str(lab.id),
                'title': lab.title,
                'description': lab.description,
                'icon_name': lab.icon_name,
                'difficulty': lab.difficulty,
                'estimated_duration_minutes': lab.estimated_duration_minutes,
                'category': lab.category,
                'prerequisites': lab.prerequisites,
                'starter_code_url': lab.starter_code_url,
                'instructions_url': lab.instructions_url,
                'status': status_value,  # Use different variable name to avoid conflict
                'score': user_lab_progress.score if user_lab_progress else None,
                'attempts': user_lab_progress.attempts if user_lab_progress else 0,
            })
        
        return Response(labs_data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

def check_prerequisites(user, prerequisites):
    """Check if user has completed all prerequisites"""
    if not prerequisites:
        return True
    
    # Check if user has completed all prerequisite courses/modules
    # This is a simplified implementation - you might want to expand this
    completed_courses = UserCourseProgress.objects.filter(
        user=user,
        is_completed=True
    ).values_list('course_id', flat=True)
    
    completed_modules = UserModuleProgress.objects.filter(
        user=user,
        is_completed=True
    ).values_list('module_id', flat=True)
    
    for prereq in prerequisites:
        # Check if prerequisite is a course or module ID
        if prereq not in completed_courses and prereq not in completed_modules:
            return False
    
    return True

@api_view(['POST'])
def start_ai_lab(request, lab_id):
    """Start an AI lab"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        try:
            lab = AILab.objects.get(id=lab_id, is_active=True)
            user_progress, created = UserAILabProgress.objects.get_or_create(
                user=user,
                lab=lab
            )
            
            if user_progress.status == 'locked':
                # Check if prerequisites are now met
                if not check_prerequisites(user, lab.prerequisites):
                    return Response(
                        {'error': 'Prerequisites not met'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                user_progress.status = 'available'
            
            if user_progress.status == 'available':
                user_progress.status = 'in-progress'
                user_progress.started_at = timezone.now()
                user_progress.attempts += 1
                user_progress.last_attempt_at = timezone.now()
                user_progress.save()
            
            lab_data = {
                'id': str(lab.id),
                'title': lab.title,
                'description': lab.description,
                'starter_code_url': lab.starter_code_url,
                'instructions_url': lab.instructions_url,
            }
            
            return Response({
                'message': 'Lab started successfully',
                'lab': lab_data
            }, status=status.HTTP_200_OK)
            
        except AILab.DoesNotExist:
            return Response(
                {'error': 'Lab not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def progress_stats(request):
    """Get user learning statistics"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        # Get or create learning stats
        learning_stats, created = UserLearningStats.objects.get_or_create(user=user)
        
        # Update stats based on current progress
        update_user_learning_stats(user)
        
        serializer = UserLearningStatsSerializer(learning_stats)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

def update_user_learning_stats(user):
    """Update user learning statistics based on current progress"""
    stats, created = UserLearningStats.objects.get_or_create(user=user)
    
    # Calculate total learning hours (simplified - you might want to track this differently)
    total_minutes = UserModuleProgress.objects.filter(
        user=user
    ).aggregate(total_time=Sum('time_spent_minutes'))['total_time'] or 0
    stats.total_learning_hours = total_minutes / 60
    
    # Count completed courses
    stats.total_courses_completed = UserCourseProgress.objects.filter(
        user=user,
        is_completed=True
    ).count()
    
    # Count completed modules
    stats.total_modules_completed = UserModuleProgress.objects.filter(
        user=user,
        is_completed=True
    ).count()
    
    # Count certificates
    stats.total_certificates_earned = Certificate.objects.filter(user=user).count()
    
    # Count completed AI labs
    stats.total_ai_projects = UserAILabProgress.objects.filter(
        user=user,
        status='completed'
    ).count()
    
    # Update streak (simplified implementation)
    today = timezone.now().date()
    if stats.last_learning_date != today:
        # Check if learning happened yesterday for streak
        yesterday = today - timedelta(days=1)
        if stats.last_learning_date == yesterday:
            stats.streak_days += 1
        elif stats.last_learning_date != today:
            stats.streak_days = 1
        
        stats.last_learning_date = today
    
    stats.save()
    return stats

@api_view(['GET'])
def user_achievements(request):
    """Get user achievements"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        # Update achievements
        check_and_award_achievements(user)
        
        # Get all achievements with user unlock status
        achievements = Achievement.objects.filter(is_active=True).order_by('criteria_threshold')
        user_achievements = UserAchievement.objects.filter(user=user).select_related('achievement')
        
        unlocked_achievement_ids = set(ua.achievement.id for ua in user_achievements)
        
        achievements_data = []
        for achievement in achievements:
            achievements_data.append({
                'title': achievement.title,
                'description': achievement.description,
                'icon': achievement.icon_name,
                'color': achievement.color,
                'unlocked': achievement.id in unlocked_achievement_ids,
                'unlocked_at': next(
                    (ua.unlocked_at.isoformat() for ua in user_achievements if ua.achievement.id == achievement.id),
                    None
                )
            })
        
        return Response(achievements_data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

def check_and_award_achievements(user):
    """Check and award achievements based on user progress"""
    stats = update_user_learning_stats(user)
    achievements = Achievement.objects.filter(is_active=True)
    
    for achievement in achievements:
        # Check if user already has this achievement
        if UserAchievement.objects.filter(user=user, achievement=achievement).exists():
            continue
        
        # Check achievement criteria
        criteria_met = False
        if achievement.criteria_type == 'courses_completed':
            criteria_met = stats.total_courses_completed >= achievement.criteria_threshold
        elif achievement.criteria_type == 'modules_completed':
            criteria_met = stats.total_modules_completed >= achievement.criteria_threshold
        elif achievement.criteria_type == 'learning_hours':
            criteria_met = stats.total_learning_hours >= achievement.criteria_threshold
        elif achievement.criteria_type == 'streak_days':
            criteria_met = stats.streak_days >= achievement.criteria_threshold
        elif achievement.criteria_type == 'labs_completed':
            criteria_met = stats.total_ai_projects >= achievement.criteria_threshold
        elif achievement.criteria_type == 'certificates_earned':
            criteria_met = stats.total_certificates_earned >= achievement.criteria_threshold
        
        if criteria_met:
            UserAchievement.objects.create(user=user, achievement=achievement)

@api_view(['POST'])
def download_certificate(request, certificate_id):
    """Download certificate PDF"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        try:
            certificate = Certificate.objects.get(id=certificate_id, user=user)
            
            # Generate PDF certificate (simplified - you might want to use a proper PDF library)
            # For now, return a placeholder response
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_id}.pdf"'
            
            # In a real implementation, you would generate the PDF here
            # For now, return a simple text response
            pdf_content = f"Certificate PDF for {certificate.course.title}"
            response.write(pdf_content)
            
            return response
            
        except Certificate.DoesNotExist:
            return Response(
                {'error': 'Certificate not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def community_stats(request):
    """Get community statistics"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Calculate stats
        total_members = User.objects.filter(is_active=True).count()
        total_discussions = Discussion.objects.count()
        total_workshops = CommunityEvent.objects.filter(event_type='workshop').count()
        upcoming_events = CommunityEvent.objects.filter(
            event_date__gte=timezone.now().date(),
            is_active=True
        ).count()
        active_mentors = Mentor.objects.filter(is_available=True).count()
        
        stats = {
            'total_members': total_members,
            'total_discussions': total_discussions,
            'total_workshops': total_workshops,
            'upcoming_events': upcoming_events,
            'active_mentors': active_mentors,
        }
        
        return Response(stats, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def mentors_list(request):
    """Get list of available mentors"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        mentors = Mentor.objects.filter(is_available=True).select_related('user').order_by('-rating')
        
        mentors_data = []
        for mentor in mentors:
            mentors_data.append({
                'id': str(mentor.id),
                'name': f"{mentor.user.full_name}",
                'role': mentor.role,
                'expertise': mentor.expertise,
                'avatar': '',  # You might want to add avatar field to User model
                'rating': mentor.rating,
                'sessions_completed': mentor.sessions_completed,
                'bio': mentor.bio,
                'is_available': mentor.is_available,
            })
        
        return Response(mentors_data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def discussions_list(request):
    """Get recent discussions"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        discussions = Discussion.objects.filter(is_closed=False).select_related('author').order_by('-created_at')[:10]
        
        discussions_data = []
        for discussion in discussions:
            discussions_data.append({
                'id': str(discussion.id),
                'title': discussion.title,
                'content': discussion.content,
                'author': {
                    'id': str(discussion.author.id),
                    'name': discussion.author.full_name,
                    'avatar': '',  # Add avatar field to User model
                },
                'replies_count': discussion.replies_count,
                'likes_count': discussion.likes_count,
                'views_count': discussion.views_count,
                'tags': discussion.tags,
                'created_at': discussion.created_at.isoformat(),
            })
        
        return Response(discussions_data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['GET'])
def events_list(request):
    """Get upcoming events"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        today = timezone.now().date()
        
        events = CommunityEvent.objects.filter(
            event_date__gte=today,
            is_active=True
        ).select_related('host').order_by('event_date', 'event_time')[:10]
        
        events_data = []
        for event in events:
            attendees_count = EventRegistration.objects.filter(event=event).count()
            is_registered = EventRegistration.objects.filter(event=event, user=user).exists()
            
            events_data.append({
                'id': str(event.id),
                'title': event.title,
                'description': event.description,
                'event_date': event.event_date.isoformat(),
                'event_time': event.event_time.strftime('%H:%M'),
                'duration_minutes': event.duration_minutes,
                'host': {
                    'id': str(event.host.id),
                    'name': event.host.full_name,
                    'avatar': '',  # Add avatar field to User model
                },
                'attendees_count': attendees_count,
                'max_attendees': event.max_attendees,
                'event_type': event.event_type,
                'is_registered': is_registered,
            })
        
        return Response(events_data, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET', 'PUT'])
def user_settings(request):
    """Get or update user settings"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        
        if request.method == 'GET':
            # Get or create user settings
            settings, created = UserSettings.objects.get_or_create(user=user)
            return Response({
                'email_notifications': settings.email_notifications,
                'push_notifications': settings.push_notifications,
                'weekly_digest': settings.weekly_digest,
                'profile_visibility': settings.profile_visibility,
                'show_progress': settings.show_progress,
                'dark_mode': settings.dark_mode,
                'language': settings.language,
            }, status=status.HTTP_200_OK)
        
        elif request.method == 'PUT':
            # Update user settings
            settings, created = UserSettings.objects.get_or_create(user=user)
            data = request.data
            
            if 'email_notifications' in data:
                settings.email_notifications = data['email_notifications']
            if 'push_notifications' in data:
                settings.push_notifications = data['push_notifications']
            if 'weekly_digest' in data:
                settings.weekly_digest = data['weekly_digest']
            if 'profile_visibility' in data:
                settings.profile_visibility = data['profile_visibility']
            if 'show_progress' in data:
                settings.show_progress = data['show_progress']
            if 'dark_mode' in data:
                settings.dark_mode = data['dark_mode']
            if 'language' in data:
                settings.language = data['language']
            
            settings.save()
            
            return Response({
                'message': 'Settings updated successfully',
                'settings': {
                    'email_notifications': settings.email_notifications,
                    'push_notifications': settings.push_notifications,
                    'weekly_digest': settings.weekly_digest,
                    'profile_visibility': settings.profile_visibility,
                    'show_progress': settings.show_progress,
                    'dark_mode': settings.dark_mode,
                    'language': settings.language,
                }
            }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )

@api_view(['PUT'])
def update_profile(request):
    """Update user profile"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    
    token = auth_header.split(' ')[1]
    try:
        session = UserSession.objects.get(token=token, is_active=True)
        if not session.is_valid():
            return Response(
                {'error': 'Invalid token'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        user = session.user
        data = request.data
        
        if 'full_name' in data:
            user.full_name = data['full_name']
        if 'bio' in data:
            # Add bio field to User model if not exists
            if hasattr(user, 'bio'):
                user.bio = data['bio']
        
        user.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.full_name,
                'bio': getattr(user, 'bio', ''),
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None,
            }
        }, status=status.HTTP_200_OK)
        
    except UserSession.DoesNotExist:
        return Response(
            {'error': 'Invalid token'},
            status=status.HTTP_401_UNAUTHORIZED
        )