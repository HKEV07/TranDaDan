from rest_framework import serializers
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.utils.crypto import get_random_string
from django.contrib.auth import get_user_model
from django.core.validators import EmailValidator
from .utils import get_free_game_nickname

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    password_confirmation = serializers.CharField(write_only=True, style={'input_type': 'password'})
    email = serializers.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirmation']

    def validate(self, data):
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError({"password_confirmation": "Passwords must match."})

        try:
            password_validation.validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({"password": e.messages})

        if User.objects.filter(email=data['email']).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})

        if User.objects.filter(email=data['username']).exists():
            raise serializers.ValidationError({"username": "A user with this username already exists."})
        return data

    def create(self, validated_data):
        validated_data.pop('password_confirmation', None)
        if validated_data['username'] and isinstance(validated_data['username'], str):
            validated_data['username'] = validated_data['username'].lower()
        user = User(
            username=validated_data['username'],
            email=validated_data['email']
        )
        user.set_password(validated_data['password'])
        user.email_token = get_random_string(32)
        user.tournament_alias = get_free_game_nickname(user.username)
        user.save()

        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    def validate(self, data):
        email = data["email"]
        user = User.objects.filter(email=email).first()
        if user:
            if not user.email_verified:
                raise serializers.ValidationError({"email": "Verify your email before logging in."})
        return data

class RequestResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        validator = EmailValidator()
        try:
            validator(value)
        except ValidationError:
            raise serializers.ValidationError({"email": "Invalid email address."})
        return value

class ResetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirmation = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        if data['password'] != data['password_confirmation']:
            raise serializers.ValidationError({"password_confirmation": "Password and confirmation do not match."})
        return data

class UserUpdateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    password_confirmation = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirmation', 'tournament_alias']

    def validate(self, data):
        password = data.get('password')
        password_confirmation = data.get('password_confirmation')
        if password and password != password_confirmation:
            raise serializers.ValidationError("Password and password confirmation do not match.")
        if password:
            try:
                password_validation.validate_password(password)
            except ValidationError as e:
                raise serializers.ValidationError(e.messages)
        return data

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            instance.set_password(password)
        return super().update(instance, validated_data)

class UserSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'avatar_url']
