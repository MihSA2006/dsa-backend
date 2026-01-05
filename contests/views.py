from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.exceptions import ValidationError
import logging
from accounts.serializers import UserSerializer
from .models import Contest, Team, ContestSubmission
from .serializers import (
    ContestListSerializer,
    ContestDetailSerializer,
    TeamListSerializer,
    TeamDetailSerializer,
    TeamCreateSerializer,
    ContestSubmissionSerializer,
    TeamInvitationSerializer
)
from api.models import Challenge
from api.challenge_validator import ChallengeValidator
from api.security import SecurityChecker

logger = logging.getLogger(__name__)


class ContestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet pour les contests (lecture seule pour les utilisateurs)
    """
    queryset = Contest.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ContestListSerializer
        return ContestDetailSerializer
    
    def list(self, request):
        """Liste tous les contests"""
        contests = self.get_queryset()
        
        # Mettre à jour le statut de tous les contests
        for contest in contests:
            contest.update_status()
            contest.save(update_fields=['statut'])
        
        serializer = ContestListSerializer(contests, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Détail d'un contest"""
        contest = get_object_or_404(Contest, pk=pk)
        
        # Mettre à jour le statut avant de retourner
        contest.update_status()
        contest.save(update_fields=['statut'])
        
        serializer = ContestDetailSerializer(contest)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def teams(self, request, pk=None):
        """GET /api/contests/{id}/teams/"""
        contest = get_object_or_404(Contest, pk=pk)
        
        # Mettre à jour le statut
        contest.update_status()
        contest.save(update_fields=['statut'])
        
        teams = contest.teams.all()
        serializer = TeamListSerializer(teams, many=True)
        return Response({
            'contest_id': contest.id,
            'contest_title': contest.title,
            'contest_status': contest.statut,
            'total_teams': teams.count(),
            'teams': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def challenges(self, request, pk=None):
        """GET /api/contests/{id}/challenges/"""
        contest = get_object_or_404(Contest, pk=pk)
        
        # Mettre à jour le statut
        contest.update_status()
        contest.save(update_fields=['statut'])
        
        if not contest.is_ongoing():
            return Response({
                'error': 'Les challenges ne sont visibles que pendant le contest',
                'contest_status': contest.statut
            }, status=status.HTTP_403_FORBIDDEN)
        
        from api.serializers import ChallengeListSerializer
        challenges = contest.challenges.all()
        serializer = ChallengeListSerializer(challenges, many=True, context={'request': request})
        
        return Response({
            'contest_id': contest.id,
            'contest_title': contest.title,
            'total_challenges': challenges.count(),
            'challenges': serializer.data
        })
    
    @action(detail=True, methods=['get'])
    def leaderboard(self, request, pk=None):
        """GET /api/contests/{id}/leaderboard/"""
        contest = get_object_or_404(Contest, pk=pk)
        
        # Mettre à jour le statut
        contest.update_status()
        contest.save(update_fields=['statut'])
        
        teams = contest.teams.all()
        serializer = TeamListSerializer(teams, many=True)
        
        return Response({
            'contest_id': contest.id,
            'contest_title': contest.title,
            'contest_status': contest.statut,
            'leaderboard': serializer.data
        })


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


# @api_view(['POST'])
# @permission_classes([IsAuthenticated])
# def invite_member(request, team_id):
#     """
#     POST /api/teams/{team_id}/invite/
#     Invite un membre à rejoindre l'équipe (réservé au capitaine)
    
#     Body: {
#         "user_id": 2
#     }
#     """
#     team = get_object_or_404(Team, pk=team_id)
    
#     # Vérifier que le requester est le capitaine
#     if team.capitaine != request.user:
#         return Response(
#             {'error': 'Seul le capitaine peut inviter des membres'},
#             status=status.HTTP_403_FORBIDDEN
#         )
    
#     user_id = request.data.get('user_id')
#     if not user_id:
#         return Response(
#             {'error': 'user_id est requis'},
#             status=status.HTTP_400_BAD_REQUEST
#         )
    
#     from accounts.models import User
#     user = get_object_or_404(User, pk=user_id)
    
#     try:
#         team.add_member(user, request.user)
#         return Response({
#             'success': True,
#             'message': f'{user.username} a été ajouté à l\'équipe',
#             'team': TeamDetailSerializer(team, context={'request': request}).data
#         })
#     except ValidationError as e:
#         return Response(
#             {'error': str(e)},
#             status=status.HTTP_400_BAD_REQUEST
#         )


from .utils import send_team_invitation_email
from .models import TeamInvitation

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def invite_member(request, team_id):
    """
    POST /api/teams/{team_id}/invite/
    Envoie une invitation par email à un membre pour rejoindre l'équipe
    
    Body: {
        "user_id": 2
    }
    """
    team = get_object_or_404(Team, pk=team_id)
    
    # Vérifier que le requester est le capitaine
    if team.capitaine != request.user:
        return Response(
            {'error': 'Seul le capitaine peut inviter des membres'},
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
    
    # Vérifier si l'utilisateur peut être ajouté
    can_add, message = team.can_add_member(user)
    if not can_add:
        return Response(
            {'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier s'il y a déjà une invitation en attente
    existing_invitation = TeamInvitation.objects.filter(
        team=team,
        invitee=user,
        status='pending'
    ).first()
    
    if existing_invitation and existing_invitation.is_valid():
        return Response(
            {'error': 'Une invitation est déjà en attente pour cet utilisateur'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Créer l'invitation
    invitation = TeamInvitation.objects.create(
        team=team,
        inviter=request.user,
        invitee=user
    )
    
    # Envoyer l'email
    email_sent = send_team_invitation_email(invitation, request)
    
    if email_sent:
        return Response({
            'success': True,
            'message': f'Une invitation a été envoyée à {user.username}',
            'invitation': TeamInvitationSerializer(invitation).data
        }, status=status.HTTP_201_CREATED)
    else:
        # Supprimer l'invitation si l'email n'a pas pu être envoyé
        invitation.delete()
        return Response(
            {'error': 'Erreur lors de l\'envoi de l\'email'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


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
    Liste les invitations reçues par l'utilisateur connecté
    """
    invitations = TeamInvitation.objects.filter(
        invitee=request.user
    ).select_related('team', 'team__contest', 'inviter')
    
    # Filtrer par statut si demandé
    status_filter = request.query_params.get('status')
    if status_filter:
        invitations = invitations.filter(status=status_filter)
    
    serializer = TeamInvitationSerializer(invitations, many=True)
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


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_contest_challenge(request, contest_id, challenge_id):
    """
    POST /api/contests/{contest_id}/challenges/{challenge_id}/test/
    Teste une solution pour un challenge de contest (sans l'enregistrer)
    
    Body: {
        "code": "...",
        "team_id": 1
    }
    """
    contest = get_object_or_404(Contest, pk=contest_id)
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Vérifier que le contest est en cours
    if not contest.is_ongoing():
        return Response(
            {'error': 'Le contest n\'est pas en cours'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que le challenge fait partie du contest
    if not contest.challenges.filter(id=challenge.id).exists():
        return Response(
            {'error': 'Ce challenge ne fait pas partie du contest'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer l'équipe
    team_id = request.data.get('team_id')
    if not team_id:
        return Response(
            {'error': 'team_id est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    team = get_object_or_404(Team, pk=team_id, contest=contest)
    
    # Vérifier que l'utilisateur est membre de l'équipe
    if not team.membres.filter(id=request.user.id).exists():
        return Response(
            {'error': 'Vous devez être membre de cette équipe'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer le code
    code = request.data.get('code')
    if not code:
        return Response(
            {'error': 'Le code est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier la sécurité du code
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)
    if not is_safe:
        return Response(
            {'error': f'Sécurité : {error_message}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer les test cases
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response(
            {'error': 'Ce challenge ne contient pas encore de tests'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    test_data = [
        {
            'input_content': tc.get_input(),
            'expected_output': tc.get_output(),
            'order': tc.order
        }
        for tc in test_cases
    ]
    
    # Exécuter les tests
    try:
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)
        
        if result['success']:
            result['message'] = "✅ Tous les tests ont réussi ! Vous pouvez soumettre."
        else:
            result['message'] = (
                f"❌ {result['passed_tests']}/{result['total_tests']} tests réussis."
            )
        
        return Response(result)
    except Exception as e:
        logger.error(f"Erreur lors du test de la solution : {str(e)}")
        return Response(
            {'error': f'Erreur serveur : {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_contest_challenge(request, contest_id, challenge_id):
    """
    POST /api/contests/{contest_id}/challenges/{challenge_id}/submit/
    Soumet une solution pour un challenge de contest
    
    Body: {
        "code": "...",
        "team_id": 1
    }
    """
    contest = get_object_or_404(Contest, pk=contest_id)
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    
    # Vérifier que le contest est en cours
    if not contest.is_ongoing():
        return Response(
            {'error': 'Le contest n\'est pas en cours'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Vérifier que le challenge fait partie du contest
    if not contest.challenges.filter(id=challenge.id).exists():
        return Response(
            {'error': 'Ce challenge ne fait pas partie du contest'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer l'équipe
    team_id = request.data.get('team_id')
    if not team_id:
        return Response(
            {'error': 'team_id est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    team = get_object_or_404(Team, pk=team_id, contest=contest)
    
    # Vérifier que l'utilisateur est membre
    if not team.membres.filter(id=request.user.id).exists():
        return Response(
            {'error': 'Vous devez être membre de cette équipe'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer le code
    code = request.data.get('code')
    if not code:
        return Response(
            {'error': 'Le code est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier la sécurité
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)
    if not is_safe:
        return Response(
            {'error': f'Sécurité : {error_message}'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Récupérer les test cases
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response(
            {'error': 'Ce challenge ne contient pas encore de tests'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    test_data = [
        {
            'input_content': tc.get_input(),
            'expected_output': tc.get_output(),
            'order': tc.order
        }
        for tc in test_cases
    ]
    
    # Exécuter les tests
    try:
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)
        
        passed_tests = result.get('passed_tests', 0)
        total_tests = result.get('total_tests', len(test_data))
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        # Calculer l'XP et le temps
        xp_earned = int(challenge.xp_reward * success_rate)
        
        # Calculer le temps depuis le début du contest
        time_diff = timezone.now() - contest.date_debut
        temps_soumission = int(time_diff.total_seconds())
        
        # Créer ou mettre à jour la soumission
        submission, created = ContestSubmission.objects.update_or_create(
            equipe=team,
            challenge=challenge,
            defaults={
                'submitted_by': request.user,
                'code_soumis': code,
                'xp_earned': xp_earned,
                'temps_soumission': temps_soumission,
                'tests_reussis': passed_tests,
                'tests_total': total_tests
            }
        )
        
        return Response({
            'success': True,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'xp_earned': xp_earned,
            'xp_total': challenge.xp_reward,
            'temps_soumission': temps_soumission,
            'message': f'Soumission enregistrée. XP : {xp_earned}/{challenge.xp_reward}',
            'submission': ContestSubmissionSerializer(submission).data
        })
        
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Erreur lors de la soumission : {str(e)}")
        return Response(
            {'error': f'Erreur serveur : {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
        "capitaine_id": team.capitaine.id,
        "capitaine_username": team.capitaine.username,
        "total_members": membres.count(),
        "xp_total": team.xp_total,
        "members": serializer.data
    })