from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser, AllowAny
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import RegistrationToken, User
from .serializers import (
    InitiateRegistrationSerializer,
    CompleteRegistrationSerializer,
    UserSerializer
)


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
    Vérifier si un token est valide.
    L'utilisateur accède à cette URL via le lien dans l'email.
    """
    token_value = request.query_params.get('token')
    
    if not token_value:
        return Response({
            'error': 'Token manquant.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        token = RegistrationToken.objects.get(token=token_value)
        
        if token.is_valid():
            return Response({
                'message': 'Token valide.',
                'email': token.email
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Token expiré ou déjà utilisé.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except RegistrationToken.DoesNotExist:
        return Response({
            'error': 'Token invalide.'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def complete_registration(request):
    """
    Compléter l'inscription en fournissant tous les champs requis.
    """
    serializer = CompleteRegistrationSerializer(data=request.data)
    
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'message': 'Inscription complétée avec succès.',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
# @permission_classes([IsAdminUser])
def list_users(request):
    """Liste tous les utilisateurs (admin seulement)"""
    users = User.objects.all()
    serializer = UserSerializer(users, many=True)
    return Response(serializer.data)