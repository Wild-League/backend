import sys
from pathlib import Path
from os import environ, path, getenv
from datetime import timedelta

from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = getenv('SECRET_KEY')

DEBUG = True

APP_NAME = environ.get('FLY_APP_NAME')

ALLOWED_HOSTS = [f"{APP_NAME}.fly.dev", 'localhost', 'api', '127.0.0.1']

FRONT_URL = 'http://localhost:3000/'
DOMAIN = '@wildleague.org'

# SeaweedFS S3-compatible storage
SEAWEED = {
	'S3_ENDPOINT': getenv('SEAWEED_S3_ENDPOINT', 'localhost:8333'),
	'ACCESS_KEY': getenv('SEAWEED_ACCESS_KEY', ''),
	'SECRET_KEY': getenv('SEAWEED_SECRET_KEY', ''),
}

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
	"default": {
		"ENGINE": "django.db.backends.postgresql",
		"NAME": getenv('POSTGRES_DB', 'wildleague'),
		"USER": getenv('POSTGRES_USER', 'postgres'),
		"PASSWORD": getenv('POSTGRES_PASSWORD', ''),
		"HOST": getenv('POSTGRES_HOST', 'localhost'),
		"PORT": getenv('POSTGRES_PORT', '5432'),
	}
}

CSRF_TRUSTED_ORIGINS = ['http://localhost', 'http://127.0.0.1', 'http://api:8000']

CSRF_COOKIE_SECURE = False

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Application definition

INSTALLED_APPS = [
	'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'rest_framework',
	'rest_framework.authtoken',
	'src.api.apps.ApiConfig',
	'corsheaders'
]

CORS_ALLOWED_ORIGINS = ['http://localhost:3000']

MIDDLEWARE = [
	'django.middleware.security.SecurityMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'corsheaders.middleware.CorsMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'src.urls'

REST_FRAMEWORK = {
	"DEFAULT_AUTHENTICATION_CLASSES": (
		# 'rest_framework.authentication.SessionAuthentication',
		# 'rest_framework.authentication.BasicAuthentication',
		'rest_framework_simplejwt.authentication.JWTAuthentication',
	),
	"DEFAULT_PERMISSION_CLASSES": (
		"rest_framework.permissions.IsAuthenticated",
	),
	"NON_FIELD_ERRORS_KEY": "errors"
}

SIMPLE_JWT = {
	'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
	'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
}

TEMPLATES = [
	{
		'BACKEND': 'django.template.backends.django.DjangoTemplates',
		'DIRS': [],
		'APP_DIRS': True,
		'OPTIONS': {
			'context_processors': [
				'django.template.context_processors.debug',
				'django.template.context_processors.request',
				'django.contrib.auth.context_processors.auth',
				'django.contrib.messages.context_processors.messages',
			],
		},
	},
]

WSGI_APPLICATION = 'src.wsgi.application'


# Password validation
# https://docs.djangoproject.com/en/5.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
	{
		'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
	},
	{
		'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
	},
]


# Internationalization
# https://docs.djangoproject.com/en/5.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.0/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'api.Users'

sys.path.append(path.join(BASE_DIR, '../src'))
