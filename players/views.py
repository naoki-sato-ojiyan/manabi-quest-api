from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, authenticate
from .models import PlayerStatus
from .serializers import RegisterSerializer, PlayerStatusSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
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