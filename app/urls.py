"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from django.views.generic import TemplateView
from django.http import HttpResponseRedirect

from social import views as social_views

def root(request):
    return HttpResponseRedirect("/admin/")

urlpatterns = [
    path("", root),
    path('admin/', admin.site.urls),
    path('social/', include('social.urls')),
    path('sns/ig/', include(('ig.urls', 'ig'), namespace='ig')),
    path('sns/th/', include(('th.urls', 'th'), namespace='th')),
    # Legacy app handles some webhooks but new endpoints are provided below
    path('webhooks/', include('social_webhooks.urls')),
    path('webhook/instagram/', social_views.webhook_instagram),
    path('webhook/threads/', social_views.webhook_threads),
    path('test/', TemplateView.as_view(template_name='test.html'), name='test'),
]
