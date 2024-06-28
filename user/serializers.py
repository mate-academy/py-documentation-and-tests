from django.contrib.auth import get_user_model, authenticate
from rest_framework import serializers
from django.utils.translation import gettext as _

from user.models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model.
    Handles the creation and updating of user instances.
    """

    class Meta:
        model = get_user_model()
        fields = ("id", "email", "password", "is_staff")
        read_only_fields = ("is_staff",)
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def create(self, validated_data: dict) -> User:
        """
        Create a new user with an encrypted password and return it.
        Args:
            validated_data (dict): The validated data from the request.
        Returns:
            User: The created user instance.
        """
        return get_user_model().objects.create_user(**validated_data)

    def update(self, instance: User, validated_data: dict) -> User:
        """
        Update an existing user, set the password correctly, and return it.
        Args:
            instance (User): The user instance to update.
            validated_data (dict): The validated data from the request.

        Returns:
            User: The updated user instance.
        """
        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user


class AuthTokenSerializer(serializers.Serializer):
    """
    Serializer for authenticating a user with email and password.
    """

    email = serializers.CharField(label=_("Email"))
    password = serializers.CharField(
        label=_("Password"), style={"input_type": "password"}
    )

    def validate(self, attrs: dict) -> dict:
        """
        Validate and authenticate the user with the provided email
        and password.
        Args:
            attrs (dict): The attributes containing email and password.
        Returns:
            dict: Validated attributes with the authenticated user.
        Raises:
            serializers.ValidationError: If authentication fails
            or the user is inactive.
        """
        email = attrs.get("email")
        password = attrs.get("password")

        if email and password:
            user = authenticate(email=email, password=password)

            if user:
                if not user.is_active:
                    msg = _("User account is disabled.")
                    raise serializers.ValidationError(
                        msg, code="authorization"
                    )
            else:
                msg = _("Unable to log in with provided credentials.")
                raise serializers.ValidationError(msg, code="authorization")
        else:
            msg = _("Must include 'username' and 'password'.")
            raise serializers.ValidationError(msg, code="authorization")

        attrs["user"] = user
        return attrs
