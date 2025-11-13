from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from django.shortcuts import get_object_or_404
from api.models import Team, TeamInvitation, Challenge, UserChallengeAttempt
from accounts.models import User
from rest_framework.response import Response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request, challenge_id):
    """
    Crée une équipe pour un challenge et invite d'autres utilisateurs.
    Body :
    {
        "name": "Team Alpha",
        "invited_user_ids": [2, 3, 4]
    }
    """
    challenge = get_object_or_404(Challenge, id=challenge_id, is_active=True)

    name = request.data.get('name')
    invited_user_ids = request.data.get('invited_user_ids', [])

    if not name:
        return Response({'error': "Le nom de l'équipe est requis."}, status=status.HTTP_400_BAD_REQUEST)

    if len(invited_user_ids) < 1 or len(invited_user_ids) > 5:
        return Response({'error': "Vous devez inviter entre 1 et 5 utilisateurs."}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier que le nom est unique pour ce challenge
    if Team.objects.filter(name=name, challenge=challenge).exists():
        return Response({'error': "Une équipe avec ce nom existe déjà pour ce challenge."}, status=status.HTTP_400_BAD_REQUEST)

    # Créer la team
    team = Team.objects.create(name=name, challenge=challenge, leader=request.user)
    team.members.add(request.user)  # le leader fait partie de la team

    # Créer une tentative de challenge pour le leader
    UserChallengeAttempt.objects.get_or_create(user=request.user, challenge=challenge)

    # Inviter les autres membres
    invited_users = User.objects.filter(id__in=invited_user_ids)
    team.invite_members(request.user, invited_users)

    return Response({
        'success': True,
        'message': f"Équipe '{team.name}' créée avec succès. Invitations envoyées.",
        'team_id': team.id
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
def accept_team_invitation(request, token):
    """
    Accepte une invitation à rejoindre une équipe via un lien reçu par email.
    """
    try:
        invitation = TeamInvitation.objects.get(token=token, is_accepted=False)
    except TeamInvitation.DoesNotExist:
        return Response({'error': "Lien invalide ou déjà utilisé."}, status=status.HTTP_400_BAD_REQUEST)

    invitation.accept()

    return Response({
        'success': True,
        'message': f"Vous avez rejoint l'équipe '{invitation.team.name}' pour le challenge '{invitation.team.challenge.title}'."
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_detail(request, team_id):
    """
    Retourne les détails d'une équipe :
    - infos générales
    - membres
    - challenge associé
    - statut du challenge (en cours ou terminé)
    """
    try:
        team = Team.objects.select_related('challenge', 'leader').prefetch_related('members').get(id=team_id)
    except Team.DoesNotExist:
        return Response({'error': 'Équipe introuvable'}, status=status.HTTP_404_NOT_FOUND)

    members_data = [{
        'id': member.id,
        'username': member.username,
        'email': member.email,
        'photo': request.build_absolute_uri(member.photo.url) if member.photo else None,
        'xp_total': member.total_xp,
    } for member in team.members.all()]

    challenge = team.challenge

    return Response({
        'team': {
            'id': team.id,
            'name': team.name,
            'leader': team.leader.username,
            'is_completed': team.is_completed,
            'created_at': team.created_at,
            'completed_at': team.completed_at,
        },
        'challenge': {
            'id': challenge.id,
            'title': challenge.title,
            'difficulty': challenge.get_difficulty_display(),
            'xp_reward': challenge.xp_reward,
            'participants_count': challenge.participants_count,
        },
        'members': members_data,
        'status': 'Terminé' if team.is_completed else 'En cours'
    }, status=status.HTTP_200_OK)


