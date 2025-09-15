# -*- coding: utf-8 -*-
from django.urls import path
from . import views

app_name = "console"

urlpatterns = [
    path("", views.dashboard, name="index"),
    path("connection-test/", views.connection_test, name="connection_test"),
    path("logs/", views.logs_view, name="logs"),
    path("integration/", views.integration, name="integration"),
    path("webhook-test/", views.webhook_test, name="webhook_test"),
    
]
