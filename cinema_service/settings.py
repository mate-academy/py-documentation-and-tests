# cinema_service/settings.py

from pathlib import Path

# ... (código existente)

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
    "rest_framework.authtoken", # Manter por enquanto se outras partes dependerem, mas JWT é o foco
    "rest_framework_simplejwt", # NOVO PARA JWT
    "drf_spectacular", # NOVO PARA SWAGGER
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

# ... (resto do TEMPLATES)

WSGI_APPLICATION = "cinema_service.wsgi.application"

# ... (resto do DATABASES)

AUTH_USER_MODEL = "user.User"

# ... (resto das configurações de i18n)

# Configuração JWT
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=5),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=1),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# Configuração DRF (incluindo Throttling e JWT)
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication", # JWT como padrão
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [ # CONFIGURAÇÃO DE THROTTLING
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": { # CONFIGURAÇÃO DE THROTTLING
        'anon': '10/min',
        'user': '30/min',
    },
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema", # SWAGGER
}


# ... (resto das configurações de static files)