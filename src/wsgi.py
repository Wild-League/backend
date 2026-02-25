"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

if "DJANGO_SETTINGS_MODULE" not in os.environ:
	os.environ["DJANGO_SETTINGS_MODULE"] = (
		"src.config.prod_settings" if os.environ.get("ENV") == "production" else "src.config.dev_settings"
	)

application = get_wsgi_application()
