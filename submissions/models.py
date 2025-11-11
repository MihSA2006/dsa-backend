# submissions/models.py

from django.db import models
from django.conf import settings
from api.models import Challenge
from django.utils import timezone


class ChallengeAttempt(models.Model):
    """
    Modèle pour enregistrer les tentatives de challenges par utilisateur
    """
    
    STATUS_CHOICES = [
        ('in_progress', 'En cours'),
        ('completed', 'Terminé'),
        ('abandoned', 'Abandonné'),
    ]
    
    # Relations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='challenge_attempts',
        verbose_name="Utilisateur"
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='attempts',
        verbose_name="Challenge"
    )
    
    # Dates
    started_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de début"
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin"
    )
    
    # Scores et statut
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress',
        verbose_name="Statut"
    )
    points_earned = models.IntegerField(
        default=0,
        verbose_name="Points obtenus"
    )
    total_points = models.IntegerField(
        default=0,
        verbose_name="Points totaux possibles"
    )
    
    # Temps d'exécution (en secondes)
    total_time_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Temps total (secondes)"
    )
    
    # Nombre de tentatives
    submission_count = models.IntegerField(
        default=0,
        verbose_name="Nombre de soumissions"
    )
    
    # Dernier code soumis (optionnel)
    last_submitted_code = models.TextField(
        blank=True,
        verbose_name="Dernier code soumis"
    )
    
    class Meta:
        verbose_name = "Tentative de Challenge"
        verbose_name_plural = "Tentatives de Challenges"
        ordering = ['-started_at']
        unique_together = ['user', 'challenge']
        indexes = [
            models.Index(fields=['challenge', '-points_earned', 'total_time_seconds']),
            models.Index(fields=['user', 'status']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.title} ({self.get_status_display()})"
    
    def calculate_time_taken(self):
        """Calcule le temps pris pour terminer le challenge"""
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            return delta.total_seconds()
        return None
    
    def get_success_rate(self):
        """Retourne le taux de réussite en pourcentage"""
        if self.total_points == 0:
            return 0
        return (self.points_earned / self.total_points) * 100
    
    def get_rank_in_challenge(self):
        """Retourne le rang de l'utilisateur pour ce challenge"""
        # Rang basé sur points puis temps
        better_attempts = ChallengeAttempt.objects.filter(
            challenge=self.challenge,
            status='completed'
        ).filter(
            models.Q(points_earned__gt=self.points_earned) |
            models.Q(
                points_earned=self.points_earned,
                total_time_seconds__lt=self.total_time_seconds
            )
        ).count()
        
        return better_attempts + 1


class Submission(models.Model):
    """
    Modèle pour enregistrer chaque soumission de code
    """
    
    # Relations
    attempt = models.ForeignKey(
        ChallengeAttempt,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name="Tentative"
    )
    
    # Code soumis
    code = models.TextField(verbose_name="Code soumis")
    
    # Résultats
    is_correct = models.BooleanField(
        default=False,
        verbose_name="Solution correcte"
    )
    points_earned = models.IntegerField(
        default=0,
        verbose_name="Points obtenus"
    )
    passed_tests = models.IntegerField(
        default=0,
        verbose_name="Tests réussis"
    )
    total_tests = models.IntegerField(
        default=0,
        verbose_name="Total de tests"
    )
    
    # Temps d'exécution
    execution_time = models.FloatField(
        default=0,
        verbose_name="Temps d'exécution (secondes)"
    )
    
    # Erreurs (si échec)
    error_message = models.TextField(
        blank=True,
        verbose_name="Message d'erreur"
    )
    
    # Métadonnées
    submitted_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de soumission"
    )
    
    class Meta:
        verbose_name = "Soumission"
        verbose_name_plural = "Soumissions"
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['attempt', '-submitted_at']),
        ]
    
    def __str__(self):
        status = "✓" if self.is_correct else "✗"
        return f"{status} {self.attempt.user.username} - {self.attempt.challenge.title}"


class ChallengeRanking(models.Model):
    """
    Modèle pour le classement général des utilisateurs
    (peut être mis à jour périodiquement)
    """
    
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='ranking',
        verbose_name="Utilisateur"
    )
    
    # Statistiques globales
    total_points = models.IntegerField(
        default=0,
        verbose_name="Points totaux"
    )
    challenges_completed = models.IntegerField(
        default=0,
        verbose_name="Challenges terminés"
    )
    challenges_attempted = models.IntegerField(
        default=0,
        verbose_name="Challenges tentés"
    )
    
    # Classement
    global_rank = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="Rang global"
    )
    
    # Métadonnées
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name="Dernière mise à jour"
    )
    
    class Meta:
        verbose_name = "Classement"
        verbose_name_plural = "Classements"
        ordering = ['-total_points', 'challenges_completed']
    
    def __str__(self):
        return f"{self.user.username} - {self.total_points} pts"
    
    def update_stats(self):
        """Met à jour les statistiques de l'utilisateur"""
        completed = ChallengeAttempt.objects.filter(
            user=self.user,
            status='completed'
        )
        
        self.challenges_completed = completed.count()
        self.total_points = sum(attempt.points_earned for attempt in completed)
        self.challenges_attempted = ChallengeAttempt.objects.filter(
            user=self.user
        ).count()
        self.save()