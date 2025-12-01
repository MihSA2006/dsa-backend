from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

app_name = 'accounts'

urlpatterns = [
    # Inscription
    path('register/initiate/', views.initiate_registration, name='initiate_registration'),
    path('verify-back/register/', views.verify_token, name='verify_token'),
    path('register/complete/', views.complete_registration, name='complete_registration'),
    
    # Connexion (JWT)
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Liste des utilisateurs
    path('users/', views.list_users, name='list_users'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('is-admin/', views.is_admin, name='is_admin'),
    path('users/profiles/<int:user_id>/', views.get_user_profile_with_stats, name='get_users_profiles'),

    # Verify Token
    path('token/verify-refresh/', views.verify_refresh_token, name='verify_refresh_token'),
    path('token/verify-access/', views.verify_access_token, name='verify_access_token'),

    # Reset Password
    path('password-reset/initiate/', views.initiate_password_reset, name='initiate_password_reset'),
    path('verify-back/password-reset/', views.verify_reset_token, name='verify_reset_token'),
    path('password-reset/complete/', views.complete_password_reset, name='complete_password_reset'),
]

