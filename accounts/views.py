from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import RegistrationToken, User
from .serializers import (
    InitiateRegistrationSerializer,
    CompleteRegistrationSerializer,
    UserSerializer,
    ProfileSerializer
)

from django.shortcuts import redirect
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework_simplejwt.tokens import RefreshToken, TokenError, AccessToken

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
            expires_at=timezone.now() + timedelta(hours=48)  # Valide 48h
        )
        
        # Créer le lien d'inscription
        registration_link = f"http://localhost:8000/api/accounts/register/verify/?token={token.token}"
        
        # Envoyer l'email
        subject = "Invitation à compléter votre inscription"
        message = f"""
        Bonjour,
        
        Vous avez été invité à créer un compte sur notre plateforme.
        
        Veuillez cliquer sur le lien suivant pour compléter votre inscription :
        {registration_link}
        
        Ce lien est valide pendant 48 heures.
        
        Cordialement,
        L'équipe
        """
        
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@example.com',
            [email],
            fail_silently=False,
        )
        
        return Response({
            'message': 'Email d\'invitation envoyé avec succès.',
            'email': email,
            'token': str(token.token)  # Pour tests avec Postman
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)




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
            # 🔁 Redirection vers le frontend avec le token
            frontend_url = f"http://localhost:3000/register?token={token_value}"
            return redirect(frontend_url)
        
        else:
            return Response({'error': 'Token expiré ou déjà utilisé.'}, status=status.HTTP_400_BAD_REQUEST)

    except RegistrationToken.DoesNotExist:
        return Response({'error': 'Token invalide.'}, status=status.HTTP_404_NOT_FOUND)




@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def complete_registration(request):
    serializer = CompleteRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': True,
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response({'message':False}, serializer.errors, status=status.HTTP_400_BAD_REQUEST)





@api_view(['GET'])
# @permission_classes([IsAdminUser])
def list_users(request):
    """Liste tous les utilisateurs (admin seulement)"""
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
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

    # PUT ou PATCH
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
        "is_admin": user.is_superuser  # True / False
    })


@api_view(['POST'])
@permission_classes([])  # pas besoin d’être connecté
def verify_refresh_token(request):
    """
    Vérifie si un refresh token JWT est encore valide.
    Ne renvoie PAS de nouveau access token.
    """
    token = request.data.get("refresh")

    if not token:
        return Response({"detail": "Refresh token manquant"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        RefreshToken(token)  # essaie de décoder et valider le token
        return Response({"valid": True}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({"valid": False}, status=status.HTTP_200_OK)
    

@api_view(['POST'])
@permission_classes([])  # Pas besoin d’être authentifié
def verify_access_token(request):
    """
    Vérifie si un access token JWT est encore valide.
    Ne génère rien, ne rafraîchit rien.
    """
    token = request.data.get("access")

    if not token:
        return Response({"detail": "Access token manquant"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        AccessToken(token)  # Essaie de décoder et vérifier la validité du token
        return Response({"valid": True}, status=status.HTTP_200_OK)
    except TokenError:
        return Response({"valid": False}, status=status.HTTP_200_OK)