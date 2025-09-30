from django.apps import AppConfig


class RetailProcurementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'retail_procurement'
    verbose_name = 'Розничные закупки'

    def ready(self):
        import retail_procurement.signals
