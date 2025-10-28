"""Конфигурация приложения retail_procurement."""
from django.apps import AppConfig


class RetailProcurementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'retail_procurement'
    verbose_name = 'Розничные закупки'

    def ready(self):
        """Импорт сигналов при готовности приложения"""
        import retail_procurement.signals
