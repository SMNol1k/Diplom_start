"""Тесты для приложения retail_procurement."""
from django.test import TestCase
from django.contrib.auth import authenticate
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.core import mail
from unittest.mock import patch, MagicMock
import yaml

from .models import (
    User, Shop, Category, Product, ProductInfo, Parameter,
    ProductParameter, Contact, Order, OrderItem
)
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    ContactSerializer, ShopSerializer, CategorySerializer,
    ProductInfoSerializer, OrderSerializer, OrderItemSerializer,
    PasswordResetSerializer, PasswordResetConfirmSerializer
)


class UserModelTest(TestCase):
    """Тесты для модели User"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'company': 'Test Company',
            'position': 'Manager',
            'type': 'buyer'
        }
        self.user = User.objects.create_user(**self.user_data, password='testpass123')

    def test_user_creation(self):
        """Тест создания пользователя"""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.type, 'buyer')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_str(self):
        """Тест строкового представления пользователя"""
        expected_str = 'testuser (Покупатель)'
        self.assertEqual(str(self.user), expected_str)

    def test_supplier_user_str(self):
        """Тест строкового представления поставщика"""
        supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        expected_str = 'supplier (Поставщик)'
        self.assertEqual(str(supplier), expected_str)


class ShopModelTest(TestCase):
    """Тесты для модели Shop"""

    def setUp(self):
        """Создание тестовых данных"""
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        self.shop = Shop.objects.create(
            name='Test Shop',
            url='https://testshop.com',
            user=self.supplier,
            state=True
        )

    def test_shop_creation(self):
        """Тест создания магазина"""
        self.assertEqual(self.shop.name, 'Test Shop')
        self.assertEqual(self.shop.url, 'https://testshop.com')
        self.assertEqual(self.shop.user, self.supplier)
        self.assertTrue(self.shop.state)

    def test_shop_str(self):
        """Тест строкового представления магазина"""
        self.assertEqual(str(self.shop), 'Test Shop')


class CategoryModelTest(TestCase):
    """Тесты для модели Category"""

    def setUp(self):
        """Создание тестовых данных"""
        self.category = Category.objects.create(name='Test Category')

    def test_category_creation(self):
        """Тест создания категории"""
        self.assertEqual(self.category.name, 'Test Category')

    def test_category_str(self):
        """Тест строкового представления категории"""
        self.assertEqual(str(self.category), 'Test Category')


class ProductModelTest(TestCase):
    """Тесты для модели Product"""

    def setUp(self):
        """Создание тестовых данных"""
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category,
            description='Test description'
        )

    def test_product_creation(self):
        """Тест создания товара"""
        self.assertEqual(self.product.name, 'Test Product')
        self.assertEqual(self.product.category, self.category)
        self.assertEqual(self.product.description, 'Test description')

    def test_product_str(self):
        """Тест строкового представления товара"""
        self.assertEqual(str(self.product), 'Test Product')


class ProductInfoModelTest(TestCase):
    """Тесты для модели ProductInfo"""

    def setUp(self):
        """Создание тестовых данных"""
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        self.shop = Shop.objects.create(
            name='Test Shop',
            user=self.supplier,
            state=True
        )
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category
        )
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            model='Test Model',
            quantity=100,
            price=10.99,
            price_rrc=15.99
        )

    def test_product_info_creation(self):
        """Тест создания информации о товаре"""
        self.assertEqual(self.product_info.product, self.product)
        self.assertEqual(self.product_info.shop, self.shop)
        self.assertEqual(self.product_info.external_id, 123)
        self.assertEqual(self.product_info.model, 'Test Model')
        self.assertEqual(self.product_info.quantity, 100)
        self.assertEqual(self.product_info.price, 10.99)
        self.assertEqual(self.product_info.price_rrc, 15.99)

    def test_product_info_str(self):
        """Тест строкового представления информации о товаре"""
        expected_str = 'Test Product (Test Shop)'
        self.assertEqual(str(self.product_info), expected_str)

    def test_unique_constraint(self):
        """Тест уникальности product_info"""
        with self.assertRaises(Exception):
            ProductInfo.objects.create(
                product=self.product,
                shop=self.shop,
                external_id=123,  # тот же external_id для того же product и shop
                quantity=50,
                price=9.99
            )


class ParameterModelTest(TestCase):
    """Тесты для модели Parameter"""

    def setUp(self):
        """Создание тестовых данных"""
        self.parameter = Parameter.objects.create(name='Test Parameter')

    def test_parameter_creation(self):
        """Тест создания параметра"""
        self.assertEqual(self.parameter.name, 'Test Parameter')

    def test_parameter_str(self):
        """Тест строкового представления параметра"""
        self.assertEqual(str(self.parameter), 'Test Parameter')


class ProductParameterModelTest(TestCase):
    """Тесты для модели ProductParameter"""

    def setUp(self):
        """Создание тестовых данных"""
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        self.shop = Shop.objects.create(name='Test Shop', user=self.supplier)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=100,
            price=10.99
        )
        self.parameter = Parameter.objects.create(name='Color')
        self.product_parameter = ProductParameter.objects.create(
            product_info=self.product_info,
            parameter=self.parameter,
            value='Red'
        )

    def test_product_parameter_creation(self):
        """Тест создания параметра товара"""
        self.assertEqual(self.product_parameter.product_info, self.product_info)
        self.assertEqual(self.product_parameter.parameter, self.parameter)
        self.assertEqual(self.product_parameter.value, 'Red')

    def test_product_parameter_str(self):
        """Тест строкового представления параметра товара"""
        expected_str = 'Color: Red'
        self.assertEqual(str(self.product_parameter), expected_str)

    def test_unique_constraint(self):
        """Тест уникальности product_parameter"""
        with self.assertRaises(Exception):
            ProductParameter.objects.create(
                product_info=self.product_info,
                parameter=self.parameter,  # тот же parameter для того же product_info
                value='Blue'
            )


class ContactModelTest(TestCase):
    """Тесты для модели Contact"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.contact = Contact.objects.create(
            user=self.user,
            first_name='John',
            last_name='Doe',
            patronymic='Smith',
            email='john@example.com',
            city='Moscow',
            street='Lenin Street',
            house='10',
            structure='A',
            building='1',
            apartment='5',
            phone='+7(999)123-45-67'
        )

    def test_contact_creation(self):
        """Тест создания контакта"""
        self.assertEqual(self.contact.user, self.user)
        self.assertEqual(self.contact.first_name, 'John')
        self.assertEqual(self.contact.last_name, 'Doe')
        self.assertEqual(self.contact.city, 'Moscow')
        self.assertEqual(self.contact.phone, '+7(999)123-45-67')

    def test_contact_str(self):
        """Тест строкового представления контакта"""
        expected_str = 'Moscow, Lenin Street 10 (John Doe)'
        self.assertEqual(str(self.contact), expected_str)


class OrderModelTest(TestCase):
    """Тесты для модели Order"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.contact = Contact.objects.create(
            user=self.user,
            city='Moscow',
            street='Lenin Street',
            house='10',
            phone='+7(999)123-45-67'
        )
        self.order = Order.objects.create(
            user=self.user,
            status='new',
            contact=self.contact
        )

    def test_order_creation(self):
        """Тест создания заказа"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.status, 'new')
        self.assertEqual(self.order.contact, self.contact)

    def test_order_str(self):
        """Тест строкового представления заказа"""
        expected_str = f'Заказ №{self.order.id} от {self.order.dt.strftime("%d.%m.%Y")}'
        self.assertEqual(str(self.order), expected_str)

    def test_total_sum_property(self):
        """Тест свойства total_sum"""
        # Создаем товары для заказа
        supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        shop = Shop.objects.create(name='Test Shop', user=supplier)
        category = Category.objects.create(name='Test Category')
        product = Product.objects.create(name='Test Product', category=category)
        product_info = ProductInfo.objects.create(
            product=product,
            shop=shop,
            external_id=123,
            quantity=100,
            price=10.50
        )

        # Создаем позиции заказа
        OrderItem.objects.create(
            order=self.order,
            product_info=product_info,
            quantity=2,
            price=10.50
        )
        OrderItem.objects.create(
            order=self.order,
            product_info=product_info,
            quantity=1,
            price=10.50
        )

        # Проверяем общую сумму
        expected_total = 2 * 10.50 + 1 * 10.50  # 31.50
        self.assertEqual(self.order.total_sum, expected_total)


class OrderItemModelTest(TestCase):
    """Тесты для модели OrderItem"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        self.shop = Shop.objects.create(name='Test Shop', user=self.supplier)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=100,
            price=10.99,
            price_rrc=15.99
        )
        self.order = Order.objects.create(user=self.user, status='basket')
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product_info=self.product_info,
            quantity=5,
            price=10.99
        )

    def test_order_item_creation(self):
        """Тест создания позиции заказа"""
        self.assertEqual(self.order_item.order, self.order)
        self.assertEqual(self.order_item.product_info, self.product_info)
        self.assertEqual(self.order_item.quantity, 5)
        self.assertEqual(self.order_item.price, 10.99)

    def test_order_item_str(self):
        """Тест строкового представления позиции заказа"""
        expected_str = 'Test Product x 5'
        self.assertEqual(str(self.order_item), expected_str)

    def test_total_price_property(self):
        """Тест свойства total_price"""
        expected_total = 5 * 10.99
        self.assertEqual(self.order_item.total_price, expected_total)

    def test_unique_constraint(self):
        """Тест уникальности order_item"""
        with self.assertRaises(Exception):
            OrderItem.objects.create(
                order=self.order,
                product_info=self.product_info,  # тот же product_info для того же order
                quantity=3,
                price=10.99
            )


class SerializerTestCase(TestCase):
    """Базовый класс для тестов сериализаторов"""

    def setUp(self):
        """Создание тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            type='supplier',
            password='testpass123'
        )
        self.shop = Shop.objects.create(name='Test Shop', user=self.supplier)
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(name='Test Product', category=self.category)
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=100,
            price=10.99,
            price_rrc=15.99
        )
        self.contact = Contact.objects.create(
            user=self.user,
            city='Moscow',
            street='Lenin Street',
            house='10',
            phone='+7(999)123-45-67'
        )
        self.order = Order.objects.create(user=self.user, status='basket')
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product_info=self.product_info,
            quantity=2,
            price=10.99
        )


class UserSerializerTest(SerializerTestCase):
    """Тесты для UserSerializer"""

    def test_user_serializer(self):
        """Тест сериализации пользователя"""
        serializer = UserSerializer(self.user)
        data = serializer.data
        self.assertEqual(data['username'], 'testuser')
        self.assertEqual(data['email'], 'test@example.com')
        self.assertEqual(data['type'], 'buyer')


class UserRegistrationSerializerTest(TestCase):
    """Тесты для UserRegistrationSerializer"""

    def test_valid_registration_data(self):
        """Тест валидных данных регистрации"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
            'type': 'buyer'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_password_mismatch(self):
        """Тест несовпадающих паролей"""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepass123',
            'password2': 'differentpass123',
            'type': 'buyer'
        }
        serializer = UserRegistrationSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)


class LoginSerializerTest(TestCase):
    """Тесты для LoginSerializer"""

    def setUp(self):
        """Создание тестового пользователя"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

    def test_valid_login(self):
        """Тест валидного входа"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }
        serializer = LoginSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['user'], self.user)

    def test_invalid_login(self):
        """Тест невалидного входа"""
        data = {
            'username': 'testuser',
            'password': 'wrongpass'
        }
        serializer = LoginSerializer(data=data)
        self.assertFalse(serializer.is_valid())


class ContactSerializerTest(SerializerTestCase):
    """Тесты для ContactSerializer"""

    def test_contact_serializer(self):
        """Тест сериализации контакта"""
        serializer = ContactSerializer(self.contact)
        data = serializer.data
        self.assertEqual(data['city'], 'Moscow')
        self.assertEqual(data['street'], 'Lenin Street')
        self.assertEqual(data['house'], '10')


class ShopSerializerTest(SerializerTestCase):
    """Тесты для ShopSerializer"""

    def test_shop_serializer(self):
        """Тест сериализации магазина"""
        serializer = ShopSerializer(self.shop)
        data = serializer.data
        self.assertEqual(data['name'], 'Test Shop')
        self.assertTrue(data['state'])


class CategorySerializerTest(SerializerTestCase):
    """Тесты для CategorySerializer"""

    def test_category_serializer(self):
        """Тест сериализации категории"""
        serializer = CategorySerializer(self.category)
        data = serializer.data
        self.assertEqual(data['name'], 'Test Category')


class ProductInfoSerializerTest(SerializerTestCase):
    """Тесты для ProductInfoSerializer"""

    def test_product_info_serializer(self):
        """Тест сериализации информации о товаре"""
        serializer = ProductInfoSerializer(self.product_info)
        data = serializer.data
        self.assertEqual(data['model'], '')
        self.assertEqual(data['quantity'], 100)
        self.assertEqual(float(data['price']), 10.99)


class OrderSerializerTest(SerializerTestCase):
    """Тесты для OrderSerializer"""

    def test_order_serializer(self):
        """Тест сериализации заказа"""
        serializer = OrderSerializer(self.order)
        data = serializer.data
        self.assertEqual(data['status'], 'basket')
        self.assertEqual(len(data['order_items']), 1)


class OrderItemSerializerTest(SerializerTestCase):
    """Тесты для OrderItemSerializer"""

    def test_order_item_serializer(self):
        """Тест сериализации позиции заказа"""
        serializer = OrderItemSerializer(self.order_item)
        data = serializer.data
        self.assertEqual(data['quantity'], 2)
        self.assertEqual(float(data['price']), 10.99)
        self.assertEqual(float(data['total_price']), 21.98)

    def test_order_item_validation_insufficient_quantity(self):
        """Тест валидации позиции заказа при недостаточном количестве товара"""
        # Создаем товар с малым количеством
        product_info_low = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=456,
            quantity=1,
            price=5.99
        )
        data = {
            'product_info': product_info_low,
            'quantity': 10  # Больше доступного
        }
        serializer = OrderItemSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('quantity', serializer.errors)


class APITestCaseBase(APITestCase):
    """Базовый класс для API тестов"""

    def setUp(self):
        """Создание тестовых данных"""
        self.client = APIClient()

        # Создание пользователей
        self.buyer = User.objects.create_user(
            username='buyer',
            email='buyer@example.com',
            password='testpass123',
            type='buyer'
        )
        self.supplier = User.objects.create_user(
            username='supplier',
            email='supplier@example.com',
            password='testpass123',
            type='supplier'
        )

        # Создание магазина для поставщика
        self.shop = Shop.objects.create(
            name='Test Shop',
            user=self.supplier,
            state=True
        )

        # Создание категории и товара
        self.category = Category.objects.create(name='Test Category')
        self.product = Product.objects.create(
            name='Test Product',
            category=self.category
        )
        self.product_info = ProductInfo.objects.create(
            product=self.product,
            shop=self.shop,
            external_id=123,
            quantity=100,
            price=10.99,
            price_rrc=15.99
        )

        # Создание контакта для покупателя
        self.contact = Contact.objects.create(
            user=self.buyer,
            city='Moscow',
            street='Lenin Street',
            house='10',
            phone='+7(999)123-45-67'
        )


class AuthenticationAPITest(APITestCaseBase):
    """Тесты для API аутентификации"""

    def test_user_registration(self):
        """Тест регистрации пользователя"""
        url = reverse('register')
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepass123',
            'password2': 'securepass123',
            'first_name': 'New',
            'last_name': 'User',
            'type': 'buyer'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)

    def test_user_login(self):
        """Тест входа пользователя"""
        url = reverse('login')
        data = {
            'username': 'buyer',
            'password': 'testpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('user', response.data)
        self.assertIn('token', response.data)

    def test_user_logout(self):
        """Тест выхода пользователя"""
        # Сначала входим
        login_url = reverse('login')
        login_data = {
            'username': 'buyer',
            'password': 'testpass123'
        }
        login_response = self.client.post(login_url, login_data, format='json')
        token = login_response.data['token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token}')

        # Теперь выходим
        logout_url = reverse('logout')
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ProfileAndContactsAPITest(APITestCaseBase):
    """Тесты для API профиля пользователя и контактов"""

    def test_get_user_profile(self):
        """Тест получения профиля пользователя"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('profile')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'buyer')

    def test_update_user_profile(self):
        """Тест обновления профиля пользователя"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('profile')
        data = {
            'first_name': 'Updated',
            'last_name': 'Name'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Updated')

    def test_get_contacts(self):
        """Тест получения контактов пользователя"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('contact-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_create_contact(self):
        """Тест создания контакта"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('contact-list')
        data = {
            'city': 'SPb',
            'street': 'Nevsky',
            'house': '1',
            'phone': '+7(999)987-65-43'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['city'], 'SPb')


class ProductRelatedAPITest(APITestCaseBase):
    """Тесты для API связанных с продуктами"""

    def test_get_categories(self):
        """Тест получения категорий"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('category-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_shops(self):
        """Тест получения магазинов"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('shop-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_get_products(self):
        """Тест получения товаров"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('product-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_search_products(self):
        """Тест поиска товаров"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('product-list')
        response = self.client.get(url, {'search': 'Test'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class BasketAPITest(APITestCaseBase):
    """Тесты для API корзины"""

    def test_get_basket(self):
        """Тест получения корзины"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('basket-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_add_to_basket(self):
        """Тест добавления товара в корзину"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('basket-list')
        data = {
            'product_info_id': self.product_info.id,
            'quantity': 2
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_update_basket_item(self):
        """Тест обновления количества товара в корзине"""
        # Сначала добавляем товар в корзину
        self.client.force_authenticate(user=self.buyer)
        basket_url = reverse('basket-list')
        add_data = {
            'product_info_id': self.product_info.id,
            'quantity': 1
        }
        self.client.post(basket_url, add_data, format='json')

        # Теперь обновляем количество
        update_url = reverse('basket-list') + 'update_items/'
        update_data = [{
            'product_info': self.product_info.id,
            'quantity': 3,
            'price': 10.99
        }]
        response = self.client.put(update_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete_from_basket(self):
        """Тест удаления товара из корзины"""
        # Сначала добавляем товар в корзину
        self.client.force_authenticate(user=self.buyer)
        basket_url = reverse('basket-list')
        add_data = {
            'product_info_id': self.product_info.id,
            'quantity': 1
        }
        self.client.post(basket_url, add_data, format='json')

        # Теперь удаляем
        delete_url = reverse('basket-list') + 'delete_items/'
        delete_data = {'items': [self.product_info.id]}
        response = self.client.delete(delete_url, delete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class OrderAPITest(APITestCaseBase):
    """Тесты для API заказов"""

    def test_get_orders(self):
        """Тест получения заказов"""
        self.client.force_authenticate(user=self.buyer)
        url = reverse('order-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_confirm_order(self):
        """Тест подтверждения заказа"""
        # Создаем корзину с товаром
        basket = Order.objects.create(user=self.buyer, status='basket')
        OrderItem.objects.create(
            order=basket,
            product_info=self.product_info,
            quantity=1,
            price=self.product_info.price
        )

        self.client.force_authenticate(user=self.buyer)
        url = reverse('order-detail', kwargs={'pk': basket.id}) + 'confirm/'
        data = {'contact_id': self.contact.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'new')


class SupplierAPITest(APITestCaseBase):
    """Тесты для API поставщика"""

    def test_get_supplier_info(self):
        """Тест получения информации о магазине поставщика"""
        self.client.force_authenticate(user=self.supplier)
        url = reverse('supplier-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Shop')

    def test_update_shop_state(self):
        """Тест обновления статуса приема заказов"""
        self.client.force_authenticate(user=self.supplier)
        url = reverse('supplier-list') + 'update_state/'
        data = {'state': False}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['state'])

    def test_update_price_list(self):
        """Тест загрузки прайс-листа"""
        self.client.force_authenticate(user=self.supplier)
        url = reverse('supplier-list') + 'update_price/'

        # Мокаем requests.get для возврата тестового YAML
        test_yaml = """
shop: Updated Shop
categories:
  - id: 1
    name: Electronics
goods:
  - id: 101
    name: New Product
    category: 1
    quantity: 50
    price: 25.99
    parameters:
      color: black
      size: large
"""
        with patch('requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.content = test_yaml.encode('utf-8')
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response

            data = {'url': 'https://example.com/pricelist.yaml'}
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn('Прайс-лист успешно загружен', response.data['status'])


class PasswordResetAPITest(APITestCaseBase):
    """Тесты для API сброса пароля"""

    def test_password_reset_request(self):
        """Тест запроса на сброс пароля"""
        url = reverse('password-reset')
        data = {'email': 'buyer@example.com'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    @patch('django.core.mail.send_mail')
    def test_password_reset_confirm(self, mock_send_mail):
        """Тест подтверждения сброса пароля"""
        from django.contrib.auth.tokens import PasswordResetTokenGenerator
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes

        # Генерируем токен
        token_generator = PasswordResetTokenGenerator()
        uid = urlsafe_base64_encode(force_bytes(self.buyer.pk))
        token = token_generator.make_token(self.buyer)

        url = reverse('password-reset-confirm', kwargs={'uidb64': uid, 'token': token})
        data = {
            'password': 'newpassword123',
            'password2': 'newpassword123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
