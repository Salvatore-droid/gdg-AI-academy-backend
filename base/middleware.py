from django.utils.deprecation import MiddlewareMixin
from .models import UserSession

class JWTAuthenticationMiddleware(MiddlewareMixin):
    """Custom JWT authentication middleware"""
    
    def process_request(self, request):
        """Add user to request if valid token is provided"""
        request.user = None
        
        auth_header = request.headers.get('Authorization', '')
        
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                # Check if session is valid
                session = UserSession.objects.get(token=token, is_active=True)
                if session.is_valid():
                    request.user = session.user
            except UserSession.DoesNotExist:
                # Token not found or session invalid
                pass