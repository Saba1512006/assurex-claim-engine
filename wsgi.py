"""WSGI entry point: `gunicorn wsgi:app` (Render/Heroku) or `application` (PythonAnywhere)."""
from src.app import create_app

app = application = create_app()
