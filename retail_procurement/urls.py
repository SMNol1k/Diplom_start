from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterView, LoginView, LogoutView, UserProfileView,
    ContactViewSet, CategoryViewSet, ShopViewSet, ProductInfoViewSet,
    BasketViewSet, OrderViewSet, SupplierViewSet, password_reset_request
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
    
    # API endpoints
    path('', include(router.urls)),
]
