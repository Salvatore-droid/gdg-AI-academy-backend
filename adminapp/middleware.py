from django.http import JsonResponse
from base.models import UserSession
from django.utils import timezone

class AdminAuthenticationMiddleware:
    """
    Middleware to authenticate admin requests
    """
    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_paths = [
            '/api/admin/',
            '/admin-api/',
        ]
    
    def __call__(self, request):
        # Check if request is for admin endpoints
        is_admin_path = any(request.path.startswith(path) for path in self.admin_paths)
        
        # Allow login and logout endpoints without authentication
        if request.path in ['/api/admin/auth/login/', '/api/admin/auth/logout/']:
            return self.get_response(request)
        
        if is_admin_path:
            # Extract token
            auth_header = request.headers.get('Authorization', '')
            token = None
            
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
            elif 'admin_token' in request.COOKIES:
                token = request.COOKIES.get('admin_token')
            
            if token:
                try:
                    session = UserSession.objects.get(token=token, is_active=True)
                    if session.is_valid():
                        user = session.user
                        if user.is_staff:
                            request.user = user
                            request.admin_session = session
                            # Continue to the view
                            return self.get_response(request)
                        else:
                            return JsonResponse(
                                {'error': 'Admin access required'}, 
                                status=403
                            )
                    else:
                        session.invalidate()
                        return JsonResponse(
                            {'error': 'Session expired'}, 
                            status=401
                        )
                except UserSession.DoesNotExist:
                    return JsonResponse(
                        {'error': 'Invalid authentication token'}, 
                        status=401
                    )
            else:
                return JsonResponse(
                    {'error': 'Authentication required'}, 
                    status=401
                )
        
        response = self.get_response(request)
        return response