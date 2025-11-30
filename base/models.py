from django.db import models
import uuid
from django.utils import timezone
import bcrypt
import jwt
from datetime import datetime, timedelta
from django.conf import settings


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password_hash = models.TextField()
    full_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def set_password(self, password):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        """Verify password"""
        if not self.password_hash:
            return False
        try:
            return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        except Exception:
            return False

    def generate_token(self):
        """Generate JWT token"""
        payload = {
            'user_id': str(self.id),
            'email': self.email,
            'exp': datetime.now() + timedelta(days=7)
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.now()
        self.save()

    def __str__(self):
        return f"{self.full_name} ({self.email})"

    class Meta:
        db_table = 'users'

class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    token = models.TextField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    @classmethod
    def create_session(cls, user):
        """Create a new user session"""
        token = user.generate_token()
        expires_at = timezone.now() + timedelta(days=7)  # Use timezone.now()
        
        session = cls.objects.create(
            user=user,
            token=token,
            expires_at=expires_at
        )
        return session

    def is_valid(self):
        """Check if session is still valid"""
        return self.is_active and timezone.now() < self.expires_at  # Use timezone.now()

    def invalidate(self):
        """Invalidate session"""
        self.is_active = False
        self.save()

    class Meta:
        db_table = 'user_sessions'
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['user', 'is_active']),
        ]

class Course(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail = models.URLField(blank=True, null=True)
    duration_minutes = models.IntegerField(default=0)  # Total course duration in minutes
    difficulty = models.CharField(
        max_length=20,
        choices=[('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')],
        default='beginner'
    )
    category = models.CharField(max_length=100)
    instructor = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'courses'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['difficulty']),
        ]

class CourseModule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='modules')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.IntegerField(default=0)
    duration_minutes = models.IntegerField(default=0)
    video_url = models.URLField(blank=True, null=True)
    content = models.TextField(blank=True)  # HTML content or markdown
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'course_modules'
        ordering = ['order']
        unique_together = ['course', 'order']

class UserCourseProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='course_progress')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='user_progress')
    current_module = models.ForeignKey(CourseModule, on_delete=models.SET_NULL, null=True, blank=True)
    progress_percentage = models.FloatField(default=0.0)  # 0.0 to 100.0
    completed_modules_count = models.IntegerField(default=0)
    total_modules_count = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    last_accessed_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_course_progress'
        unique_together = ['user', 'course']
        indexes = [
            models.Index(fields=['user', 'is_completed']),
            models.Index(fields=['progress_percentage']),
        ]

class UserModuleProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='module_progress')
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='user_progress')
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    time_spent_minutes = models.IntegerField(default=0)  # Time spent on this module
    last_position = models.FloatField(default=0.0)  # For video progress

    class Meta:
        db_table = 'user_module_progress'
        unique_together = ['user', 'module']

class Certificate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='certificates')
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='certificates')
    certificate_id = models.CharField(max_length=100, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    download_url = models.URLField(blank=True, null=True)

    class Meta:
        db_table = 'certificates'
        unique_together = ['user', 'course']

class LearningPath(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon_name = models.CharField(max_length=50)  # e.g., "brain", "shield", "code"
    color = models.CharField(max_length=20)  # e.g., "google-blue", "google-red"
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'), 
        ('advanced', 'Advanced')
    ])
    estimated_duration_hours = models.IntegerField(default=0)
    courses = models.ManyToManyField(Course, through='PathCourse', related_name='learning_paths')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'learning_paths'

class PathCourse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)

    class Meta:
        db_table = 'path_courses'
        ordering = ['order']
        unique_together = ['learning_path', 'course']

class UserLearningStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True, related_name='learning_stats')
    total_learning_hours = models.FloatField(default=0.0)
    total_courses_completed = models.IntegerField(default=0)
    total_modules_completed = models.IntegerField(default=0)
    total_certificates_earned = models.IntegerField(default=0)
    total_ai_projects = models.IntegerField(default=0)
    streak_days = models.IntegerField(default=0)
    last_learning_date = models.DateField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_learning_stats'

class AILab(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, default="sparkles")
    difficulty = models.CharField(
        max_length=20,
        choices=[('Beginner', 'Beginner'), ('Intermediate', 'Intermediate'), ('Advanced', 'Advanced')],
        default='Beginner'
    )
    estimated_duration_minutes = models.IntegerField(default=120)
    category = models.CharField(max_length=100, default="Machine Learning")
    prerequisites = models.JSONField(default=list)  # List of prerequisite course/module IDs
    starter_code_url = models.URLField(blank=True, null=True)
    instructions_url = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'ai_labs'

class UserAILabProgress(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='ai_lab_progress')
    lab = models.ForeignKey(AILab, on_delete=models.CASCADE, related_name='user_progress')
    status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('in-progress', 'In Progress'),
            ('completed', 'Completed'),
            ('locked', 'Locked')
        ],
        default='locked'
    )
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    code_submission = models.TextField(blank=True, null=True)
    score = models.FloatField(null=True, blank=True)  # 0-100 score
    attempts = models.IntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'user_ai_lab_progress'
        unique_together = ['user', 'lab']


class Achievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon_name = models.CharField(max_length=50, default="trophy")
    color = models.CharField(max_length=20, default="google-blue")
    criteria_type = models.CharField(
        max_length=50,
        choices=[
            ('courses_completed', 'Courses Completed'),
            ('modules_completed', 'Modules Completed'),
            ('learning_hours', 'Learning Hours'),
            ('streak_days', 'Streak Days'),
            ('labs_completed', 'Labs Completed'),
            ('certificates_earned', 'Certificates Earned'),
        ]
    )
    criteria_threshold = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        db_table = 'achievements'

class UserAchievement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey(Achievement, on_delete=models.CASCADE, related_name='user_achievements')
    unlocked_at = models.DateTimeField(auto_now_add=True)
    is_notified = models.BooleanField(default=False)

    class Meta:
        db_table = 'user_achievements'
        unique_together = ['user', 'achievement']

class Mentor(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='mentor_profile')
    role = models.CharField(max_length=255)
    expertise = models.JSONField(default=list)  # List of expertise areas
    bio = models.TextField()
    rating = models.FloatField(default=0.0)
    sessions_completed = models.IntegerField(default=0)
    is_available = models.BooleanField(default=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'mentors'

class Discussion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    content = models.TextField()
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussions')
    tags = models.JSONField(default=list)
    replies_count = models.IntegerField(default=0)
    likes_count = models.IntegerField(default=0)
    views_count = models.IntegerField(default=0)
    is_pinned = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discussions'
        ordering = ['-created_at']

class DiscussionReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    discussion = models.ForeignKey(Discussion, on_delete=models.CASCADE, related_name='replies')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='discussion_replies')
    content = models.TextField()
    likes_count = models.IntegerField(default=0)
    is_solution = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'discussion_replies'
        ordering = ['created_at']

class CommunityEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    description = models.TextField()
    event_date = models.DateField()
    event_time = models.TimeField()
    duration_minutes = models.IntegerField(default=60)
    host = models.ForeignKey(User, on_delete=models.CASCADE, related_name='hosted_events')
    max_attendees = models.IntegerField(default=50)
    event_type = models.CharField(
        max_length=20,
        choices=[
            ('workshop', 'Workshop'),
            ('webinar', 'Webinar'),
            ('panel', 'Panel Discussion'),
            ('qna', 'Q&A Session'),
        ],
        default='workshop'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'community_events'
        ordering = ['event_date', 'event_time']

class EventRegistration(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event = models.ForeignKey(CommunityEvent, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'event_registrations'
        unique_together = ['event', 'user']