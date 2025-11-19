from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, RegistrationToken

class InitiateRegistrationSerializer(serializers.Serializer):
    """Serializer pour l'admin qui initie l'inscription"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Vérifier si l'email existe déjà
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value


class CompleteRegistrationSerializer(serializers.ModelSerializer):
    """Serializer pour compléter l'inscription par l'utilisateur"""
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password]
    )
    password_confirm = serializers.CharField(write_only=True, required=True)
    token = serializers.UUIDField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'token', 'nom', 'prenom', 'username', 'email',
            'password', 'password_confirm', 'photo',
            'numero_inscription', 'parcours', 'classe'
        ]
        extra_kwargs = {
            'email': {'read_only': True}  # Email déjà défini par le token
        }
    
    def validate(self, attrs):
        # Vérifier que les mots de passe correspondent
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                "password": "Les mots de passe ne correspondent pas."
            })
        return attrs
    
    def create(self, validated_data):
        # Retirer les champs qui ne sont pas dans le modèle User
        token_value = validated_data.pop('token')
        validated_data.pop('password_confirm')
        
        # Vérifier le token
        try:
            token = RegistrationToken.objects.get(token=token_value)
            if not token.is_valid():
                raise serializers.ValidationError("Token invalide ou expiré.")
        except RegistrationToken.DoesNotExist:
            raise serializers.ValidationError("Token invalide.")
        
        # Ajouter l'email du token
        validated_data['email'] = token.email
        
        # Créer l'utilisateur
        user = User.objects.create_user(**validated_data)
        
        # Marquer le token comme utilisé
        token.is_used = True
        token.save()
        
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les informations utilisateur"""
    class Meta:
        model = User
        fields = [
            'id', 'nom', 'prenom', 'username', 'email',
            'photo', 'numero_inscription', 'parcours', 'classe',
            'challenges_joined', 'total_xp'  # 🆕 NOUVEAUX CHAMPS
        ]

class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour consulter / mettre à jour le profil de l'utilisateur connecté.
    - email en lecture seule (on le gère via token d'invitation).
    - certains champs calculés en lecture seule.
    """
    class Meta:
        model = User
        fields = [
            'id', 'nom', 'prenom', 'username', 'email', 'photo',
            'numero_inscription', 'parcours', 'classe',
            'challenges_joined', 'total_xp'
        ]
        read_only_fields = (
            'email', 'challenges_joined', 'total_xp', 'numero_inscription', 'username'
        )