"""Регистрация моделей в админке Django."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    User, Shop, Category, Product, ProductInfo, Parameter,
    ProductParameter, Contact, Order, OrderItem
)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Админка пользователей"""
    list_display = ['username', 'email', 'first_name', 'last_name', 'type', 'is_staff']
    list_filter = ['type', 'is_staff', 'is_active']
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Дополнительная информация', {'fields': ('company', 'position', 'type')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Дополнительная информация', {'fields': ('email', 'company', 'position', 'type')}),
    )


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """Админка магазинов"""
    list_display = ['name', 'user', 'state', 'url']
    list_filter = ['state']
    search_fields = ['name', 'user__username']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Админка категорий"""
    list_display = ['name']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Админка товаров"""
    list_display = ['name', 'category', 'description']
    list_filter = ['category']
    search_fields = ['name', 'description']


class ProductParameterInline(admin.TabularInline):
    """Инлайн для параметров товара"""
    model = ProductParameter
    extra = 0


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """Админка информации о товарах"""
    list_display = ['product', 'shop', 'external_id', 'quantity', 'price', 'price_rrc']
    list_filter = ['shop']
    search_fields = ['product__name', 'shop__name', 'model']
    inlines = [ProductParameterInline]


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """Админка параметров"""
    list_display = ['name']
    search_fields = ['name']


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """Админка контактов"""
    list_display = ['user', 'first_name', 'last_name', 'city', 'street', 'house', 'phone']
    list_filter = ['city']
    search_fields = ['user__username', 'first_name', 'last_name', 'city', 'street', 'phone'] 


class OrderItemInline(admin.TabularInline):
    """Инлайн для позиций заказа"""
    model = OrderItem
    extra = 0
    readonly_fields = ['price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Админка заказов"""
    list_display = ['id', 'user', 'dt', 'status', 'total_sum', 'contact']
    list_filter = ['status', 'dt']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['dt', 'total_sum']
    inlines = [OrderItemInline]
    
    def total_sum(self, obj):
        """Общая сумма заказа"""
        return obj.total_sum
    total_sum.short_description = 'Общая сумма'


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """Админка позиций заказов"""
    list_display = ['order', 'product_info', 'quantity', 'price', 'total_price']
    list_filter = ['order__status']
    search_fields = ['order__id', 'product_info__product__name']
    readonly_fields = ['price', 'total_price']
