from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import logging
from .models import User

logger = logging.getLogger(__name__)

@shared_task
def send_order_status_email(order_id):
    """Отправка email при изменении статуса заказа"""
    try:
        order = Order.objects.get(id=order_id)
        status_messages = {
            'new': 'принят в обработку',
            'confirmed': 'подтвержден',
            'assembled': 'собран',
            'sent': 'отправлен',
            'delivered': 'доставлен',
            'canceled': 'отменен',
        }

        status_text = status_messages.get(order.status, order.status)

        subject = f'Изменение статуса заказа №{order.id}'
        message = f'''
        Здравствуйте, {order.user.first_name or order.user.username}!

        Статус вашего заказа №{order.id} изменен на: {status_text}

        Общая сумма: {order.total_sum} руб.
        '''

        if order.contact:
            message += f'\nАдрес доставки: {order.contact}'

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=False,
        )
    except Order.DoesNotExist:
        logger.warning(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Error sending email for order {order_id}: {e}")


@shared_task
def send_order_confirmation_email(order_id):
    """Отправка подтверждения заказа клиенту"""
    try:
        order = Order.objects.select_related('user', 'contact').prefetch_related('order_items__product_info__product').get(id=order_id)
        order_items = order.order_items.all()
        subject = f'Заказ №{order.id} принят'
        message = f'''
        Здравствуйте, {order.user.first_name or order.user.username}!

        Ваш заказ №{order.id} успешно оформлен.

        Товары:
        '''
        for item in order_items:
            message += f'\n- {item.product_info.product.name} x {item.quantity} = {item.total_price} руб.'

        message += f'\n\nОбщая сумма: {order.total_sum} руб.'
        if order.contact:
            message += f'\n\nАдрес доставки: {order.contact}'

        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [order.user.email],
            fail_silently=True,
        )
    except Order.DoesNotExist:
        logger.warning(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Error sending email for order {order_id}: {e}")

@shared_task
def send_order_notification_to_suppliers(order_id):
    """Отправка уведомления о заказе поставщикам"""
    try:
        order = Order.objects.select_related('user', 'contact').prefetch_related('order_items__product_info__shop', 'order_items__product_info__product').get(id=order_id)
        order_items = order.order_items.all()

        shops = set()
        for item in order_items:
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
            if order.contact:
                message += f'\nАдрес доставки: {order.contact}'

            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [shop.user.email],
                fail_silently=True,
            )
    except Order.DoesNotExist:
        logger.warning(f"Order {order_id} not found")
    except Exception as e:
        logger.error(f"Error sending email for order {order_id}: {e}")


@shared_task
def process_avatar(user_id):
    user = User.objects.get(id=user_id)
    # Генерация миниатюр
    user.avatar.create_versatileimagefield('thumbnail', size=(100, 100))
    user.avatar.create_versatileimagefield('medium', size=(300, 300))
    user.save()