from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ContestViewSet,
    create_team,
    invite_member,
    remove_member,
    leave_team,
    test_contest_challenge,
    submit_contest_challenge,
    list_team_members,
    accept_invitation,
    decline_invitation,
    my_invitations,
    check_user_role,
    check_user_captain,
    check_user_membership
)
from django.conf import settings
from django.conf.urls.static import static

app_name = 'contests'

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'contests', ContestViewSet, basename='contest')

urlpatterns = [
    # Routes du router (contests)
    # GET /api/contests/ - Liste tous les contests
    # GET /api/contests/{id}/ - Détail d'un contest
    # GET /api/contests/{id}/teams/ - Liste des équipes dans un contest
    # GET /api/contests/{id}/challenges/ - Liste des challenges (si en cours)
    # GET /api/contests/{id}/leaderboard/ - Classement des équipes
    path('', include(router.urls)),
    
    # Gestion des équipes
    path('teams/create/', create_team, name='create-team'),
    path('teams/<int:team_id>/members/', list_team_members, name='team-members'),
    path('teams/<int:team_id>/remove/', remove_member, name='remove-member'),
    path('teams/<int:team_id>/leave/', leave_team, name='leave-team'),

    path('teams/<int:team_id>/invite/', invite_member, name='invite-member'),
    path('invitations/accept/<str:token>/', accept_invitation, name='accept-invitation'),
    path('invitations/decline/<str:token>/', decline_invitation, name='decline-invitation'),
    path('invitations/me/', my_invitations, name='my-invitations'),

    # Vérification du rôle de l'utilisateur dans un contest
    path('contests/<int:contest_id>/check-membership/', check_user_membership, name='check-membership'),
    path('contests/<int:contest_id>/check-captain/', check_user_captain, name='check-captain'),
    path('contests/<int:contest_id>/check-role/', check_user_role, name='check-role'),  # Vue combinée
    
    # Test et soumission de solutions dans un contest
    path(
        'contests/<int:contest_id>/challenges/<int:challenge_id>/test/',
        test_contest_challenge,
        name='test-contest-challenge'
    ),
    path(
        'contests/<int:contest_id>/challenges/<int:challenge_id>/submit/',
        submit_contest_challenge,
        name='submit-contest-challenge'
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)