# submissions/urls.py

from django.urls import path
from .views import (
    ChallengeSubmitView,
    UserChallengeAttemptsView,
    ChallengeLeaderboardView,
    GlobalLeaderboardView,
    UserStatsView
)

app_name = 'submissions'

urlpatterns = [
    # Soumission de challenge (nécessite authentification)
    path('submit/', ChallengeSubmitView.as_view(), name='submit'),
    
    # Tentatives de l'utilisateur
    path('my-attempts/', UserChallengeAttemptsView.as_view(), name='my-attempts'),
    
    # Statistiques de l'utilisateur
    path('my-stats/', UserStatsView.as_view(), name='my-stats'),
    
    # Classement d'un challenge
    path('leaderboard/<int:challenge_id>/', ChallengeLeaderboardView.as_view(), name='challenge-leaderboard'),
    
    # Classement global
    path('leaderboard/', GlobalLeaderboardView.as_view(), name='global-leaderboard'),
]