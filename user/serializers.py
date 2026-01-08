from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from django.utils.translation import gettext as _
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for User model.
    Supports creating and updating users with encrypted passwords.
    """
    class Meta:
        model = get_user_model()
        fields = ("id", "email", "password", "is_staff")
        read_only_fields = ("is_staff",)
        extra_kwargs = {
            "password": {
                "write_only": True,
                "min_length": 5,
                "help_text": "Password (write-only, min 5 characters)"
            },
            "email": {
                "help_text": "User email address (unique)"
            },
        }

    def create(self, validated_data):
        """Create a new user with encrypted password and return it."""
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        """Update a user, set the password correctly and return it."""
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom serializer for obtaining JWT token pair.
    Returns 'access' and 'refresh' tokens.
    Includes user ID and email in token payload.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["email"] = user.email
        token["id"] = user.id
        return token


class AuthTokenSerializer(serializers.Serializer):
    """
    Legacy serializer for token authentication.
    Kept for backward compatibility if needed.
    """
    email = serializers.CharField(
        label=_("Email"), help_text="User email for login"
    )
    password = serializers.CharField(
        label=_("Password"),
        style={"input_type": "password"},
        help_text="User password for login",
    )

    def validate(self, attrs):
        """Validate and authenticate user credentials."""
        email = attrs.get("email")
        password = attrs.get("password")

        if not email or not password:
            msg = _("Must include 'email' and 'password'.")
            raise serializers.ValidationError(msg, code="authorization")

        user = authenticate(email=email, password=password)

        if not user:
            msg = _("Unable to log in with provided credentials.")
            raise serializers.ValidationError(msg, code="authorization")

        if not user.is_active:
            msg = _("User account is disabled.")
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs
