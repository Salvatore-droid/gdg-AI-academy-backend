# adminapp/permissions.py

from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        print(f"=== IsAdminUser Permission Check ===")
        print(f"Request method: {request.method}")
        print(f"Request path: {request.path}")
        print(f"View action: {getattr(view, 'action', 'Unknown')}")
        print(f"Request user: {request.user}")
        print(f"User is authenticated: {request.user.is_authenticated}")
        print(f"User is staff: {request.user.is_staff}")
        print(f"User email: {getattr(request.user, 'email', 'No email')}")
        
        # Check if user is authenticated
        if not request.user.is_authenticated:
            print("Permission result: False (not authenticated)")
            return False
        
        # Check if user is staff
        if not request.user.is_staff:
            print("Permission result: False (not staff)")
            return False
        
        print("Permission result: True")
        print("===")
        return True

class IsSuperAdmin(BasePermission):
    """
    Allows access only to super admin users.
    """
    def has_permission(self, request, view):
        print(f"=== IsSuperAdmin Permission Check ===")
        print(f"Request user: {request.user}")
        print(f"User is authenticated: {request.user.is_authenticated}")
        print(f"User is staff: {request.user.is_staff}")
        print(f"User is superuser: {request.user.is_superuser}")
        
        is_superadmin = bool(request.user and request.user.is_authenticated and 
                           request.user.is_staff and request.user.is_superuser)
        print(f"Permission result: {is_superadmin}")
        return is_superadmin

class AdminPermissionMixin:
    """
    Mixin to add admin permissions to views
    """
    permission_classes = [IsAdminUser]