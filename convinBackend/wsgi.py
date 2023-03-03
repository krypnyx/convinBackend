"""
WSGI config for convinBackend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/howto/deployment/wsgi/
"""

import os
import sys
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'convinBackend.settings')
os.environ.setdefault('OAUTHLIB_INSECURE_TRANSPORT', '1')
application = get_wsgi_application()
