from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
import os
import getpass

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates the first super admin user for the system'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Creating first admin user...'))
        
        # Check if any admin already exists
        if User.objects.filter(is_staff=True, is_superuser=True).exists():
            self.stdout.write(self.style.WARNING('Admin user already exists!'))
            return
        
        # Get admin details
        email = input('Enter admin email: ').strip()
        full_name = input('Enter admin full name: ').strip()
        
        # Get password securely
        while True:
            password = getpass.getpass('Enter admin password: ')
            confirm_password = getpass.getpass('Confirm admin password: ')
            
            if password != confirm_password:
                self.stdout.write(self.style.ERROR('Passwords do not match!'))
                continue
            
            if len(password) < 8:
                self.stdout.write(self.style.ERROR('Password must be at least 8 characters!'))
                continue
            
            break
        
        # Create the admin user
        try:
            with transaction.atomic():
                admin = User.objects.create_superuser(
                    email=email,
                    full_name=full_name,
                    password=password
                )
                
                # Add additional admin metadata
                admin.is_active = True
                admin.is_staff = True
                admin.is_superuser = True
                admin.save()
                
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Super admin created successfully!\n'
                    f'  Email: {email}\n'
                    f'  Name: {full_name}\n'
                    f'  ID: {admin.id}'
                ))
                
                # Generate initial access token
                from base.models import UserSession
                session = UserSession.create_session(admin)
                self.stdout.write(self.style.SUCCESS(
                    f'✓ Initial access token generated\n'
                    f'  Token: {session.token}'
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error creating admin: {str(e)}'))