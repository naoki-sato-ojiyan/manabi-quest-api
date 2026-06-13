from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import PlayerStatus, RateLimitLog, EmailVerificationToken
from .serializers import RegisterSerializer, PlayerStatusSerializer

User = get_user_model()


# レート制限チェックとログ記録
def check_rate_limit(ip, endpoint, max_requests, period_minutes):
    """指定期間内のリクエスト数が上限を超えていたらTrueを返す"""
    since = timezone.now() - timedelta(minutes=period_minutes)
    count = RateLimitLog.objects.filter(
        ip=ip,
        endpoint=endpoint,
        requested_at__gte=since
    ).count()
    if count >= max_requests:
        return True
    RateLimitLog.objects.create(ip=ip, endpoint=endpoint)
    return False


# CloudFront経由でも正しいIPを取得する
def get_client_ip(request):
    """リクエスト元のIPアドレスを取得する"""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    ip = get_client_ip(request)
    if check_rate_limit(ip, 'register', max_requests=3, period_minutes=60):
        return Response(
            {'error': 'リクエストが多すぎます。しばらく待ってから再試行してください。'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        # 変更：登録時はis_active=Falseにしてメール認証待ちにする
        user = serializer.save(is_active=False)
        verification = EmailVerificationToken.objects.create(user=user)
        verify_url = f"{settings.API_BASE_URL}/api/verify-email/?token={verification.token}"
        send_mail(
            subject='【まなびクエスト】メールアドレスの確認',
            message=f'以下のリンクをクリックしてメールアドレスを確認してください。\n\n{verify_url}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
        )
        return Response(
            {'message': '確認メールを送信しました。メールをご確認ください。'},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    ip = get_client_ip(request)
    if check_rate_limit(ip, 'login', max_requests=10, period_minutes=15):
        return Response(
            {'error': 'リクエストが多すぎます。しばらく待ってから再試行してください。'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    email = request.data.get('email')
    password = request.data.get('password')
    user = authenticate(request, username=email, password=password)
    if user:
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)
        return Response({
            'token': token.key,
            'email': user.email
        })
    # 変更：メール未認証の場合は専用メッセージを返す
    try:
        unverified = User.objects.get(email=email)
        if not unverified.is_active:
            return Response(
                {'error': 'メール認証が完了していません。届いたメールのリンクをクリックしてください。'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    except User.DoesNotExist:
        pass
    return Response({'error': 'メールアドレスまたはパスワードが違います'},
                    status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def player_status(request):
    try:
        player = PlayerStatus.objects.get(user=request.user)
    except PlayerStatus.DoesNotExist:
        return Response({'error': 'プレイヤーが存在しません'},
                        status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = PlayerStatusSerializer(player)
        return Response(serializer.data)

    if request.method == 'PUT':
        serializer = PlayerStatusSerializer(player, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_player(request):
    if PlayerStatus.objects.filter(user=request.user).exists():
        return Response({'error': 'プレイヤーは既に存在します'},
                        status=status.HTTP_400_BAD_REQUEST)
    serializer = PlayerStatusSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 追加：メール認証リンクをクリックしたときの処理
@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request):
    token = request.query_params.get('token')
    if not token:
        return Response({'error': 'トークンがありません'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        verification = EmailVerificationToken.objects.get(token=token)
    except EmailVerificationToken.DoesNotExist:
        return Response({'error': '無効なトークンです'},
                        status=status.HTTP_400_BAD_REQUEST)
    user = verification.user
    user.is_active = True
    user.save()
    verification.delete()
    Token.objects.get_or_create(user=user)
    return Response({'message': 'メールアドレスの確認が完了しました。ログインしてください。'})

# 追加：パスワードリセットメール送信
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset(request):
    email = request.data.get('email')
    if not email:
        return Response({'error': 'メールアドレスを入力してください'},
                        status=status.HTTP_400_BAD_REQUEST)
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        # 存在しないメールアドレスでも同じメッセージを返す（ユーザー列挙攻撃対策）
        return Response({'message': 'パスワードリセットメールを送信しました。メールをご確認ください。'})

    from .models import PasswordResetToken
    reset_token = PasswordResetToken.objects.create(user=user)
    reset_url = f"{settings.FRONTEND_URL}/?reset_token={reset_token.token}"
    send_mail(
        subject='【まなびクエスト】パスワードリセット',
        message=f'以下のリンクからパスワードを再設定してください。\n\n{reset_url}\n\nこのリンクは1時間有効です。',
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return Response({'message': 'パスワードリセットメールを送信しました。メールをご確認ください。'})


# 追加：パスワードリセット実行
@api_view(['POST'])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    token = request.data.get('token')
    new_password = request.data.get('password')
    if not token or not new_password:
        return Response({'error': 'トークンとパスワードは必須です'},
                        status=status.HTTP_400_BAD_REQUEST)

    from .models import PasswordResetToken
    try:
        reset_token = PasswordResetToken.objects.get(token=token, is_used=False)
    except PasswordResetToken.DoesNotExist:
        return Response({'error': '無効なトークンです'},
                        status=status.HTTP_400_BAD_REQUEST)

    # 1時間以上経過したトークンは無効
    if timezone.now() - reset_token.created_at > timedelta(hours=1):
        return Response({'error': 'トークンの有効期限が切れています。再度申請してください。'},
                        status=status.HTTP_400_BAD_REQUEST)

    user = reset_token.user
    user.set_password(new_password)
    user.save()
    reset_token.is_used = True
    reset_token.save()
    return Response({'message': 'パスワードを変更しました。ログインしてください。'})