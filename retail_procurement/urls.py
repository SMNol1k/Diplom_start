"""URL-конфигурация для приложения retail_procurement."""
from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    ContactViewSet, CategoryViewSet, ShopViewSet, ProductInfoViewSet,
    BasketViewSet, OrderViewSet, SupplierViewSet, password_reset_request,
    PasswordResetConfirmView
)

router = DefaultRouter()
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'shops', ShopViewSet, basename='shop')
router.register(r'products', ProductInfoViewSet, basename='product')
router.register(r'basket', BasketViewSet, basename='basket')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'supplier', SupplierViewSet, basename='supplier')

urlpatterns = [
    # Аутентификация
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/profile/', UserProfileView.as_view(), name='profile'),
    path('auth/password-reset/', password_reset_request, name='password-reset'), 
    re_path(r'^auth/password-reset-confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,900})/$',
            PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # API endpoints
    path('', include(router.urls)),
]
