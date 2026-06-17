from django.apps import AppConfig


class TicketsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tickets"

    def ready(self):
        import os
        # Only start the scheduler in the main process, not the reloader subprocess
        if os.environ.get("RUN_MAIN") != "true":
            return
        from .scheduler import start
        start()
