# adminapp/authentication.py - Create this file
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from django.views.decorators.csrf import csrf_exempt

class CsrfExemptSessionAuthentication(SessionAuthentication):
    """
    Session authentication with CSRF exemption for admin API.
    """
    def enforce_csrf(self, request):
        # Bypass CSRF for all admin API requests
        if request.path.startswith('/api/admin/'):
            return
        return super().enforce_csrf(request)