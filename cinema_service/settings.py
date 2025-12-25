# settings.py

INSTALLED_APPS = [
    # ... other apps
    'drf_spectacular',
    'rest_framework_simplejwt',
]

REST_FRAMEWORK = {
    # 1. Documentation Schema
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # 2. JWT Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),

    # 3. Throttling Configuration
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',  # 10 requests per minute for unauthorized
        'user': '30/min',  # 30 requests per minute for authorized
    }
}

# Optional: Spectacular Settings for UI customization
SPECTACULAR_SETTINGS = {
    'TITLE': 'Cinema API Project',
    'DESCRIPTION': 'API for managing cinema movies and sessions',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
