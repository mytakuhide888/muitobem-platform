from django.urls import path
from .views.dashboard import dashboard   # ← 直接 import

app_name = "console"

urlpatterns = [
    path("", dashboard, name="index"),
]
