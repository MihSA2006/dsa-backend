# api/models.py

from django.db import models
from django.core.validators import FileExtensionValidator
from django.conf import settings
import os

from django.utils import timezone
from django.core.mail import send_mail
from django.urls import reverse
import uuid
from cloudinary.models import CloudinaryField

class Challenge(models.Model):
    """
    Modèle pour les challenges de programmation
    """
    
    DIFFICULTY_CHOICES = [
        ('easy', 'Facile'),
        ('medium', 'Moyen'),
        ('hard', 'Difficile'),
    ]
    
    # Informations de base
    title = models.CharField(max_length=200, verbose_name="Titre")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="Slug")
    difficulty = models.CharField(
        max_length=10, 
        choices=DIFFICULTY_CHOICES, 
        default='easy',
        verbose_name="Niveau de difficulté"
    )
    
    # Description (fichier markdown)
    description_file = CloudinaryField(
        'file',
        resource_type='raw',
        blank=True,
        null=True,
        # verbose_name="Fichier description (markdown)"
    )
    
    # Template initial
    template_file = CloudinaryField(
        'file',
        resource_type='raw',
        blank=True,
        null=True,
        # verbose_name="Fichier template (.py)"
    )
    
    # XP Reward
    xp_reward = models.IntegerField(
        default=100,
        verbose_name="Points XP"
    )
    
    # 🆕 NOUVEAU CHAMP : Nombre de participants
    participants_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de participants"
    )
    
    xp_required = models.IntegerField(
        default=0,
        verbose_name="XP minimum requis pour valider la soumission"
    )

    # Description PDF optionnelle
    description_pdf = CloudinaryField(
        'file',
        resource_type='raw',
        blank=True,
        null=True,
        # verbose_name="Description en PDF"
    )

    # Image optionnelle
    description_img = CloudinaryField(
        'image',
        blank=True,
        null=True,
        # verbose_name="Image de description"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, verbose_name="Actif")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"
    
    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()}) - {self.xp_reward} XP"
    
    def get_description(self):
        """Lit et retourne le contenu du fichier description depuis Cloudinary"""
        try:
            if self.description_file:
                # Cloudinary stocke l'URL, vous devrez télécharger le contenu
                import requests
                response = requests.get(self.description_file.url)
                if response.status_code == 200:
                    return response.text
            return ""
        except Exception:
            return ""
    
    def get_template(self):
        """Lit et retourne le contenu du fichier template depuis Cloudinary"""
        try:
            if self.template_file:
                # Cloudinary stocke l'URL, vous devrez télécharger le contenu
                import requests
                response = requests.get(self.template_file.url)
                if response.status_code == 200:
                    return response.text
            return ""
        except Exception:
            return ""
    
    def update_participants_count(self):
        """Met à jour le nombre de participants"""
        self.participants_count = UserChallengeAttempt.objects.filter(
            challenge=self
        ).count()
        self.save(update_fields=['participants_count'])
    
    def get_completion_rate(self):
        """Retourne le taux de complétion"""
        if self.participants_count == 0:
            return 0
        completed = UserChallengeAttempt.objects.filter(
            challenge=self, 
            status='completed'
        ).count()
        return round((completed / self.participants_count) * 100, 2)


class TestCase(models.Model):
    """
    Modèle pour les cas de test d'un challenge
    Chaque challenge peut avoir plusieurs test cases
    """
    
    challenge = models.ForeignKey(
        Challenge, 
        on_delete=models.CASCADE, 
        related_name='test_cases'
    )
    
    # Fichiers input/output
    input_file = CloudinaryField(
        'file',
        resource_type='raw',
        blank=True,
        null=True,
        # verbose_name="Fichier input (.txt)"
    )
    
    output_file = CloudinaryField(
        'file',
        resource_type='raw',
        blank=True,
        null=True,
        # verbose_name="Fichier output (.txt)"
    )
    
    # Ordre d'affichage
    order = models.IntegerField(default=0, verbose_name="Ordre")
    
    # Métadonnées
    is_sample = models.BooleanField(
        default=False, 
        verbose_name="Exemple visible"
    )
    
    class Meta:
        ordering = ['order']
        verbose_name = "Test Case"
        verbose_name_plural = "Test Cases"
    
    def __str__(self):
        return f"Test {self.order} - {self.challenge.title}"
    
    def get_input(self):
        """Lit et retourne le contenu du fichier input depuis Cloudinary"""
        try:
            if self.input_file:
                import requests
                response = requests.get(self.input_file.url)
                if response.status_code == 200:
                    return response.text
            return ""
        except Exception:
            return ""
    
    def get_output(self):
        """Lit et retourne le contenu du fichier output depuis Cloudinary"""
        try:
            if self.output_file:
                import requests
                response = requests.get(self.output_file.url)
                if response.status_code == 200:
                    return response.text
            return ""
        except Exception:
            return ""


# 🆕 NOUVEAU MODÈLE
class UserChallengeAttempt(models.Model):
    """
    Modèle pour tracker les tentatives des utilisateurs sur les challenges
    """
    
    STATUS_CHOICES = [
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenge_attempts'
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='user_attempts'
    )
    
    # Statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Statut"
    )
    
    # Dates
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de début"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de complétion"
    )
    
    # Temps de résolution (en secondes)
    completion_time = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Temps de résolution (secondes)"
    )
    
    # XP gagné
    xp_earned = models.IntegerField(
        default=0,
        verbose_name="XP gagné"
    )
    
    # Nombre de tentatives
    attempts_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de tentatives"
    )
    
    class Meta:
        unique_together = ['user', 'challenge']
        ordering = ['-started_at']
        verbose_name = "Tentative de Challenge"
        verbose_name_plural = "Tentatives de Challenges"
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({self.get_status_display()})"
    
    def mark_as_completed(self, xp_earned=0):
        """Marque la tentative comme complétée et calcule le temps"""
        from django.utils import timezone
        
        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()
            
            # Calculer le temps de résolution
            time_diff = self.completed_at - self.started_at
            self.completion_time = int(time_diff.total_seconds())
            
            # Attribuer les XP
            self.xp_earned = xp_earned
            
            self.save()
            
            # Mettre à jour les stats de l'utilisateur
            if hasattr(self.user, 'update_stats'):
                self.user.update_stats()

class UserCodeSave(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_codes'
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='saved_codes'
    )
    code = models.TextField()
    saved_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'challenge')  # 1 sauvegarde par pair user/challenge

    def __str__(self):
        return f"{self.user.username} — {self.challenge.title}"
