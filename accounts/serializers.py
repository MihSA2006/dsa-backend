from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User, RegistrationToken
from django.contrib.auth import get_user_model

class InitiateRegistrationSerializer(serializers.Serializer):
    """Serializer pour l'admin qui initie l'inscription"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Vérifier si l'email existe déjà
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Cet email est déjà utilisé.")
        return value


class CompleteRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    token = serializers.UUIDField(write_only=True, required=True)
    photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = [
            'token', 'nom', 'prenom', 'username', 'email',
            'password', 'password_confirm', 'photo',
            'numero_inscription', 'parcours', 'classe'
        ]
        extra_kwargs = {
            'email': {'read_only': True}
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


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Serializer pour afficher les informations utilisateur"""
    photo = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'nom', 'prenom', 'username', 'email',
            'photo', 'numero_inscription', 'parcours', 'classe',
            'challenges_joined', 'total_xp'
        ]
    
    def get_photo(self, obj):
        """Retourne l'URL complète de la photo"""
        if obj.photo:
            # Si vous utilisez Cloudinary, l'URL est déjà complète
            return obj.photo.url
        return None

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

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'nom', 'prenom', 'username', 'email',
            'photo', 'numero_inscription', 'parcours', 'classe',
            'challenges_joined', 'total_xp'
        ]
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

class InitiatePasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()
    
    def validate_email(self, value):
        # Vérifier que l'utilisateur existe
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun utilisateur avec cet email.")
        return value


class CompletePasswordResetSerializer(serializers.Serializer):
    token = serializers.UUIDField()
    new_password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        # Vérifier que les mots de passe correspondent
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({
                "confirm_password": "Les mots de passe ne correspondent pas."
            })
        
        # Valider le mot de passe selon les règles Django
        try:
            validate_password(data['new_password'])
        except Exception as e:
            raise serializers.ValidationError({
                "new_password": list(e.messages)
            })
        
        return data

class EditProfileSerializer(serializers.ModelSerializer):
    """
    Serializer pour l'édition du profil utilisateur.
    Permet uniquement de modifier : nom, prenom, photo, numero_inscription, classe, parcours
    """
    
    class Meta:
        model = User
        fields = ['nom', 'prenom', 'photo', 'numero_inscription', 'classe', 'parcours']
        extra_kwargs = {
            'nom': {'required': False},
            'prenom': {'required': False},
            'photo': {'required': False},
            'numero_inscription': {'required': False},
            'classe': {'required': False},
            'parcours': {'required': False},
        }
    
    def validate_numero_inscription(self, value):
        """
        Vérifier que le numéro d'inscription n'est pas déjà utilisé par un autre utilisateur
        """
        user = self.instance  # L'utilisateur actuel
        if User.objects.filter(numero_inscription=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Ce numéro d'inscription est déjà utilisé.")
        return value
    
    def validate_classe(self, value):
        """
        Vérifier que la classe est dans les choix autorisés
        """
        valid_classes = [choice[0] for choice in User.CLASSE_CHOICES]
        if value not in valid_classes:
            raise serializers.ValidationError(f"Classe invalide. Choix possibles : {', '.join(valid_classes)}")
        return value
    
    def validate_parcours(self, value):
        """
        Vérifier que le parcours est dans les choix autorisés
        """
        valid_parcours = [choice[0] for choice in User.PARCOURS_CHOICES]
        if value not in valid_parcours:
            raise serializers.ValidationError(f"Parcours invalide. Choix possibles : {', '.join(valid_parcours)}")
        return value
    
    def to_representation(self, instance):
        """
        Personnaliser la réponse pour inclure l'URL complète de la photo
        """
        data = super().to_representation(instance)
        if instance.photo:
            data['photo'] = instance.photo.url
        return data
    

    