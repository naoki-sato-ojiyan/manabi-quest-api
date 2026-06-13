from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
import uuid


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('メールアドレスは必須です')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)  # ログインID
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'   # ログインにemailを使う
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class PlayerStatus(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    character_name = models.CharField(max_length=20)
    level = models.IntegerField(default=1)
    hp = models.IntegerField(default=10)
    max_hp = models.IntegerField(default=10)
    exp = models.IntegerField(default=0)
    attack = models.IntegerField(default=5)
    defense = models.IntegerField(default=5)
    agility = models.IntegerField(default=5)
    luck = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.character_name} - Lv.{self.level}'

class RateLimitLog(models.Model):
    ip = models.GenericIPAddressField()
    endpoint = models.CharField(max_length=100)
    requested_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            # IPとエンドポイントと日時で絞り込むクエリを高速化
            models.Index(fields=['ip', 'endpoint', 'requested_at']),
        ]

    def __str__(self):
        return f'{self.ip} - {self.endpoint} - {self.requested_at}'

class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.email} - {self.token}'
    
class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user.email} - {self.token}'