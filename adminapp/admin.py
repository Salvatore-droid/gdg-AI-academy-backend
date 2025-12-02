from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from base.models import User
from adminapp.models import AdminAuditLog, SystemConfig, CourseApproval

# Register your models here
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'full_name', 'is_staff', 'is_active', 'last_login')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('email', 'full_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('full_name', 'bio')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important Dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2', 'is_staff', 'is_active'),
        }),
    )
    
    readonly_fields = ('created_at', 'updated_at')

@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ('admin_user', 'action', 'model_name', 'created_at')
    list_filter = ('action', 'model_name', 'created_at')
    search_fields = ('admin_user__email', 'admin_user__full_name', 'action')
    readonly_fields = ('created_at', 'ip_address', 'user_agent')
    date_hierarchy = 'created_at'

@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'updated_at', 'updated_by')
    search_fields = ('key', 'description')
    readonly_fields = ('updated_at',)

@admin.register(CourseApproval)
class CourseApprovalAdmin(admin.ModelAdmin):
    list_display = ('course', 'status', 'reviewed_by', 'reviewed_at')
    list_filter = ('status', 'reviewed_at')
    search_fields = ('course__title', 'review_notes')
    readonly_fields = ('created_at',)