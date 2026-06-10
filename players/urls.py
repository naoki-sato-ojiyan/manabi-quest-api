from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('player/', views.player_status, name='player_status'),
    path('player/create/', views.create_player, name='create_player'),
]