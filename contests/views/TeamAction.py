from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
import logging
from accounts.serializers import UserSerializer
from contests.models import Team
from contests.serializers import (
    TeamDetailSerializer,
    TeamCreateSerializer,
    TeamInvitationSerializer
)
from django.utils import timezone

from contests.models import Contest

logger = logging.getLogger(__name__)

from contests.utils import send_team_invitation_email
from contests.models import TeamInvitation

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_team(request):
    """
    POST /api/teams/create/
    Crée une nouvelle équipe pour un contest
    
    Body: {
        "contest": 1,
        "nom": "Nom de l'équipe"
    }
    """
    serializer = TeamCreateSerializer(data=request.data, context={'request': request})
    
    if serializer.is_valid():
        try:
            team = serializer.save()
            return Response(
                TeamDetailSerializer(team, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_team(request, team_id):
    """
    DELETE /api/teams/{team_id}/delete/
    Supprime une équipe d'un contest
    
    Restrictions:
    - Seul le capitaine peut supprimer l'équipe
    - Impossible de supprimer après le début du contest
    - Toutes les invitations en attente seront annulées
    """
    team = get_object_or_404(Team, pk=team_id)
    
    # Vérifier que le requester est le capitaine
    if team.capitaine != request.user:
        return Response(
            {'error': 'Seul le capitaine peut supprimer l\'équipe'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que le contest n'a pas commencé
    if team.contest.has_started():
        return Response(
            {
                'error': 'Impossible de supprimer l\'équipe après le début du contest',
                'contest_status': team.contest.statut,
                'contest_start': team.contest.date_debut
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Sauvegarder les informations avant suppression
    team_info = {
        'id': team.id,
        'name': team.nom,
        'contest': team.contest.title,
        'contest_id': team.contest.id,
        'members_count': team.membres.count(),
        'xp_total': team.xp_total
    }
    
    # Compter les invitations en attente
    pending_invitations = TeamInvitation.objects.filter(
        team=team,
        status='pending'
    )
    pending_count = pending_invitations.count()
    
    try:
        # Annuler toutes les invitations en attente
        if pending_count > 0:
            pending_invitations.update(
                status='expired',
                responded_at=timezone.now()
            )
        
        # Supprimer l'équipe (cela supprimera aussi les soumissions via CASCADE)
        team.delete()
        
        return Response({
            'success': True,
            'message': f'L\'équipe "{team_info["name"]}" a été supprimée avec succès',
            'deleted_team': team_info,
            'cancelled_invitations': pending_count
        }, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Erreur lors de la suppression de l'équipe {team_id}: {str(e)}")
        return Response(
            {'error': 'Une erreur est survenue lors de la suppression de l\'équipe'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_member(request, team_id):
    """
    POST /api/teams/{team_id}/invite/
    Envoie une ou plusieurs invitations à des membres pour rejoindre l'équipe
    
    Body: {
        "user_email": "user@example.com"
    }
    ou 
    Body: {
        "emails": ["user1@example.com", "user2@example.com"]
    }
    """
    team = get_object_or_404(Team, pk=team_id)
    
    # Vérifier que le requester est le capitaine
    if team.capitaine != request.user:
        return Response(
            {'error': 'Seul le capitaine peut inviter des membres'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer les emails (soit un seul, soit une liste)
    emails = request.data.get('emails')
    single_email = request.data.get('user_email')
    
    if not emails and not single_email:
        return Response(
            {'error': 'user_email ou emails est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if single_email and not emails:
        emails = [single_email]
    elif not isinstance(emails, list):
        return Response(
            {'error': 'Le champ emails doit être une liste'},
            status=status.HTTP_400_BAD_REQUEST
        )

    from accounts.models import User
    results = []
    
    for email in emails:
        # Validation basique
        if '@' not in email:
            results.append({'email': email, 'status': 'error', 'message': 'Format d\'email invalide'})
            continue
            
        try:
            user = User.objects.get(email=email)
            
            # Vérifications
            if user == request.user:
                results.append({'email': email, 'status': 'error', 'message': 'Auto-invitation interdite'})
                continue
                
            can_add, message = team.can_add_member(user)
            if not can_add:
                results.append({'email': email, 'status': 'error', 'message': message})
                continue
                
            existing = TeamInvitation.objects.filter(team=team, invitee=user, status='pending').first()
            if existing and existing.is_valid():
                results.append({'email': email, 'status': 'error', 'message': 'Invitation déjà en attente'})
                continue
            
            # Création
            invitation = TeamInvitation.objects.create(team=team, inviter=request.user, invitee=user)
            results.append({
                'email': email, 
                'status': 'success', 
                'username': user.username,
                'invitation': TeamInvitationSerializer(invitation).data
            })
            
        except User.DoesNotExist:
            results.append({'email': email, 'status': 'error', 'message': 'Utilisateur non trouvé'})
            
    return Response({
        'team_id': team.id,
        'team_name': team.nom,
        'results': results
    }, status=status.HTTP_200_OK)


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])  # Pas besoin d'authentification
def accept_invitation(request, token):
    """
    POST ou GET /api/invitations/accept/{token}/
    Accepte une invitation à rejoindre une équipe
    Le token sert de preuve d'identité, pas besoin d'être authentifié
    """
    invitation = get_object_or_404(TeamInvitation, token=token)
    
    # Vérifier que l'invitation est toujours valide
    if not invitation.is_valid():
        if invitation.status == 'accepted':
            message = f'Cette invitation a déjà été acceptée le {invitation.responded_at.strftime("%d/%m/%Y à %H:%M")}'
        elif invitation.status == 'declined':
            message = 'Cette invitation a été refusée'
        elif invitation.status == 'expired':
            message = 'Cette invitation a expiré'
        else:
            message = 'Cette invitation n\'est plus valide'
        
        return Response({
            'success': False,
            'error': message,
            'status': invitation.status
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        invitation.accept()
        
        return Response({
            'success': True,
            'message': f'Félicitations ! Vous avez rejoint l\'équipe {invitation.team.nom}',
            'team': {
                'id': invitation.team.id,
                'nom': invitation.team.nom,
                'contest': invitation.team.contest.title,
                'capitaine': invitation.team.capitaine.username,
                'nombre_membres': invitation.team.membres.count()
            }
        }, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST', 'GET'])
@permission_classes([AllowAny])  # Pas besoin d'authentification
def decline_invitation(request, token):
    """
    POST ou GET /api/invitations/decline/{token}/
    Refuse une invitation à rejoindre une équipe
    Le token sert de preuve d'identité, pas besoin d'être authentifié
    """
    invitation = get_object_or_404(TeamInvitation, token=token)
    
    # Vérifier que l'invitation n'a pas déjà été traitée
    if invitation.status != 'pending':
        if invitation.status == 'accepted':
            message = f'Cette invitation a déjà été acceptée le {invitation.responded_at.strftime("%d/%m/%Y à %H:%M")}'
        elif invitation.status == 'declined':
            message = 'Cette invitation a déjà été refusée'
        else:
            message = 'Cette invitation n\'est plus disponible'
        
        return Response({
            'success': False,
            'error': message,
            'status': invitation.status
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        invitation.decline()
        
        return Response({
            'success': True,
            'message': f'Vous avez refusé l\'invitation à rejoindre l\'équipe {invitation.team.nom}'
        }, status=status.HTTP_200_OK)
        
    except ValidationError as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_invitations(request):
    """
    GET /api/invitations/me/
    Récupère l'invitation la plus récente reçue par l'utilisateur connecté
    """
    invitations = TeamInvitation.objects.filter(
        invitee=request.user
    ).select_related('team', 'team__contest', 'inviter').order_by('-created_at')
    
    # Filtrer par statut si demandé
    status_filter = request.query_params.get('status')
    if status_filter:
        invitations = invitations.filter(status=status_filter)
    
    invitation = invitations.first()
    
    if not invitation:
        return Response(None)
        
    serializer = TeamInvitationSerializer(invitation)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def remove_member(request, team_id):
    """
    POST /api/teams/{team_id}/remove/
    Retire un membre de l'équipe (réservé au capitaine)
    
    Body: {
        "user_id": 2
    }
    """
    team = get_object_or_404(Team, pk=team_id)
    
    if team.capitaine != request.user:
        return Response(
            {'error': 'Seul le capitaine peut retirer des membres'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user_id = request.data.get('user_id')
    if not user_id:
        return Response(
            {'error': 'user_id est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    from accounts.models import User
    user = get_object_or_404(User, pk=user_id)
    
    try:
        team.remove_member(user, request.user)
        return Response({
            'success': True,
            'message': f'{user.username} a été retiré de l\'équipe',
            'team': TeamDetailSerializer(team, context={'request': request}).data
        })
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def leave_team(request, team_id):
    """
    POST /api/teams/{team_id}/leave/
    Permet à un membre de quitter l'équipe
    """
    team = get_object_or_404(Team, pk=team_id)
    
    try:
        team.leave_team(request.user)
        return Response({
            'success': True,
            'message': 'Vous avez quitté l\'équipe'
        })
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_team_members(request, team_id):
    """
    GET /api/teams/<team_id>/members/
    Liste les membres d'une équipe d'un contest
    """
    team = get_object_or_404(Team, id=team_id)

    # Optionnel : Empêcher un utilisateur non membre ou non admin d'accéder
    # if request.user not in team.members.all() and not request.user.is_staff:
    #     return Response(
    #         {"error": "Vous n'avez pas accès à cette équipe."},
    #         status=status.HTTP_403_FORBIDDEN
    #     )
    
    membres = team.membres.all()
    serializer = UserSerializer(membres, many=True)

    return Response({
        "team_id": team.id,
        "team_name": team.nom,
        "contest": team.contest.title,
        "contest_id": team.contest.id,
        "capitaine_id": team.capitaine.id,
        "capitaine_username": team.capitaine.username,
        "total_members": membres.count(),
        "xp_total": team.xp_total,
        "members": serializer.data
    })



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_membership(request, contest_id):
    """
    GET /api/contests/<contest_id>/check-membership/
    Vérifie si l'utilisateur connecté est membre d'une équipe dans ce contest
    
    Response: {
        "is_member": true/false,
        "team_id": 5 (ou null si pas membre),
        "team_name": "Nom de l'équipe" (ou null),
        "member_count": 3 (ou null)
    }
    """
    contest = get_object_or_404(Contest, pk=contest_id)
    
    # Chercher si l'utilisateur est membre d'une équipe dans ce contest
    team = Team.objects.filter(
        contest=contest,
        membres=request.user
    ).first()
    
    if team:
        return Response({
            'is_member': True,
            'team_id': team.id,
            'team_name': team.nom,
            'member_count': team.membres.count(),
            'contest_id': contest.id,
            'contest_title': contest.title
        })
    else:
        return Response({
            'is_member': False,
            'team_id': None,
            'team_name': None,
            'member_count': None,
            'contest_id': contest.id,
            'contest_title': contest.title
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_captain(request, contest_id):
    """
    GET /api/contests/<contest_id>/check-captain/
    Vérifie si l'utilisateur connecté est capitaine d'une équipe dans ce contest
    
    Response: {
        "is_captain": true/false,
        "team_id": 5 (ou null si pas capitaine),
        "team_name": "Nom de l'équipe" (ou null),
        "member_count": 3 (ou null)
    }
    """
    contest = get_object_or_404(Contest, pk=contest_id)
    
    # Chercher si l'utilisateur est capitaine d'une équipe dans ce contest
    team = Team.objects.filter(
        contest=contest,
        capitaine=request.user
    ).first()
    
    if team:
        return Response({
            'is_captain': True,
            'team_id': team.id,
            'team_name': team.nom,
            'member_count': team.membres.count(),
            'contest_id': contest.id,
            'contest_title': contest.title
        })
    else:
        return Response({
            'is_captain': False,
            'team_id': None,
            'team_name': None,
            'member_count': None,
            'contest_id': contest.id,
            'contest_title': contest.title
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_user_role(request, contest_id):
    """
    GET /api/contests/<contest_id>/check-role/
    Vérifie à la fois si l'utilisateur est membre ET capitaine dans ce contest
    (Vue combinée pour économiser des requêtes)
    
    Response: {
        "is_member": true/false,
        "is_captain": true/false,
        "team_id": 5 (ou null),
        "team_name": "Nom de l'équipe" (ou null),
        "member_count": 3 (ou null),
        "role": "captain" | "member" | "none"
    }
    """
    contest = get_object_or_404(Contest, pk=contest_id)
    
    # Chercher l'équipe de l'utilisateur dans ce contest
    team = Team.objects.filter(
        contest=contest,
        membres=request.user
    ).first()
    
    if team:
        is_captain = team.capitaine == request.user
        role = "captain" if is_captain else "member"
        
        return Response({
            'is_member': True,
            'is_captain': is_captain,
            'team_id': team.id,
            'team_name': team.nom,
            'member_count': team.membres.count(),
            'role': role,
            'contest_id': contest.id,
            'contest_title': contest.title
        })
    else:
        return Response({
            'is_member': False,
            'is_captain': False,
            'team_id': None,
            'team_name': None,
            'member_count': None,
            'role': 'none',
            'contest_id': contest.id,
            'contest_title': contest.title
        })