# players/management/commands/create_superuser_prod.py
from django.core.management.base import BaseCommand
from players.models import User
import os

class Command(BaseCommand):
    help = 'スーパーユーザーを作成する'

    def handle(self, *args, **options):
        email = os.environ.get('SUPERUSER_EMAIL')
        if not email:
            self.stdout.write('SUPERUSER_EMAILが設定されていません。スキップします。')
            return

        password = os.environ.get('SUPERUSER_PASSWORD')
        if not password:
            self.stdout.write('SUPERUSER_PASSWORDが設定されていません。スキップします。')
            return

        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(f'既存ユーザーをスーパーユーザーに昇格: {email}')
        else:
            User.objects.create_superuser(email=email, password=password)
            self.stdout.write(f'スーパーユーザー作成完了: {email}')