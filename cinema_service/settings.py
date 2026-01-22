INSTALLED_APPS = [
    # ... other apps
    'drf_spectacular',
]

REST_FRAMEWORK = {
    # Documentation
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    
    # Authentication
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    
    # Throttling
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '10/min',  # 10 requests per minute for unauthorized
        'user': '30/min',  # 30 requests per minute for authorized
    }
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Cinema API',
    'DESCRIPTION': 'Ordering tickets for movie sessions',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}
