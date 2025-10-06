"""Сериализаторы для API системы розничных закупок."""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import (
    User, Shop, Category, Product, ProductInfo, Parameter, 
    ProductParameter, Contact, Order, OrderItem
)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор пользователя"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'company', 'position', 'type']
        read_only_fields = ['id']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Сериализатор регистрации пользователя"""
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2', 'first_name', 'last_name', 'company', 'position', 'type']

    def validate(self, attrs):
        """Валидация данных регистрации"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        return attrs

    def create(self, validated_data):
        """Создание пользователя"""
        validated_data.pop('password2')
        user = User.objects.create_user(**validated_data)
        return user


class LoginSerializer(serializers.Serializer):
    """Сериализатор входа"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Валидация учетных данных"""
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('Неверные учетные данные.')
            if not user.is_active:
                raise serializers.ValidationError('Аккаунт отключен.')
        else:
            raise serializers.ValidationError('Необходимо указать username и password.')

        attrs['user'] = user
        return attrs


class ContactSerializer(serializers.ModelSerializer):
    """Сериализатор контактов"""
    
    class Meta:
        model = Contact
        fields = ['id', 'first_name', 'last_name', 'patronymic', 'email', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone']
        read_only_fields = ['id']


class ShopSerializer(serializers.ModelSerializer):
    """Сериализатор магазина"""
    
    class Meta:
        model = Shop
        fields = ['id', 'name', 'url', 'state']
        read_only_fields = ['id']


class CategorySerializer(serializers.ModelSerializer):
    """Сериализатор категории"""
    
    class Meta:
        model = Category
        fields = ['id', 'name']
        read_only_fields = ['id']


class ProductSerializer(serializers.ModelSerializer):
    """Сериализатор товара"""
    category = serializers.StringRelatedField()
    
    class Meta:
        model = Product
        fields = ['id', 'name', 'category', 'description']
        read_only_fields = ['id']


class ProductParameterSerializer(serializers.ModelSerializer):
    """Сериализатор параметра товара"""
    parameter = serializers.StringRelatedField()
    
    class Meta:
        model = ProductParameter
        fields = ['parameter', 'value']


class ProductInfoSerializer(serializers.ModelSerializer):
    """Сериализатор информации о товаре"""
    product = ProductSerializer(read_only=True)
    shop = ShopSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(many=True, read_only=True)
    
    class Meta:
        model = ProductInfo
        fields = ['id', 'product', 'shop', 'model', 'quantity', 'price', 'price_rrc', 'product_parameters']
        read_only_fields = ['id']


class OrderItemSerializer(serializers.ModelSerializer):
    """Сериализатор позиции заказа"""
    product_info = ProductInfoSerializer(read_only=True)
    product_info_id = serializers.PrimaryKeyRelatedField(
        queryset=ProductInfo.objects.all(),
        source='product_info',
        write_only=True
    )
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = OrderItem
        fields = ['id', 'product_info', 'product_info_id', 'quantity', 'price', 'total_price']
        read_only_fields = ['id', 'price']

    def validate(self, attrs):
        """Валидация позиции заказа"""
        product_info = attrs.get('product_info')
        quantity = attrs.get('quantity')

        if product_info and quantity:
            # Автоматически устанавливаем цену из ProductInfo
            attrs['price'] = product_info.price

            # Проверяем наличие товара на складе
            if product_info.quantity < quantity:
                raise serializers.ValidationError(
                    {'quantity': f'Недостаточно товара "{product_info.product.name}" на складе. Доступно: {product_info.quantity}'}
                )   
        return attrs


class OrderSerializer(serializers.ModelSerializer):
    """Сериализатор заказа"""
    order_items = OrderItemSerializer(many=True, read_only=True)
    total_sum = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    contact = ContactSerializer(read_only=True)
    
    class Meta:
        model = Order
        fields = ['id', 'dt', 'status', 'order_items', 'total_sum', 'contact']
        read_only_fields = ['id', 'dt']


class OrderItemCreateSerializer(serializers.Serializer):
    """Сериализатор для добавления товаров в корзину"""
    product_info_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class PasswordResetSerializer(serializers.Serializer):
    """Сериализатор сброса пароля"""
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Сериализатор подтверждения сброса пароля"""
    token = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True)

    def validate(self, attrs):
        """Валидация нового пароля"""
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Пароли не совпадают."})
        return attrs
