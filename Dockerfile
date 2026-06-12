FROM python:3.14-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 【変更なし】本番用.envを読み込む
COPY .env.prod .env

# 【変更なし】静的ファイルをまとめる
RUN python manage.py collectstatic --noinput

# 【新規追加】スーパーユーザーを作成する（起動時に実行）
CMD python manage.py create_superuser_prod && \
    python manage.py runserver 0.0.0.0:8000 