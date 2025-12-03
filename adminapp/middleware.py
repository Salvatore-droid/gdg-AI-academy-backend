# adminapp/middleware.py

from django.utils.deprecation import MiddlewareMixin
from base.models import UserSession

class AdminAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware to authenticate admin requests for DRF.
    Sets request.user but lets DRF handle the responses.
    """
    def process_request(self, request):
        # Check if request is for admin endpoints
        if request.path.startswith('/api/admin/'):
            print(f"=== AdminAuthenticationMiddleware ===")
            print(f"Path: {request.path}")
            print(f"Method: {request.method}")
            
            # Skip for login and logout endpoints
            if request.path in ['/api/admin/auth/login/', '/api/admin/auth/logout/']:
                print("Skipping authentication for login/logout")
                return None
            
            # Extract token
            auth_header = request.headers.get('Authorization', '')
            token = None
            
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
                print(f"Token from Authorization header: {token[:20]}...")
            elif 'admin_token' in request.COOKIES:
                token = request.COOKIES.get('admin_token')
                print(f"Token from cookie: {token[:20]}...")
            
            if token:
                try:
                    session = UserSession.objects.get(token=token, is_active=True)
                    print(f"Found session for user: {session.user.email}")
                    
                    if session.is_valid():
                        user = session.user
                        if user.is_staff:
                            # Set user on request - THIS IS CRITICAL
                            request.user = user
                            request._cached_user = user  # Cache for performance
                            request.admin_session = session
                            print(f"User set on request: {request.user.email}")
                            print(f"Is staff: {request.user.is_staff}")
                        else:
                            print(f"User {user.email} is not staff")
                            # Don't return response, let DRF handle it
                            request.user = user  # Still set user
                    else:
                        print("Session invalid")
                        session.invalidate()
                except UserSession.DoesNotExist:
                    print(f"No session found for token: {token[:20]}...")
            else:
                print("No token found in request")
            
            print("===")
        
        return None  # Continue to next middleware/view