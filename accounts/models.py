# accounts/models.py

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

    CLASSE_CHOICES = [
        ("L1", "L1"),
        ("L2", "L2"),
        ("L3", "L3"),
        ("M1", "M1"),
        ("M2", "M2"),
    ]
    # classe = models.CharField(max_length=2, choices=CLASSE_CHOICES)

    classe = models.CharField(max_length=2, choices=CLASSE_CHOICES, default='L1')
    PARCOURS_CHOICES = [
        ("Software Engineering", "Software Engineering"),
        ("Artificial Intelligence", "Artificial Intelligence"),
        ("Network Administration", "Network Administration"),
        ("Common Core", "Common Core"),
    ]
    # parcours = models.CharField(max_length=50, choices=PARCOURS_CHOICES)
    parcours = models.CharField(max_length=50, choices=PARCOURS_CHOICES, default='Common Core')

    
    # Champs supplémentaires utiles
    email = models.EmailField(unique=True)  # Rendre email unique
    
    # 🆕 NOUVEAUX CHAMPS
    challenges_joined = models.IntegerField(
        default=0, 
        verbose_name="Nombre de challenges rejoints"
    )
    total_xp = models.IntegerField(
        default=0, 
        verbose_name="XP total"
    )
    
    class Meta:
        verbose_name = 'Utilisateur'
        verbose_name_plural = 'Utilisateurs'
        ordering = ['-total_xp', 'username']  # Tri par XP décroissant
    
    def __str__(self):
        return self.username
    
    def update_stats(self):
        """Met à jour les statistiques de l'utilisateur"""
        from api.models import UserChallengeAttempt
        
        # Nombre de challenges rejoints
        self.challenges_joined = UserChallengeAttempt.objects.filter(
            user=self
        ).values('challenge').distinct().count()
        
        # XP total = somme de tous les XP validés (progressifs)
        attempts = UserChallengeAttempt.objects.filter(
            user=self
        ).select_related('challenge')
        
        self.total_xp = sum(
            attempt.xp_earned for attempt in attempts
        )
        
        self.save()
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
class PasswordResetToken(models.Model):
    email = models.EmailField()
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    def is_valid(self):
        from django.utils import timezone
        return not self.used and timezone.now() < self.expires_at
    
    def __str__(self):
        return f"Reset token pour {self.email}"