from django.db import models
import uuid
from base.models import User, Course, AILab  # Import from base app

# Admin-specific models can go here
class AdminAuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'admin_audit_logs'
        ordering = ['-created_at']

class SystemConfig(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.JSONField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        db_table = 'system_configs'

# Admin-specific models for managing content
class CourseApproval(models.Model):
    course = models.OneToOneField(Course, on_delete=models.CASCADE, primary_key=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('needs_revision', 'Needs Revision')
        ],
        default='pending'
    )
    reviewed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'course_approvals'

from django.db import models
import uuid
from django.contrib.auth import get_user_model

User = get_user_model()

class SystemConfig(models.Model):
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('security', 'Security'),
        ('email', 'Email'),
        ('features', 'Features'),
        ('database', 'Database'),
        ('notifications', 'Notifications'),
        ('performance', 'Performance'),
        ('maintenance', 'Maintenance'),
    ]
    
    DATA_TYPE_CHOICES = [
        ('string', 'String'),
        ('integer', 'Integer'),
        ('boolean', 'Boolean'),
        ('text', 'Text'),
        ('password', 'Password'),
        ('secret', 'Secret'),
        ('select', 'Select'),
        ('json', 'JSON'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='general')
    data_type = models.CharField(max_length=20, choices=DATA_TYPE_CHOICES, default='string')
    is_required = models.BooleanField(default=True)
    is_sensitive = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        db_table = 'system_configs'
        verbose_name = 'System Configuration'
        verbose_name_plural = 'System Configurations'
        ordering = ['category', 'key']
    
    def __str__(self):
        return self.key

class SystemHealth(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(max_length=20, choices=[
        ('healthy', 'Healthy'),
        ('warning', 'Warning'),
        ('critical', 'Critical'),
    ], default='healthy')
    uptime = models.FloatField(default=100.0)
    database_status = models.CharField(max_length=50, default='connected')
    storage_usage = models.FloatField(default=0.0)
    active_users = models.IntegerField(default=0)
    api_response_time = models.FloatField(default=0.0)
    last_backup = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_health'
        verbose_name = 'System Health'
        verbose_name_plural = 'System Health Records'
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Only keep latest 100 records
        if not self.pk:
            # Delete old records if we have more than 100
            old_records = SystemHealth.objects.order_by('-created_at')[100:]
            if old_records.exists():
                old_records.delete()
        super().save(*args, **kwargs)

class SystemLog(models.Model):
    LOG_LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
        ('debug', 'Debug'),
    ]
    
    LOG_CATEGORY_CHOICES = [
        ('system', 'System'),
        ('auth', 'Authentication'),
        ('database', 'Database'),
        ('api', 'API'),
        ('security', 'Security'),
        ('user', 'User Activity'),
        ('admin', 'Admin Action'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=20, choices=LOG_LEVEL_CHOICES, default='info')
    category = models.CharField(max_length=50, choices=LOG_CATEGORY_CHOICES, default='system')
    message = models.TextField()
    details = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'system_logs'
        verbose_name = 'System Log'
        verbose_name_plural = 'System Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['level', 'created_at']),
            models.Index(fields=['category', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.level.upper()} - {self.message[:50]}"