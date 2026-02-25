"""
ASGI config for api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

if "DJANGO_SETTINGS_MODULE" not in os.environ:
	os.environ["DJANGO_SETTINGS_MODULE"] = (
		"src.config.prod_settings" if os.environ.get("ENV") == "production" else "src.config.dev_settings"
	)

application = get_asgi_application()
