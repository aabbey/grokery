from django.apps import AppConfig
import asyncio
import signal
import sys


class AppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "app"

    def ready(self):
        from app.services.recipe_service import RecipeService

        async def cleanup():
            await RecipeService.cleanup()

        def sync_cleanup():
            loop = asyncio.new_event_loop()
            loop.run_until_complete(cleanup())
            loop.close()

        def signal_handler(signum, frame):
            sync_cleanup()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
