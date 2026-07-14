from __future__ import annotations

from typing import Any

from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from apps.accounts.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name"]
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def validate_password(self, value: str) -> str:
        validate_password(value)
        return value

    def create(self, validated_data: dict[str, str]) -> User:
        email = validated_data["email"]
        return User.objects.create_user(
            username=email,
            email=email,
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()


class VerifyEmailSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()
    code = serializers.CharField(min_length=6, max_length=6, trim_whitespace=True)

    def validate_email(self, value: str) -> str:
        return value.strip().lower()

    def validate_code(self, value: str) -> str:
        if not value.isdigit():
            raise serializers.ValidationError("Enter the 6-digit verification code.")
        return value


class ResendVerificationSerializer(serializers.Serializer[Any]):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        return value.strip().lower()
