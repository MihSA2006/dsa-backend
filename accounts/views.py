from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import RegistrationToken, User
from .serializers import (
    InitiateRegistrationSerializer,
    CompleteRegistrationSerializer,
    UserSerializer,
    ProfileSerializer,
    CompletePasswordResetSerializer,
    InitiatePasswordResetSerializer,
    EditProfileSerializer
)
from .models import PasswordResetToken

from api.models import UserChallengeAttempt
from django.shortcuts import redirect
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken


from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives


from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

from threading import Thread
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from django.template.loader import render_to_string
from .email_utils import send_email_sendgrid 

from django.shortcuts import render
from django.http import JsonResponse

@api_view(['POST'])
@permission_classes([IsAdminUser])
def initiate_registration(request):
    """
    Vue pour l'admin qui initie l'inscription.
    L'admin envoie seulement l'email.
    """
    serializer = InitiateRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        # Supprimer l'ancien token si existe
        RegistrationToken.objects.filter(email=email).delete()
        
        # Créer un nouveau token
        token = RegistrationToken.objects.create(
            email=email,
            expires_at=timezone.now() + timedelta(hours=48)
        )
        
        # Créer le lien d'inscription
        registration_link = f"https://dsa-3v1v.onrender.com/api/accounts/verify-back/register/?token={token.token}"
        
        subject = "Invitation à compléter votre inscription"
        html_content = render_to_string('mail.html', {
            'registration_link': registration_link
        })

        # 🔥 Fonction pour envoyer l'email de manière asynchrone
        def send_email_async():
            success = send_email_sendgrid(email, subject, html_content)
            if success:
                print(f"✅ Email envoyé avec succès à {email}")
            else:
                print(f"❌ Échec de l'envoi à {email}")
        
        # Lancer l'envoi dans un thread séparé
        Thread(target=send_email_async, daemon=True).start()
        
        return Response({
            'message': 'Email d\'invitation envoyé avec succès.',
            'email': email,
            'token': str(token.token)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def initiate_password_reset(request):
    """
    L'admin initie la réinitialisation du mot de passe.
    Envoie un email avec un token à l'utilisateur.
    """
    serializer = InitiatePasswordResetSerializer(data=request.data)
    
    if serializer.is_valid():
        email = serializer.validated_data['email']
        
        # Supprimer les anciens tokens non utilisés pour cet email
        PasswordResetToken.objects.filter(email=email, used=False).delete()
        
        # Créer un nouveau token
        token = PasswordResetToken.objects.create(
            email=email,
            expires_at=timezone.now() + timedelta(hours=48)
        )
        
        # Créer le lien de réinitialisation
        reset_link = f"https://dsa-3v1v.onrender.com/api/accounts/verify-back/password-reset/?token={token.token}"
        
        # Sujet de l'email
        subject = "Réinitialisation de votre mot de passe"
        
        # Charger le template HTML
        html_content = render_to_string('reset.html', {
            'reset_link': reset_link
        })
        
        # Envoyer l'email
        email_message = EmailMultiAlternatives(
            subject,
            "",  # Version texte (facultatif)
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
            [email]
        )
        email_message.attach_alternative(html_content, "text/html")
        email_message.send()
        
        return Response({
            'message': 'Email de réinitialisation envoyé avec succès.',
            'email': email,
            'token': str(token.token)
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_reset_token(request):
    """
    Vérifie si le token de réinitialisation est valide.
    Si valide → redirige vers le frontend avec le token.
    """
    token_value = request.query_params.get('token')
    
    if not token_value:
        return Response({'error': 'Token manquant.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token = PasswordResetToken.objects.get(token=token_value)
        
        if token.is_valid():
            # Redirection vers le frontend avec le token
            frontend_url = f"https://dsa-kohl-one.vercel.app/reset-password?token={token_value}"
            return redirect(frontend_url)
        else:
            return Response({
                'error': 'Token expiré ou déjà utilisé.'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    except PasswordResetToken.DoesNotExist:
        return Response({'error': 'Token invalide.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_password_reset(request):
    """
    L'utilisateur envoie le nouveau mot de passe avec le token.
    """
    serializer = CompletePasswordResetSerializer(data=request.data)
    
    if serializer.is_valid():
        token_value = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        
        try:
            token = PasswordResetToken.objects.get(token=token_value)
            
            if not token.is_valid():
                return Response({
                    'message': False,
                    'error': 'Token expiré ou déjà utilisé.'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Récupérer l'utilisateur
            user = User.objects.get(email=token.email)
            
            # Changer le mot de passe
            user.set_password(new_password)
            user.save()
            
            # Marquer le token comme utilisé
            token.used = True
            token.save()
            
            return Response({
                'message': True,
                'detail': 'Mot de passe réinitialisé avec succès.'
            }, status=status.HTTP_200_OK)
        
        except PasswordResetToken.DoesNotExist:
            return Response({
                'message': False,
                'error': 'Token invalide.'
            }, status=status.HTTP_404_NOT_FOUND)
        
        except User.DoesNotExist:
            return Response({
                'message': False,
                'error': 'Utilisateur introuvable.'
            }, status=status.HTTP_404_NOT_FOUND)
    
    return Response({
        'message': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([AllowAny])
def verify_token(request):
    """
    Vérifie si un token est valide.
    Si valide → redirige vers le frontend avec le token.
    """
    token_value = request.query_params.get('token')

    if not token_value:
        return Response({'error': 'Token manquant.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        token = RegistrationToken.objects.get(token=token_value)

        if token.is_valid():
            frontend_url = f"https://dsa-kohl-one.vercel.app/register?token={token_value}"
            return redirect(frontend_url)
        
        else:
            return Response({'error': 'Token expiré ou déjà utilisé.'}, status=status.HTTP_400_BAD_REQUEST)

    except RegistrationToken.DoesNotExist:
        return Response({'error': 'Token invalide.'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def complete_registration(request):
    serializer = CompleteRegistrationSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': True,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response({
        'message': False,
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_users(request):
    """Liste tous les utilisateurs (admin seulement)"""
    users = User.objects.all()
    serializer = UserSerializer(users, many=True, context={'request': request})
    return Response(serializer.data)

@api_view(['GET', 'PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def profile(request):
    """
    GET -> retourne les données du user connecté.
    PUT/PATCH -> met à jour le profil (PATCH partiel recommandé).
    Supporte upload d'image via multipart/form-data (champ 'photo').
    """
    user = request.user

    if request.method == 'GET':
        serializer = ProfileSerializer(user)
        return Response(serializer.data)

    partial = (request.method == 'PATCH')
    serializer = ProfileSerializer(user, data=request.data, partial=partial)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def is_admin(request):
    """
    Vérifie si l'utilisateur connecté est admin (superuser)
    → retourne { "is_admin": true } ou { "is_admin": false }
    """
    user = request.user
    return Response({
        "is_admin": user.is_superuser
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile_with_stats(request, user_id):
    """
    Retourne le profil COMPLET d’un utilisateur avec :
    - infos
    - stats de challenges
    - classement global
    """
    # Récupérer l’utilisateur
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return Response({"error": "Utilisateur introuvable"}, status=404)

    # Récupérer les tentatives
    attempts = UserChallengeAttempt.objects.filter(user=user)
    completed = attempts.filter(status='completed')

    # Construction de la réponse
    data = {
        'user': {
            'id': user.id,
            'username': user.username,
            'nom': user.nom,
            'prenom': user.prenom,
            'numero_inscription' : user.numero_inscription,
            'classe': user.classe,
            'parcours': user.parcours,
            'email': user.email,
            'total_xp': user.total_xp,
            'challenges_joined': user.challenges_joined,
            'photo': user.photo.url if user.photo else None
        },
        'challenges': {
            # 'joined': attempts.count(),
            'completed': completed.count(),
            'in_progress': attempts.filter(status='in_progress').count(),
            'completion_rate': round(
                (completed.count() / attempts.count() * 100)
                if attempts.count() > 0 else 0,
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

    return Response(data)




@api_view(['POST'])
@permission_classes([])
def verify_refresh_token(request):
    """
    Vérifie si un refresh token JWT est encore valide.
    Ne renvoie PAS de nouveau access token.
    """
    token = request.data.get("refresh")

    if not token:
        return Response({"detail": "Refresh token manquant"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        RefreshToken(token)
        return Response({"valid": True}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({"valid": False}, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@permission_classes([])
def verify_access_token(request):
    """
    Vérifie si un access token JWT est encore valide.
    Ne génère rien, ne rafraîchit rien.
    """
    token = request.data.get("access")

    if not token:
        return Response({"detail": "Access token manquant"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        AccessToken(token)
        return Response({"valid": True}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({"valid": False}, status=status.HTTP_200_OK)

def custom_404_view(request, exception):
    return render(request, '404.html', status=404)

def custom_404_api(request, exception=None):
    return JsonResponse({
        "status": 404,
        "error": "URL not found",
        "message": "La route demandée n'existe pas."
    }, status=404)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser, JSONParser])
def edit_profile(request):
    """
    Permet à un utilisateur connecté de modifier son profil.
    
    Champs modifiables : nom, prenom, photo, numero_inscription, classe, parcours
    
    PUT : Mise à jour complète (tous les champs requis)
    PATCH : Mise à jour partielle (seulement les champs envoyés)
    
    Support multipart/form-data pour l'upload de photo
    """
    user = request.user
    
    partial = (request.method == 'PATCH')
    
    serializer = EditProfileSerializer(
        user, 
        data=request.data, 
        partial=partial
    )
    
    if serializer.is_valid():
        serializer.save()
        
        return Response({
            'message': 'Profil mis à jour avec succès.',
            'user': serializer.data
        }, status=status.HTTP_200_OK)
    
    return Response({
        'message': 'Erreur lors de la mise à jour du profil.',
        'errors': serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)
