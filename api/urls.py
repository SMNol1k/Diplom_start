"""Основная URL-конфигурация проекта."""
from django.contrib import admin
from django.urls import path, include
from retail_procurement.views import PasswordResetConfirmView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('retail_procurement.urls')),
    path('api/auth/password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
]
