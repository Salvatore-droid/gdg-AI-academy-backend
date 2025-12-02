# create_first_admin.py
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gdg_ai_lms.settings')
django.setup()

from django.contrib.auth.hashers import make_password
from base.models import User
from admin_dashboard.models import AdminUser

def create_first_admin():
    # Create the admin user
    admin_email = 'admin@example.com'
    admin_password = 'Admin123!'
    
    # Check if user exists
    user, created = User.objects.get_or_create(
        email=admin_email,
        defaults={
            'full_name': 'System Administrator',
            'is_active': True
        }
    )
    
    if created or not user.has_usable_password():
        user.set_password(admin_password)
        user.save()
        print(f"User created/updated: {admin_email}")
    
    # Create admin profile
    admin_profile, admin_created = AdminUser.objects.get_or_create(
        user=user,
        defaults={
            'role': 'super_admin',
            'permissions': ['*'],  # All permissions
            'is_active': True
        }
    )
    
    if admin_created:
        print(f"Admin profile created with role: {admin_profile.role}")
    else:
        print(f"Admin profile already exists with role: {admin_profile.role}")
    
    print("\n=== Admin Credentials ===")
    print(f"Email: {admin_email}")
    print(f"Password: {admin_password}")
    print("========================")

if __name__ == '__main__':
    create_first_admin()