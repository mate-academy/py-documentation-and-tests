# cinema_service/settings.py

from pathlib import Path

# ... (código existente até BASE_DIR)
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = (
    "django-insecure-6vubhk2$++agnctay_4pxy_8cq)mosmn(*-#2b^v4cgsh-^!i3"
) # <--- GARANTA QUE ESTA LINHA ESTÁ AQUI

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

INTERNAL_IPS = [
    "127.0.0.1",
]

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt", # NOVO
    "drf_spectacular", # NOVO
    "debug_toolbar",
    "cinema",
    "user",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "cinema_service.urls"

TEMPLATES = [
    # ... (manter a estrutura de TEMPLATES)
]

WSGI_APPLICATION = "cinema_service.wsgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
} # <--- GARANTA QUE ESTA SEÇÃO ESTÁ AQUI


# Password validation
# ... (manter a estrutura de AUTH_PASSWORD_VALIDATORS)

AUTH_USER_MODEL = "user.User"

# Internationalization
# ... (manter a estrutura de i18n)

USE_TZ = False # <-- VERIFIQUE SE ESTÁ COMO VOCÊ RECEBEU OU SE MUDOU PARA TRUE/FALSE

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media" # <--- GARANTA QUE ESTA LINHA ESTÁ AQUI

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Configuração DRF (incluindo Throttling e JWT/Swagger)
from datetime import timedelta

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        'anon': '10/min',
        'user': '30/min',
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY, # Agora SECRET_KEY está definido
    "AUTH_HEADER_TYPES": ("Bearer",),
}
