# api/models.py

from django.db import models
from django.core.validators import FileExtensionValidator
import os

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
    description_file = models.FileField(
        upload_to='challenges/descriptions/',
        validators=[FileExtensionValidator(allowed_extensions=['txt', 'md'])],
        verbose_name="Fichier description (markdown)"
    )
    
    # Template initial
    template_file = models.FileField(
        upload_to='challenges/templates/',
        validators=[FileExtensionValidator(allowed_extensions=['py'])],
        verbose_name="Fichier template (.py)"
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
        return f"{self.title} ({self.get_difficulty_display()})"
    
    def get_description(self):
        """Lit et retourne le contenu du fichier description"""
        try:
            with open(self.description_file.path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def get_template(self):
        """Lit et retourne le contenu du fichier template"""
        try:
            with open(self.template_file.path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""


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
    input_file = models.FileField(
        upload_to='challenges/inputs/',
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        verbose_name="Fichier input (.txt)"
    )
    
    output_file = models.FileField(
        upload_to='challenges/outputs/',
        validators=[FileExtensionValidator(allowed_extensions=['txt'])],
        verbose_name="Fichier output (.txt)"
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
        """Lit et retourne le contenu du fichier input"""
        try:
            with open(self.input_file.path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""
    
    def get_output(self):
        """Lit et retourne le contenu du fichier output"""
        try:
            with open(self.output_file.path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception:
            return ""