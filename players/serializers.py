from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PlayerStatus

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['email', 'password']

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )


class PlayerStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlayerStatus
        fields = [
            'character_name', 'level', 'hp', 'max_hp', 'exp',
            'attack', 'defense', 'agility', 'luck',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']