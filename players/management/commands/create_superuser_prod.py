# players/management/commands/create_superuser_prod.py
from django.core.management.base import BaseCommand
from players.models import User

class Command(BaseCommand):
    help = 'スーパーユーザーを作成する'

    def handle(self, *args, **options):
        email = 'nakky19900709@gmail.com'
        if User.objects.filter(email=email).exists():
            user = User.objects.get(email=email)
            user.is_staff = True
            user.is_superuser = True
            user.save()
            self.stdout.write(f'既存ユーザーをスーパーユーザーに昇格: {email}')
        else:
            User.objects.create_superuser(email=email, password='Nakky0804')
            self.stdout.write(f'スーパーユーザー作成完了: {email}')