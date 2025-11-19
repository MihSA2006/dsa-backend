from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Inscription
    path('register/initiate/', views.initiate_registration, name='initiate_registration'),
    path('register/verify/', views.verify_token, name='verify_token'),
    path('register/complete/', views.complete_registration, name='complete_registration'),
    
    # Connexion (JWT)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Liste des utilisateurs
    path('users/', views.list_users, name='list_users'),
    path('profile/', views.profile, name='profile'),
    path('token/verify-refresh/', views.verify_refresh_token, name='verify_refresh_token'),
    path('token/verify-access/', views.verify_access_token, name='verify_access_token'),
]

