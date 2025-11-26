"""Модели базы данных для системы розничных закупок."""
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.utils.translation import gettext_lazy as _


USER_TYPE_CHOICES = (
    ('buyer', 'Покупатель'),
    ('supplier', 'Поставщик'),
)

ORDER_STATUS_CHOICES = (
    ('basket', 'Корзина'),
    ('new', 'Новый'),
    ('confirmed', 'Подтвержден'),
    ('assembled', 'Собран'),
    ('sent', 'Отправлен'),
    ('delivered', 'Доставлен'),
    ('canceled', 'Отменен'),
)


class User(AbstractUser):
    """
    Кастомная модель пользователя
    """
    username_validator = UnicodeUsernameValidator()

    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        validators=[username_validator],
        error_messages={
            'unique': _("A user with that username already exists."),
        },
    )
    email = models.EmailField(_('email address'), unique=True)
    company = models.CharField(max_length=100, blank=True, verbose_name='Компания')
    position = models.CharField(max_length=100, blank=True, verbose_name='Должность')
    type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='buyer', verbose_name='Тип пользователя')
    
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name=('groups'),
        blank=True,
        related_name="retail_procurement_user_set",
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name=('user permissions'),
        blank=True,
        related_name="retail_procurement_user_permissions_set",
        related_query_name="user",
    )

    REQUIRED_FIELDS = ['email']

    avatar = models.URLField(blank=True, null=True, verbose_name='Аватар')  # Для фото из соц. сети
    def save(self, *args, **kwargs):
        # Логика для обновления avatar из соц. данных
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['id']

    def __str__(self):
        """Строковое представление пользователя"""
        return f'{self.username} ({self.get_type_display()})'


class Shop(models.Model):
    """
    Магазин/Поставщик
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    url = models.URLField(blank=True, null=True, verbose_name='Ссылка')
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='shop', verbose_name='Пользователь')
    state = models.BooleanField(default=True, verbose_name='Статус приема заказов')

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = 'Магазины'
        ordering = ['name']

    def __str__(self):
        """Строковое представление магазина"""
        return self.name


class Category(models.Model):
    """
    Категория товаров
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    shops = models.ManyToManyField(Shop, related_name='categories', blank=True, verbose_name='Магазины')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        """Строковое представление категории"""
        return self.name


class Product(models.Model):
    """
    Товар
    """
    name = models.CharField(max_length=200, verbose_name='Название')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категория')
    description = models.TextField(blank=True, verbose_name='Описание')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['name']

    def __str__(self):
        """Строковое представление товара"""
        return self.name


class ProductInfo(models.Model):
    """
    Информация о товаре от поставщика
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_infos', verbose_name='Товар')
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, related_name='product_infos', verbose_name='Магазин')
    external_id = models.PositiveIntegerField(verbose_name='Внешний ID')
    model = models.CharField(max_length=100, blank=True, verbose_name='Модель')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    price_rrc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Рекомендуемая розничная цена', default=0.0 )

    class Meta:
        verbose_name = 'Информация о товаре'
        verbose_name_plural = 'Информация о товарах'
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info'),
        ]

    def __str__(self):
        """Строковое представление информации о товаре"""
        return f'{self.product.name} ({self.shop.name})'


class Parameter(models.Model):
    """
    Параметр/Характеристика товара
    """
    name = models.CharField(max_length=100, verbose_name='Название')

    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = 'Параметры'
        ordering = ['name']

    def __str__(self):
        """Строковое представление параметра"""
        return self.name


class ProductParameter(models.Model):
    """
    Значение параметра товара
    """
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='product_parameters', verbose_name='Информация о товаре')
    parameter = models.ForeignKey(Parameter, on_delete=models.CASCADE, related_name='product_parameters', verbose_name='Параметр')
    value = models.CharField(max_length=200, verbose_name='Значение')

    class Meta:
        verbose_name = 'Параметр товара'
        verbose_name_plural = 'Параметры товаров'
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]

    def __str__(self):
        """Строковое представление параметра товара"""
        return f'{self.parameter.name}: {self.value}'


class Contact(models.Model):
    """
    Контактная информация / Адрес доставки
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contacts', verbose_name='Пользователь')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя') # Добавлено
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия') # Добавлено
    patronymic = models.CharField(max_length=100, blank=True, verbose_name='Отчество') # Добавлено
    email = models.EmailField(blank=True, verbose_name='Email для контакта') # Добавлено
    city = models.CharField(max_length=100, verbose_name='Город')
    street = models.CharField(max_length=200, verbose_name='Улица')
    house = models.CharField(max_length=20, verbose_name='Дом')
    structure = models.CharField(max_length=20, blank=True, verbose_name='Корпус')
    building = models.CharField(max_length=20, blank=True, verbose_name='Строение')
    apartment = models.CharField(max_length=20, blank=True, verbose_name='Квартира')
    phone = models.CharField(max_length=20, verbose_name='Телефон')

    class Meta:
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'

    def __str__(self):
        """Строковое представление контакта"""
        return f'{self.city}, {self.street} {self.house} ({self.first_name} {self.last_name})'


class Order(models.Model):
    """
    Заказ
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders', verbose_name='Пользователь')
    dt = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='basket', verbose_name='Статус')
    contact = models.ForeignKey(Contact, on_delete=models.CASCADE, blank=True, null=True, related_name='orders', verbose_name='Контакт')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-dt']

    def __str__(self):
        """Строковое представление заказа"""
        return f'Заказ №{self.id} от {self.dt.strftime("%d.%m.%Y")}'

    @property
    def total_sum(self):
        """Общая сумма заказа"""
        return sum(item.quantity * item.price for item in self.order_items.all())


class OrderItem(models.Model):
    """
    Позиция в заказе
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items', verbose_name='Заказ')
    product_info = models.ForeignKey(ProductInfo, on_delete=models.CASCADE, related_name='order_items', verbose_name='Информация о товаре')
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказов'
        constraints = [
            models.UniqueConstraint(fields=['order', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        """Строковое представление позиции заказа"""
        return f'{self.product_info.product.name} x {self.quantity}'

    @property
    def total_price(self):
        """Стоимость позиции"""
        if self.quantity is not None and self.price is not None:
            return self.quantity * self.price
        return 0
