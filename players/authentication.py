from datetime import timedelta
from django.utils import timezone
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class ExpiringTokenAuthentication(TokenAuthentication):
    """30日で期限切れになるトークン認証"""

    def authenticate_credentials(self, key):
        user, token = super().authenticate_credentials(key)
        if timezone.now() > token.created + timedelta(days=30):
            token.delete()
            raise AuthenticationFailed('トークンの有効期限が切れています。再ログインしてください。')
        return user, token