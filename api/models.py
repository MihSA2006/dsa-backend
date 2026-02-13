# api/models.py

from django.db import models
from django.conf import settings
from cloudinary.models import CloudinaryField

import requests


# ============================================================
# ✅ Fonction utilitaire : lire un fichier texte Cloudinary UTF-8
# ============================================================

def read_cloudinary_text(file_field):
    """
    Lit correctement un fichier texte uploadé sur Cloudinary
    (UTF-8 + accents + emojis) et normalise les retours à la ligne.
    """
    try:
        if not file_field:
            return ""

        response = requests.get(file_field.url, timeout=10)

        if response.status_code == 200:
            # ✅ Décodage manuel UTF-8 (corrige le bug : ð§© RÃ¨gles)
            text = response.content.decode("utf-8")

            # ✅ Normaliser les sauts de ligne
            return text.replace("\r\n", "\n").replace("\r", "\n")

        return ""

    except Exception:
        return ""


# ============================================================
# ✅ MODEL : Challenge
# ============================================================

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

    # Description (markdown)
    description_file = CloudinaryField(
        resource_type='raw',
        blank=True,
        null=True,
        verbose_name="Fichier description (markdown)"
    )

    # Template initial
    template_file = CloudinaryField(
        resource_type='raw',
        blank=True,
        null=True,
        verbose_name="Fichier template (.py)"
    )

    # XP Reward
    xp_reward = models.IntegerField(default=100, verbose_name="Points XP")

    # Nombre de participants
    participants_count = models.IntegerField(default=0)

    xp_required = models.IntegerField(
        default=0,
        verbose_name="XP minimum requis"
    )

    # PDF optionnel
    description_pdf = CloudinaryField(
        resource_type='raw',
        blank=True,
        null=True,
        verbose_name="Description PDF"
    )

    # Image optionnelle
    description_img = CloudinaryField(
        blank=True,
        null=True,
        verbose_name="Image de description"
    )

    # Métadonnées
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Challenge"
        verbose_name_plural = "Challenges"

    def __str__(self):
        return f"{self.title} ({self.get_difficulty_display()})"

    # ✅ Lecture UTF-8 correcte
    def get_description(self):
        return read_cloudinary_text(self.description_file)

    def get_template(self):
        return read_cloudinary_text(self.template_file)

    def update_participants_count(self):
        self.participants_count = UserChallengeAttempt.objects.filter(
            challenge=self
        ).count()
        self.save(update_fields=['participants_count'])

    def get_completion_rate(self):
        if self.participants_count == 0:
            return 0

        completed = UserChallengeAttempt.objects.filter(
            challenge=self,
            status='completed'
        ).count()

        return round((completed / self.participants_count) * 100, 2)


# ============================================================
# ✅ MODEL : TestCase
# ============================================================

class TestCase(models.Model):
    """
    Cas de test pour un challenge
    """

    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='test_cases'
    )

    input_file = CloudinaryField(
        resource_type='raw',
        blank=True,
        null=True,
        verbose_name="Fichier input (.txt)"
    )

    output_file = CloudinaryField(
        resource_type='raw',
        blank=True,
        null=True,
        verbose_name="Fichier output (.txt)"
    )

    order = models.IntegerField(default=0)
    is_sample = models.BooleanField(default=False)

    class Meta:
        ordering = ['order']
        verbose_name = "Test Case"
        verbose_name_plural = "Test Cases"

    def __str__(self):
        return f"Test {self.order} - {self.challenge.title}"

    # ✅ Lecture UTF-8 correcte
    def get_input(self):
        return read_cloudinary_text(self.input_file)

    def get_output(self):
        return read_cloudinary_text(self.output_file)


# ============================================================
# ✅ MODEL : UserChallengeAttempt
# ============================================================

class UserChallengeAttempt(models.Model):
    """
    Suivi des tentatives utilisateurs
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

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='in_progress'
    )

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    completion_time = models.IntegerField(null=True, blank=True)

    xp_earned = models.IntegerField(default=0)
    attempts_count = models.IntegerField(default=0)

    class Meta:
        unique_together = ['user', 'challenge']
        ordering = ['-started_at']

    def __str__(self):
        return f"{self.user.username} - {self.challenge.title}"

    def mark_as_completed(self, xp_earned=0):
        from django.utils import timezone

        if self.status != 'completed':
            self.status = 'completed'
            self.completed_at = timezone.now()

            # Calcul du temps
            diff = self.completed_at - self.started_at
            self.completion_time = int(diff.total_seconds())

            self.xp_earned = xp_earned
            self.save()

            if hasattr(self.user, 'update_stats'):
                self.user.update_stats()


# ============================================================
# ✅ MODEL : UserCodeSave
# ============================================================

class UserCodeSave(models.Model):
    """
    Sauvegarde du code utilisateur
    """

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
        unique_together = ('user', 'challenge')

    def __str__(self):
        return f"{self.user.username} — {self.challenge.title}"
