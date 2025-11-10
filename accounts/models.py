from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    # Les champs de AbstractUser inclus par défaut : 
    # username, email, password, first_name, last_name, etc.
    
    # Vos champs personnalisés
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    photo = models.ImageField(upload_to='photos/', null=True, blank=True)
    numero_inscription = models.CharField(max_length=50, unique=True)
    parcours = models.CharField(max_length=100)
    filiere = models.CharField(max_length=100, null=True, blank=True)
    
    # Champs supplémentaires utiles
    email = models.EmailField(unique=True)  # Rendre email unique
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
    
    def __str__(self):
        return self.username


class RegistrationToken(models.Model):
    """Modèle pour stocker les tokens d'inscription"""
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = 'Token d\'inscription'
        verbose_name_plural = 'Tokens d\'inscription'
    
    def __str__(self):
        return f"Token for {self.email}"
    
    def is_valid(self):
        """Vérifier si le token est encore valide"""
        from django.utils import timezone
        return not self.is_used and self.expires_at > timezone.now()