"""Обработчики сигналов для приложения retail_procurement."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order
import logging

logger = logging.getLogger(__name__) 

@receiver(post_save, sender=Order)
def order_status_changed(sender, instance, created, **kwargs):
    """
    Сигнал для отправки уведомлений при изменении статуса заказа
    """
    if created:
        return
    
    # Отправляем уведомление клиенту при изменении статуса
    if instance.status != 'basket':
        status_messages = {
            'new': 'принят в обработку',
            'confirmed': 'подтвержден',
            'assembled': 'собран',
            'sent': 'отправлен',
            'delivered': 'доставлен',
            'canceled': 'отменен',
        }
        
        status_text = status_messages.get(instance.status, instance.status)
        
        subject = f'Изменение статуса заказа №{instance.id}'
        message = f'''
        Здравствуйте, {instance.user.first_name or instance.user.username}!

        Статус вашего заказа №{instance.id} изменен на: {status_text}
        
        Общая сумма: {instance.total_sum} руб.
        '''
        
        if instance.contact:
            message += f'\nАдрес доставки: {instance.contact}'
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.user.email],
                fail_silently=False,  # Изменено на False для явного перехвата ошибок
            )
            logger.info(f"Email отправлен пользователю {instance.user.email} о заказе #{instance.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки email для заказа #{instance.id}: {str(e)}")
