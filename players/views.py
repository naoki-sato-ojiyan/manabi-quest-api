from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from django.utils import timezone
from datetime import timedelta
from .models import PlayerStatus, RateLimitLog
from .serializers import RegisterSerializer, PlayerStatusSerializer

User = get_user_model()


# 追加：レート制限チェックとログ記録
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


# 追加：CloudFront経由でも正しいIPを取得する
def get_client_ip(request):
    """リクエスト元のIPアドレスを取得する"""
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    # 追加：1時間3回までに制限
    ip = get_client_ip(request)
    if check_rate_limit(ip, 'register', max_requests=3, period_minutes=60):
        return Response(
            {'error': 'リクエストが多すぎます。しばらく待ってから再試行してください。'},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'email': user.email
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    # 追加：15分10回までに制限
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
        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'email': user.email
        })
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