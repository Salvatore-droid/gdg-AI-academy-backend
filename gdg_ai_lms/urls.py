"""
URL configuration for gdg_ai_lms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse

def api_root(request):
    return JsonResponse({
        'message': 'Google AI Learning Platform API',
        'endpoints': {
            'auth': {
                'login': '/api/auth/login/',
                'signup': '/api/auth/signup/',
                'logout': '/api/auth/logout/',
                'profile': '/api/auth/profile/',
                'change_password': '/api/auth/change-password/',
            }
        },
        'status': 'active'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('base.urls')),
    path('', api_root, name='api-root'),
]