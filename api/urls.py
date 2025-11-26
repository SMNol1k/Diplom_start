"""Основная URL-конфигурация проекта."""
from django.contrib import admin
from django.urls import path, include
from retail_procurement.views import PasswordResetConfirmView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('retail_procurement.urls')),
    path('api/auth/password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),  # JSON/YAML схема
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),  # Swagger UI
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),  # Альтернативный Redoc UI
    path('api/auth/', include('social_django.urls', namespace='social')),  # URL для соц. аутентификации
]
