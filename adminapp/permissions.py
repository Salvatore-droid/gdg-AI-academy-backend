from rest_framework.permissions import BasePermission

class IsAdminUser(BasePermission):
    """
    Allows access only to admin users.
    """
    def has_permission(self, request, view):
        print(f"=== IsAdminUser Permission Check ===")
        print(f"Request user: {request.user}")
        print(f"User is authenticated: {request.user.is_authenticated}")
        print(f"User is staff: {request.user.is_staff}")
        print(f"User email: {getattr(request.user, 'email', 'No email')}")
        
        # Check if user is authenticated and is staff
        is_admin = bool(request.user and request.user.is_authenticated and request.user.is_staff)
        print(f"Permission result: {is_admin}")
        print("===")
        
        return is_admin

class IsSuperAdmin(BasePermission):
    """
    Allows access only to super admin users.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and 
                   request.user.is_staff and request.user.is_superuser)

class AdminPermissionMixin:
    """
    Mixin to add admin permissions to views
    """
    permission_classes = [IsAdminUser]