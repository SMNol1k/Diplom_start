from rest_framework import viewsets, status, generics, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.authtoken.models import Token
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import login, logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_str 
from django.utils.http import urlsafe_base64_decode
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
import yaml
import requests
from django.core.exceptions import ObjectDoesNotExist

from .models import (
    User, Shop, Category, Product, ProductInfo, Parameter, 
    ProductParameter, Contact, Order, OrderItem
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    ContactSerializer, ShopSerializer, CategorySerializer, 
    ProductInfoSerializer, OrderSerializer,
    OrderItemCreateSerializer, PasswordResetSerializer,
    PasswordResetConfirmSerializer
)

from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.template.loader import render_to_string
from django.urls import reverse # Для генерации URL
from django.contrib.sites.shortcuts import get_current_site # Для получения домена сайта

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
    filter_backends = [DjangoFilterBackend, filters.SearchFilter] # Добавлено
    filterset_fields = ['shop', 'product__category'] # Фильтрация по shop_id и category_id
    search_fields = ['product__name', 'product__description', 'model', 'product_parameters__value'] # Добавлено

    def get_queryset(self):
        queryset = ProductInfo.objects.select_related(
            'product', 'shop', 'product__category'
        ).prefetch_related(
            'product_parameters__parameter'
        ).filter(shop__state=True)

        # # Фильтрация по магазину
        # shop_id = self.request.query_params.get('shop_id')
        # if shop_id:
        #     queryset = queryset.filter(shop_id=shop_id)

        # # Фильтрация по категории
        # category_id = self.request.query_params.get('category_id')
        # if category_id:
        #     queryset = queryset.filter(product__category_id=category_id)

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
        # Используем OrderItemSerializer для валидации и установки цены
        # Передаем order_id для контекста
        serializer = OrderItemCreateSerializer(
            data=request.data, 
            many=isinstance(request.data, list),
            context={'request': request}
            )
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data if isinstance(serializer.validated_data, list) else [serializer.validated_data]

        with transaction.atomic():
            for item_data in items_data:
                product_info = item_data['product_info_id'] # уже объект благодаря PrimaryKeyRelatedField
                quantity = item_data['quantity']
                price = item_data['price']

                order_item, created = OrderItem.objects.get_or_create(
                    order=basket,
                    product_info=product_info,
                    defaults={'quantity': quantity,
                              'price': price,
                              }
                )

                if not created:
                    order_item.quantity += quantity
                    order_item.price = price
                    order_item.save()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['put'])
    def update_items(self, request):
        """Обновить количество товаров в корзине"""
        basket = get_object_or_404(Order, user=request.user, status='basket')

        # Используем OrderItemSerializer для валидации и установки цены
        serializer = OrderItemCreateSerializer(data=request.data, 
                                               many=isinstance(request.data, list),
                                               context={'request': request}
                                               )
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data if isinstance(serializer.validated_data, list) else [serializer.validated_data]

        with transaction.atomic():
            for item_data in items_data:
                product_info = item_data['product_info']
                quantity = item_data['quantity']
                price = item_data['price']

                order_item = get_object_or_404(
                    OrderItem, 
                    order=basket, 
                    product_info=product_info
                )
                order_item.quantity = quantity
                order_item.price = price
                order_item.save()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data)

    @action(detail=False, methods=['delete'])
    def delete_items(self, request):
        """Удалить товары из корзины"""
        basket = get_object_or_404(Order, user=request.user, status='basket')
        
        items_to_delete_ids = request.data.get('items', [])
        if not items_to_delete_ids:
            return Response({'error': 'Не указаны товары для удаления'}, status=status.HTTP_400_BAD_REQUEST)

        # Проверяем, что все ID существуют в корзине пользователя
        existing_items_count = OrderItem.objects.filter(
            order=basket,
            product_info_id__in=items_to_delete_ids
        ).count()

        if existing_items_count != len(items_to_delete_ids):
            return Response({'error': 'Один или несколько товаров не найдены в вашей корзине'}, status=status.HTTP_400_BAD_REQUEST)        

        OrderItem.objects.filter(order=basket, product_info_id__in=items_to_delete_ids).delete()

        basket_serializer = OrderSerializer(basket)
        return Response(basket_serializer.data, status=status.HTTP_200_OK)


class OrderViewSet(viewsets.ModelViewSet):
    """ViewSet для управления заказами"""
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Order.objects.exclude(status='basket').select_related('contact', 'user').prefetch_related('order_items__product_info__product')
        
        if user.type == 'supplier' and hasattr(user, 'shop'):
            # Поставщик видит заказы, содержащие его товары
            return queryset.filter(order_items__product_info__shop=user.shop).distinct().order_by('-dt')
        else:
            # Покупатель видит свои заказы
            return queryset.filter(user=user).order_by('-dt')

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
            # Проверяем наличие всех товаров в корзине перед подтверждением
            for item in basket.order_items.all():
                if item.product_info.quantity < item.quantity:
                    return Response(
                        {'error': f'Недостаточно товара "{item.product_info.product.name}" на складе магазина "{item.product_info.shop.name}". Доступно: {item.product_info.quantity}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                # Уменьшаем количество товара на складе
                item.product_info.quantity -= item.quantity
                item.product_info.save()

            basket.contact = contact
            basket.status = 'new'
            basket.save()

            # Отправка email клиенту
            self._send_order_confirmation_email(basket)

            # Отправка email администраторам поставщиков
            self._send_order_notification_to_suppliers(basket)

        serializer = self.get_serializer(basket)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def _send_order_confirmation_email(self, order):
        """Отправка подтверждения заказа клиенту"""
        order_items = order.order_items.select_related('product_info__product').all()
        subject = f'Заказ №{order.id} принят'
        message = f'''
        Здравствуйте, {order.user.first_name or order.user.username}!

        Ваш заказ №{order.id} успешно оформлен.
        
        Товары:
        '''
        for item in order_items:
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
        order_items = order.order_items.select_related('product_info__shop', 'product_info__product').all()
        
        shops = set()
        for item in order.order_items:
            shops.add(item.product_info.shop)

        for shop in shops:
            shop_items = [item for item in order_items if item.product_info.shop == shop]
            
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

        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def update_state(self, request):
        """Обновить статус приема заказов"""
        if request.user.type != 'supplier':
            return Response({'error': 'Доступ только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)

        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)

        state = request.data.get('state')
        if state is None or not isinstance(state, bool):
            return Response({'error': 'Не указан или неверный параметр state (ожидается true/false)'}, status=status.HTTP_400_BAD_REQUEST)
        
        shop.state = state
        shop.save()

        return Response({'status': 'Статус обновлен', 'state': shop.state}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'])
    def update_price(self, request):
        """Загрузить прайс-лист"""
        if request.user.type != 'supplier':
            return Response({'error': 'Доступ только для поставщиков'}, status=status.HTTP_403_FORBIDDEN)

        try:
            shop = request.user.shop
        except Shop.DoesNotExist:
            return Response({'error': 'У пользователя нет магазина'}, status=status.HTTP_404_NOT_FOUND)
        
        url = request.data.get('url')
        if not url:
            return Response({'error': 'Не указан URL прайс-листа'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = yaml.safe_load(response.content)
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к URL: {e}")  # Лог в консоль
            return Response({'error': f'Ошибка при запросе к URL: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except yaml.YAMLError as e:
            print(f"Ошибка парсинга YAML: {e}")
            return Response({'error': f'Ошибка парсинга YAML файла: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Неизвестная ошибка при загрузке: {e}")
            return Response({'error': f'Неизвестная ошибка при загрузке файла: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        if not data:
            return Response({'error': 'Пустой YAML файл'}, status=status.HTTP_400_BAD_REQUEST)

        if 'shop' in data and data['shop']:
            shop.name = data['shop']
            shop.save()
            print(f"Обновлено имя магазина: {shop.name}")

        # Обрабатываем категории: создаём/обновляем по name, маппим по id из YAML
        categories_map = {} 
        current_shop_categories = set(shop.categories.values_list('id', flat=True))
        new_categories_ids = set()

        for cat_data in data.get('categories', []):
            cat_id = cat_data.get('id')  # ID из YAML (для маппинга)
            cat_name = cat_data.get('name')
            if not cat_name:
                print(f"Пропущена категория без name: {cat_data}")
                continue

            category, created = Category.objects.get_or_create(name=cat_name)
            if created:
                print(f"Создана категория: {cat_name}")
            else:
                print(f"Найдена категория: {cat_name}")

            if cat_id:
                categories_map[cat_id] = category
                new_categories_ids.add(category.id)

            if category not in shop.categories.all():
                shop.categories.add(category)

        # Удаляем категории магазина, которых нет в новом прайс-листе (по реальным ID)
        categories_to_remove = current_shop_categories - new_categories_ids
        if categories_to_remove:
            shop.categories.remove(*Category.objects.filter(id__in=categories_to_remove))
            print(f"Удалены категории магазина: {categories_to_remove}")

        # Поддержка 'goods' (список) или 'products' (словарь для совместимости)
        items = data.get('goods', [])
        if not items and 'products' in data:
            items = [{'id': key, **value} for key, value in data['products'].items()]
            print("Обработан 'products' как словарь, преобразован в список")

        if not items:
            return Response({'error': "Нет товаров в YAML (ни 'goods', ни 'products')"}, status=status.HTTP_400_BAD_REQUEST)

        updated_count = 0
        with transaction.atomic():
            for item_data in items:
                try:
                    required_fields = ['id', 'name', 'category', 'quantity', 'price']
                    if not all(field in item_data for field in required_fields):
                        print(f"Пропущен товар без обязательных полей: {item_data.get('name', 'Unknown')}")
                        continue

                    external_id = str(item_data['id'])
                    category_id_yaml = item_data['category']  # ID из YAML
                    category = categories_map.get(category_id_yaml)
                    if not category:
                        print(f"Пропущен товар {external_id} без категории (ID {category_id_yaml}): {item_data.get('name', 'Unknown')}")
                        continue

                    product, _ = Product.objects.get_or_create(
                        name=item_data['name'],
                        defaults={'category': category}
                    )

                    product_info, created = ProductInfo.objects.update_or_create(
                        external_id=external_id,
                        shop=shop,
                        defaults={
                            'product': product,
                            'model': item_data.get('model', ''),
                            'quantity': item_data['quantity'],
                            'price': float(item_data['price']),
                            'price_rrc': float(item_data.get('price_rrc', 0)) if item_data.get('price_rrc') is not None else None
                        }
                    )
                    if created:
                        print(f"Создана ProductInfo: {external_id} - {item_data['name']}")
                    else:
                        print(f"Обновлена ProductInfo: {external_id} - {item_data['name']}")

                    for param_name, param_value in item_data.get('parameters', {}).items():
                        if not param_name or param_value is None:
                            continue
                        param_value_str = str(param_value)
                        parameter, _ = Parameter.objects.get_or_create(name=param_name)
                        ProductParameter.objects.update_or_create(
                            product_info=product_info,
                            parameter=parameter,
                            defaults={'value': param_value_str}
                        )
                        print(f"Добавлен/обновлён параметр: {param_name} = {param_value_str} для {external_id}")

                    updated_count += 1

                except Exception as e:
                    print(f"Ошибка при обработке товара {item_data.get('id', 'Unknown')}: {e}")
                    continue

        return Response({
            'status': 'Прайс-лист успешно загружен',
            'updated_products': updated_count,
            'message': f'Обработано {len(items)} товаров, обновлено {updated_count} в магазине "{shop.name}"'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_request(request):
    """Запрос на сброс пароля"""
    serializer = PasswordResetSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    
    email = serializer.validated_data['email']
    try:
        user = User.objects.get(email=email)

        # Генерация токена сброса пароля
        current_site = get_current_site(request)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = PasswordResetTokenGenerator().make_token(user)

        reset_url = f"http://{current_site.domain}{reverse('password-reset-confirm', kwargs={'uidb64': uid, 'token': token})}"
        # Внимание: 'password-reset-confirm' - это имя URL, которое добавлено в urls.py

        subject = 'Сброс пароля для вашего аккаунта'
        message = render_to_string('email/password_reset_email.html', {
            'user': user,
            'domain': current_site.domain,
            'uid': uid,
            'token': token,
            'reset_url': reset_url, # Передаем сгенерированный URL
        })

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False, # Устанавливаем False, чтобы видеть ошибки отправки в консоли
        )
        return Response({'status': 'Письмо для сброса пароля отправлено'}, status=status.HTTP_200_OK)
    except User.DoesNotExist:
        # Не сообщаем, что пользователь не найден (безопасность)
        return Response({'status': 'Письмо для сброса пароля отправлено'}, status=status.HTTP_200_OK)
    except Exception as e:
        # Логируем ошибку отправки почты
        print(f"Ошибка при отправке письма для сброса пароля: {e}")
        return Response({'error': 'Произошла ошибка при отправке письма'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PasswordResetConfirmView(generics.GenericAPIView):
    """Подтверждение сброса пароля"""
    permission_classes = [AllowAny]
    serializer_class = PasswordResetConfirmSerializer
    def post(self, request, uidb64, token):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None
        if user is not None and PasswordResetTokenGenerator().check_token(user, token):
            user.set_password(serializer.validated_data['password'])
            user.save()
            return Response({'status': 'Пароль успешно изменен'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Неверная ссылка для сброса пароля или истек срок действия'}, status=status.HTTP_400_BAD_REQUEST)

