import os
import django
from django.core.asgi import get_asgi_application

# Set the Django settings module FIRST
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')

# Setup Django BEFORE importing anything else
django.setup()

# Now we can safely import channels and our routing
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import chatbot.routing

# Get the Django ASGI application
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AuthMiddlewareStack(
        URLRouter(
            chatbot.routing.websocket_urlpatterns
        )
    ),
})