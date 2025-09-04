#!/usr/bin/env python
import os
import sys

if __name__ == '__main__':
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatbot_project.settings')
    
    # Check if runserver command is being used
    if 'runserver' in sys.argv and '--use-wsgi' not in sys.argv:
        # Use ASGI server instead
        print("Starting ASGI server with WebSocket support...")
        try:
            import subprocess
            subprocess.run([
                sys.executable, '-m', 'uvicorn', 
                'chatbot_project.asgi:application',
                '--host', '127.0.0.1',
                '--port', '8000',
                '--reload'
            ])
        except KeyboardInterrupt:
            print("\nServer stopped.")
            sys.exit(0)
    else:
        try:
            from django.core.management import execute_from_command_line
        except ImportError as exc:
            raise ImportError(
                "Couldn't import Django. Are you sure it's installed and "
                "available on your PYTHONPATH environment variable? Did you "
                "forget to activate a virtual environment?"
            ) from exc
        execute_from_command_line(sys.argv)