from django.apps import AppConfig


class TicketsConfig(AppConfig):
    name = "tickets"

    def ready(self):
        import os
        if os.environ.get("RUN_MAIN") != "true":
            return
        from .scheduler import start
        start()
