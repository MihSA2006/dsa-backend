from rest_framework.response import Response
from rest_framework import status

from api.models import Challenge
from api.serializers import (
    ChallengeLeaderboardSerializer,
    GlobalLeaderboardSerializer
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.db.models import F, Q, Count, Case, When, IntegerField
from django.contrib.auth import get_user_model
from api.models import UserChallengeAttempt


User = get_user_model()

import logging

# Configuration du logger
logger = logging.getLogger(__name__)


@api_view(['GET'])
def challenge_leaderboard(request, challenge_id):
    """
    Retourne le leaderboard d'un challenge spécifique
    Inclut tous les participants (même ceux qui n'ont pas complété)
    
    GET /api/challenges/{id}/leaderboard/
    """
    
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Récupérer toutes les tentatives pour ce challenge
    attempts = UserChallengeAttempt.objects.filter(
        challenge=challenge
    ).select_related('user').order_by(
        # Tri : completed d'abord, puis XP desc, puis temps asc
        Case(
            When(status='completed', then=0),
            default=1,
            output_field=IntegerField()
        ),
        '-xp_earned',
        'completion_time',
        'started_at'
    )
    
    # Construire les données du leaderboard
    leaderboard_data = []
    rank = 0
    prev_xp = None
    prev_time = None
    
    for idx, attempt in enumerate(attempts, 1):
        # Calculer le rang
        if attempt.status == 'completed':
            if attempt.xp_earned != prev_xp or attempt.completion_time != prev_time:
                rank = idx
                prev_xp = attempt.xp_earned
                prev_time = attempt.completion_time
        else:
            rank = None  # Pas de rang si pas complété
        
        leaderboard_data.append({
            'rank': rank,
            'user_id': attempt.user.id,
            'username': attempt.user.username,
            'nom': attempt.user.nom,
            'prenom': attempt.user.prenom,
            'xp_earned': attempt.xp_earned,
            'completion_time': attempt.completion_time,
            'completed_at': attempt.completed_at,
            'status': attempt.status
        })
    
    serializer = ChallengeLeaderboardSerializer(leaderboard_data, many=True)
    
    return Response({
        'challenge': {
            'id': challenge.id,
            'title': challenge.title,
            'xp_reward': challenge.xp_reward
        },
        'leaderboard': serializer.data
    })


@api_view(['GET'])
def global_leaderboard(request):
    """
    Retourne le leaderboard global de tous les utilisateurs
    Tri par XP total puis par temps de résolution moyen
    
    GET /api/leaderboard/global/
    """
    
    # Récupérer tous les utilisateurs avec leurs stats
    users = User.objects.annotate(
        challenges_completed=Count(
            'challenge_attempts',
            filter=Q(challenge_attempts__status='completed')
        )
    ).filter(
        total_xp__gt=0  # Seulement les utilisateurs avec XP > 0
    ).order_by('-total_xp', 'username')
    
    # Construire les données du leaderboard
    leaderboard_data = []
    rank = 0
    prev_xp = None
    
    for idx, user in enumerate(users, 1):
        if user.total_xp != prev_xp:
            rank = idx
            prev_xp = user.total_xp
        
        leaderboard_data.append({
            'rank': rank,
            'user_id': user.id,
            'username': user.username,
            'nom': user.nom,
            'prenom': user.prenom,
            'total_xp': user.total_xp,
            'challenges_joined': user.challenges_joined,
            'challenges_completed': user.challenges_completed
        })
    
    serializer = GlobalLeaderboardSerializer(leaderboard_data, many=True)
    
    return Response({
        'total_users': len(leaderboard_data),
        'leaderboard': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_stats(request):
    """
    Retourne les statistiques de l'utilisateur connecté
    
    GET /api/my-stats/
    """
    
    user = request.user
    
    # Récupérer les tentatives
    attempts = UserChallengeAttempt.objects.filter(user=user)
    completed = attempts.filter(status='completed')
    
    # Calculer les statistiques
    stats = {
        'user': {
            'id': user.id,
            'username': user.username,
            'nom': user.nom,
            'prenom': user.prenom,
            'total_xp': user.total_xp,
            'challenges_joined': user.challenges_joined,
            'photo': user.photo.url if user.photo else None  # ✅ Changement ici
        },
        'challenges': {
            'joined': attempts.count(),
            'completed': completed.count(),
            'in_progress': attempts.filter(status='in_progress').count(),
            'completion_rate': round(
                (completed.count() / attempts.count() * 100) if attempts.count() > 0 else 0,
                2
            )
        },
        'ranking': {
            'global_rank': User.objects.filter(
                total_xp__gt=user.total_xp
            ).count() + 1,
            'total_users': User.objects.filter(total_xp__gt=0).count()
        }
    }
    
    return Response(stats)