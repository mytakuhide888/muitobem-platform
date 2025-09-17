# app/console/urls_public.py
from django.urls import path
from .views import oauth as v, webhooks as w

app_name = "console_public"

urlpatterns = [
    path("connect/",  v.meta_connect,  name="meta_connect"),
    path("callback/", v.meta_callback, name="meta_callback"),
    path("import/",   v.meta_import,   name="meta_import"),
    path("meta/oauth/start/",    v.meta_oauth_start,   name="meta_oauth_start"),
    path("meta/oauth/callback/", v.meta_oauth_cb,      name="meta_oauth_cb"),
    path("meta/oauth/import/",   v.meta_import,        name="meta_import"),
    path("meta/webhook/",        w.meta_webhook,       name="meta_webhook"),
]
