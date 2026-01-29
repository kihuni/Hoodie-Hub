from django.apps import AppConfig


class HoodiehubConfig(AppConfig):
    name = 'hoodieHub'
    
    def ready(self):
        import hoodieHub.signals
