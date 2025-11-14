# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Exécution de code
    ExecuteCodeView,
    HealthCheckView,
    SupportedLanguagesView,
    SecurityInfoView,
    
    # Challenges
    ChallengeViewSet,
    TestCaseViewSet,
    join_challenge,
    submit_challenge_solution,
    my_challenges,
    test_challenge_solution,
    test_specific_test_case,
    save_code,

    # Team
    create_team,
    accept_team_invitation,
    team_detail,
    team_submit_solution,

    # Leaderboards
    challenge_leaderboard,
    global_leaderboard,
    my_global_stats,
)

app_name = 'api'

# Router pour les ViewSets
router = DefaultRouter()
router.register(r'challenges', ChallengeViewSet, basename='challenge')
router.register(r'test-cases', TestCaseViewSet, basename='testcase')

urlpatterns = [
    # Endpoints d'exécution de code
    path('execute/', ExecuteCodeView.as_view(), name='execute'),
    
    # Endpoints utilitaires
    path('health/', HealthCheckView.as_view(), name='health'),
    path('languages/', SupportedLanguagesView.as_view(), name='languages'),
    path('security-info/', SecurityInfoView.as_view(), name='security-info'),
    
    # Actions sur les challenges
    path('challenges/<int:challenge_id>/join/', join_challenge, name='join-challenge'),
    path('challenges/<int:challenge_id>/test/', test_challenge_solution, name='test-challenge'),
    path('challenges/<int:challenge_id>/test-case/<int:test_case_id>/',test_specific_test_case,name='test-specific-testcase'),

    path('challenges/<int:challenge_id>/submit/', submit_challenge_solution, name='submit-challenge'),
    path('challenges/my-challenges/', my_challenges, name='my-challenges'),
    path('challenges/<int:challenge_id>/create-team/', create_team, name='create-team'),

    path('challenges/<int:challenge_id>/save-code/', save_code, name='save-code'),


    path('team/<int:team_id>/', team_detail, name='team-detail'),
    path('team/<int:team_id>/submit/', team_submit_solution, name='team-submit'),
    path('team/invite/accept/<str:token>/', accept_team_invitation, name='accept-team-invite'),

    
    # Leaderboards
    path('challenges/<int:challenge_id>/leaderboard/', challenge_leaderboard, name='challenge-leaderboard'),
    path('leaderboard/global/', global_leaderboard, name='global-leaderboard'),
    path('my-global-stats/', my_global_stats, name='my-stats'),



    
    # Routes du router
    path('', include(router.urls)),

]