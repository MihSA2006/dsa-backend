# api/urls.py

from django.urls import path
from .views import (
    ExecuteCodeView,
    HealthCheckView,
    SupportedLanguagesView,
    SecurityInfoView
)

app_name = 'api'

urlpatterns = [
    # Endpoint principal : exécution du code
    path('execute/', ExecuteCodeView.as_view(), name='execute'),
    
    # Endpoints utilitaires
    path('health/', HealthCheckView.as_view(), name='health'),
    path('languages/', SupportedLanguagesView.as_view(), name='languages'),
    path('security-info/', SecurityInfoView.as_view(), name='security-info'),
]