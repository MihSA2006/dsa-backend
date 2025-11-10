# api/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ExecuteCodeView,
    HealthCheckView,
    SupportedLanguagesView,
    SecurityInfoView,
    ChallengeViewSet,
    TestCaseViewSet,
    ChallengeSubmissionView
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
    
    # Endpoint de soumission de challenge
    path('challenges/submit/', ChallengeSubmissionView.as_view(), name='challenge-submit'),
    
    # Routes du router (challenges et test-cases)
    path('', include(router.urls)),
]