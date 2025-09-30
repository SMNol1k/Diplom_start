from rest_framework import viewsets, status, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
import yaml
import requests

from .models import (
    User, Shop, Category, Product, ProductInfo, Parameter, 
    ProductParameter, Contact, Order, OrderItem
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    ContactSerializer, ShopSerializer, CategorySerializer, 
    ProductInfoSerializer, OrderSerializer,
    OrderItemCreateSerializer, PasswordResetSerializer
)


class RegisterView(generics.CreateAPIView):
    """Регистрация нового пользователя"""
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """Вход пользователя"""
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        login(request, user)
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
        })


class LogoutView(generics.GenericAPIView):
    """Выход пользователя"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        logout(request)
        return Response({'detail': 'Успешный выход'}, status=status.HTTP_200_OK)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Профиль пользователя"""
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class ContactViewSet(viewsets.ModelViewSet):
    """ViewSet для управления контактами"""
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра категорий"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated]


class ShopViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра магазинов"""
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated]


class ProductInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для просмотра товаров"""
    serializer_class = ProductInfoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        queryset = ProductInfo.objects.select_related(
            'product', 'shop', 'product__category'
        ).prefetch_related(
            'product_parameters__parameter'
        ).filter(shop__state=True)

        # Фильтрация по магазину
        shop_id = self.request.query_params.get('shop_id')
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)

        # Фильтрация по категории
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)

        return queryset


class BasketViewSet(viewsets.ViewSet):
    """ViewSet для управления корзиной"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Получить корзину"""
        basket, created = Order.objects.get_or_create(
            user=request.user,
            status='basket'
        )
        serializer = OrderSerializer(basket)
        return Response(serializer.data)

    def create(self, request):
        """Добавить товар в корзину"""
        basket, created = Order.objects.get_or_create(
            user=request.user,
            status='basket'
        )

        serializer = OrderItemCreateSerializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data if isinstance(serializer.validated_data, list) else [serializer.validated_data]

        for item_data in items_data:
            product_info = get_object_or_404(ProductInfo, id=item_data['product_info_id'])
            
            if product_info.quantity < item_data['quantity']:
                return Response(
                    {'error': f'Недостаточно товара {product_info.product.name} на складе'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            order_item, created = OrderItem.objects.get_or_create(
                order=basket,
                product_info=product_info,
                defaults={'quantity': item_data['quantity'], 'price': product_info.price}
            )

            if not created:
                order_item.quantity += item_data['quantity']
                order_item.save()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['put'])
    def update_items(self, request):
        """Обновить количество товаров в корзине"""
        basket = get_object_or_404(Order, user=request.user, status='basket')
        
        serializer = OrderItemCreateSerializer(data=request.data, many=isinstance(request.data, list))
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data if isinstance(serializer.validated_data, list) else [serializer.validated_data]

        for item_data in items_data:
            order_item = get_object_or_404(
                OrderItem, 
                order=basket, 
                product_info_id=item_data['product_info_id']
            )
            order_item.quantity = item_data['quantity']
            order_item.save()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data)

    @action(detail=False, methods=['delete'])
    def delete_items(self, request):
        """Удалить товары из корзины"""
        basket = get_object_or_404(Order, user=request.user, status='basket')
        
        items_to_delete = request.data.get('items', [])
        if not items_to_delete:
            return Response({'error': 'Не указаны товары для удаления'}, status=status.HTTP_400_BAD_REQUEST)

        OrderItem.objects.filter(order=basket, product_info_id__in=items_to_delete).delete()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet для управления заказами"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.type == 'supplier' and hasattr(user, 'shop'):
            # Поставщик видит заказы, содержащие его товары
            return Order.objects.filter(
                order_items__product_info__shop=user.shop
            ).exclude(status='basket').distinct().order_by('-dt')
        else:
            # Покупатель видит свои заказы
            return Order.objects.filter(user=user).exclude(status='basket')

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Подтвердить заказ"""
        basket = get_object_or_404(Order, pk=pk, user=request.user, status='basket')

        contact_id = request.data.get('contact_id')
        if not contact_id:
            return Response({'error': 'Не указан адрес доставки'}, status=status.HTTP_400_BAD_REQUEST)

        contact = get_object_or_404(Contact, id=contact_id, user=request.user)

        if not basket.order_items.exists():
            return Response({'error': 'Корзина пуста'}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            basket.contact = contact
            basket.status = 'new'
            basket.save()

            # Отправка email клиенту
            self._send_order_confirmation_email(basket)

            # Отправка email администраторам поставщиков
            self._send_order_notification_to_suppliers(basket)

        serializer = self.get_serializer(basket)
        return Response(serializer.data)

    def _send_order_confirmation_email(self, order):
        """Отправка подтверждения заказа клиенту"""
        subject = f'Заказ №{order.id} принят'
        message = f'''
        Здравствуйте, {order.user.first_name or order.user.username}!

        Ваш заказ №{order.id} успешно оформлен.
        
        Товары:
        '''
        for item in order.order_items.all():
            message += f'\n- {item.product_info.product.name} x {item.quantity} = {item.total_price} руб.'
        
        message += f'\n\nОбщая сумма: {order.total_sum} руб.'
        message += f'\n\nАдрес доставки: {order.contact}'

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=True,
        )

    def _send_order_notification_to_suppliers(self, order):
        """Отправка уведомления о заказе поставщикам"""
        shops = set()
        for item in order.order_items.all():
            shops.add(item.product_info.shop)

        for shop in shops:
            shop_items = order.order_items.filter(product_info__shop=shop)
            
            subject = f'Новый заказ №{order.id}'
            message = f'''
            Новый заказ №{order.id} от {order.dt.strftime("%d.%m.%Y %H:%M")}

            Товары:
            '''
            for item in shop_items:
                message += f'\n- {item.product_info.product.name} (ID: {item.product_info.external_id}) x {item.quantity}'

            message += f'\n\nКлиент: {order.user.email}'
            message += f'\nАдрес доставки: {order.contact}'

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [shop.user.email],
                fail_silently=True,
            )


class SupplierViewSet(viewsets.ViewSet):
    """ViewSet для функций поставщика"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Получить информацию о магазине поставщика"""
        if request.user.type != 'supplier':
            return Response({'error': 'Доступ только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, 'shop'):
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)

        serializer = ShopSerializer(request.user.shop)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_state(self, request):
        """Обновить статус приема заказов"""
        if request.user.type != 'supplier':
            return Response({'error': 'Доступ только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, 'shop'):
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)

        state = request.data.get('state')
        if state is None:
            return Response({'error': 'Не указан параметр state'}, status=status.HTTP_400_BAD_REQUEST)

        request.user.shop.state = state
        request.user.shop.save()

        return Response({'status': 'Статус обновлен', 'state': request.user.shop.state})

    @action(detail=False, methods=['post'])
    def update_price(self, request):
        """Загрузить прайс-лист"""
        if request.user.type != 'supplier':
            return Response({'error': 'Доступ только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)

        if not hasattr(request.user, 'shop'):
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)

        url = request.data.get('url')
        if not url:
            return Response({'error': 'Не указан URL прайс-листа'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = yaml.safe_load(response.content)
        except Exception as e:
            return Response({'error': f'Ошибка загрузки файла: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        shop = request.user.shop

        with transaction.atomic():
            # Обновляем информацию о магазине
            if 'shop' in data:
                shop.name = data['shop']
                shop.save()

            # Обрабатываем категории
            categories_map = {}
            for cat_data in data.get('categories', []):
                category, _ = Category.objects.get_or_create(
                    id=cat_data['id'],
                    defaults={'name': cat_data['name']}
                )
                categories_map[cat_data['id']] = category
                if category not in shop.categories.all():
                    shop.categories.add(category)

            # Удаляем старые товары магазина
            ProductInfo.objects.filter(shop=shop).delete()

            # Добавляем новые товары
            for item_data in data.get('goods', []):
                category = categories_map.get(item_data['category'])
                if not category:
                    continue

                product, _ = Product.objects.get_or_create(
                    name=item_data['name'],
                    category=category
                )

                product_info = ProductInfo.objects.create(
                    product=product,
                    shop=shop,
                    external_id=item_data['id'],
                    model=item_data.get('model', ''),
                    quantity=item_data['quantity'],
                    price=item_data['price'],
                    price_rrc=item_data['price_rrc']
                )

                # Добавляем параметры товара
                for param_name, param_value in item_data.get('parameters', {}).items():
                    parameter, _ = Parameter.objects.get_or_create(name=param_name)
                    ProductParameter.objects.create(
                        product_info=product_info,
                        parameter=parameter,
                        value=param_value
                    )

        return Response({'status': 'Прайс-лист успешно загружен'})


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """Запрос на сброс пароля"""
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    try:
        user = User.objects.get(email=email)
        # В реальном приложении здесь нужно сгенерировать токен и отправить ссылку
        # Для демонстрации просто отправим уведомление
        send_mail(
            'Сброс пароля',
            f'Для сброса пароля перейдите по ссылке: http://example.com/reset-password',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=True,
        )
        return Response({'status': 'Письмо отправлено'})
    except User.DoesNotExist:
        # Не сообщаем, что пользователь не найден (безопасность)
        return Response({'status': 'Письмо отправлено'})
