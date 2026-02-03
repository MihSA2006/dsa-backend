# contests/models.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from accounts.models import User
from api.models import Challenge
from cloudinary.models import CloudinaryField

class Contest(models.Model):
    """
    Modèle pour les contests de programmation
    """
    TYPE_CHOICES = [
        ('individual', 'Individuel'),
        ('team', 'Équipe'),
    ]
    
    STATUS_CHOICES = [
        ('upcoming', 'À venir'),
        ('ongoing', 'En cours'),
        ('finished', 'Terminé'),
    ]
    
    title = models.CharField(max_length=200, verbose_name="Titre")
    description = models.TextField(
        verbose_name="Description",
        blank=True,
        null=True,
        help_text="Description détaillée du contest"
    )
    contest_img = CloudinaryField(
        # 'image',
        blank=True,
        null=True,
        verbose_name="Image du contest",
        help_text="Image de couverture du contest"
    )
    date_debut = models.DateTimeField(verbose_name="Date de début")
    date_fin = models.DateTimeField(verbose_name="Date de fin")
    statut = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='upcoming',
        verbose_name="Statut"
    )
    nombre_team = models.IntegerField(
        default=0,
        verbose_name="Nombre d'équipes"
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default='team',
        verbose_name="Type de contest"
    )
    challenges = models.ManyToManyField(
        Challenge,
        related_name='contests',
        verbose_name="Challenges"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_debut']
        verbose_name = "Contest"
        verbose_name_plural = "Contests"
    
    def __str__(self):
        return f"{self.title} ({self.get_statut_display()})"
    
    def clean(self):
        """Validation des contraintes"""
        # Date de fin > Date de début
        if self.date_fin <= self.date_debut:
            raise ValidationError("La date de fin doit être après la date de début")
        
        # Impossible de modifier dates si contest commencé
        if self.pk:
            old_contest = Contest.objects.get(pk=self.pk)
            if old_contest.has_started():
                if (old_contest.date_debut != self.date_debut or 
                    old_contest.date_fin != self.date_fin):
                    raise ValidationError(
                        "Impossible de modifier les dates d'un contest déjà commencé"
                    )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        self.update_status()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        """Suppression impossible si des équipes existent"""
        if self.teams.exists():
            raise ValidationError(
                "Impossible de supprimer un contest avec des équipes inscrites"
            )
        super().delete(*args, **kwargs)
    
    def update_status(self):
        """Met à jour automatiquement le statut du contest"""
        now = timezone.now()
        if now < self.date_debut:
            self.statut = 'upcoming'
        elif self.date_debut <= now <= self.date_fin:
            self.statut = 'ongoing'
        else:
            self.statut = 'finished'

    def has_started(self):
        if not self.date_debut:
            return False
        return timezone.now() >= self.date_debut

    def is_ongoing(self):
        if not self.date_debut or not self.date_fin:
            return False
        now = timezone.now()
        return self.date_debut <= now <= self.date_fin

    def is_finished(self):
        if not self.date_fin:
            return False
        return timezone.now() > self.date_fin
    
    def can_add_challenges(self):
        """Vérifie si on peut ajouter des challenges"""
        return not self.has_started()
    
    def update_team_count(self):
        """Met à jour le nombre d'équipes"""
        self.nombre_team = self.teams.count()
        self.save(update_fields=['nombre_team'])


class Team(models.Model):
    """
    Modèle pour les équipes participant à un contest
    """
    contest = models.ForeignKey(
        Contest,
        on_delete=models.CASCADE,
        related_name='teams',
        verbose_name="Contest"
    )
    nom = models.CharField(max_length=100, verbose_name="Nom de l'équipe")
    capitaine = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='capitaine_teams',
        verbose_name="Capitaine"
    )
    membres = models.ManyToManyField(
        User,
        related_name='team_memberships',
        verbose_name="Membres"
    )
    xp_total = models.IntegerField(default=0, verbose_name="XP total")
    temps_total = models.IntegerField(
        default=0,
        verbose_name="Temps total (secondes)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-xp_total', 'temps_total']
        verbose_name = "Équipe"
        verbose_name_plural = "Équipes"
        unique_together = [['contest', 'nom']]
    
    def __str__(self):
        return f"{self.nom} - {self.contest.title}"
    
    def clean(self):
        """Validation des contraintes"""
        # Création uniquement avant début du contest
        if not self.pk and self.contest.has_started():
            raise ValidationError(
                "Impossible de créer une équipe après le début du contest"
            )
        
        # Vérifier nombre de membres (1 à 5 max, capitaine compris)
        if self.pk:
            member_count = self.membres.count()
            if member_count > 5:
                raise ValidationError(
                    "Une équipe ne peut avoir que 5 membres maximum (capitaine compris)"
                )
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Ajouter automatiquement le capitaine aux membres
        if is_new:
            self.membres.add(self.capitaine)
            # Mettre à jour le nombre d'équipes du contest
            self.contest.update_team_count()
    
    # def delete(self, *args, **kwargs):
    #     contest = self.contest
    #     super().delete(*args, **kwargs)
    #     # Mettre à jour le nombre d'équipes
    #     contest.update_team_count()

    def delete(self, *args, **kwargs):
        """
        Suppression avec validation
        - Impossible de supprimer si le contest a commencé
        """
        # Vérifier si le contest a commencé
        if self.contest.has_started():
            raise ValidationError(
                "Impossible de supprimer l'équipe après le début du contest"
            )
        
        contest = self.contest
        super().delete(*args, **kwargs)
        # Mettre à jour le nombre d'équipes
        contest.update_team_count()
    
    def can_be_deleted(self):
        """Vérifie si l'équipe peut être supprimée"""
        if self.contest.has_started():
            return False, "Contest déjà commencé"
        
        return True, "OK"
    
    def can_add_member(self, user):
        """Vérifie si on peut ajouter un membre"""
        # Ne pas ajouter après le début du contest
        if self.contest.has_started():
            return False, "Contest déjà commencé"
        
        # Vérifier le nombre max de membres
        if self.membres.count() >= 5:
            return False, "Équipe complète (5 membres maximum)"
        
        # Vérifier que l'utilisateur n'est pas déjà dans une autre équipe
        if Team.objects.filter(
            contest=self.contest,
            membres=user
        ).exists():
            return False, "L'utilisateur est déjà dans une équipe pour ce contest"
        
        return True, "OK"
    
    def add_member(self, user, requester):
        """Ajoute un membre à l'équipe"""
        # Seul le capitaine peut ajouter
        if requester != self.capitaine:
            raise ValidationError("Seul le capitaine peut ajouter des membres")
        
        can_add, message = self.can_add_member(user)
        if not can_add:
            raise ValidationError(message)
        
        self.membres.add(user)
    
    def remove_member(self, user, requester):
        """Retire un membre de l'équipe"""
        # Seul le capitaine peut retirer
        if requester != self.capitaine:
            raise ValidationError("Seul le capitaine peut retirer des membres")
        
        # Ne pas retirer après le début du contest
        if self.contest.has_started():
            raise ValidationError("Impossible de retirer un membre après le début du contest")
        
        # Ne pas retirer le capitaine
        if user == self.capitaine:
            raise ValidationError("Le capitaine ne peut pas être retiré de l'équipe")
        
        self.membres.remove(user)
    
    def leave_team(self, user):
        """Un membre quitte l'équipe"""
        # Impossible de quitter si contest commencé
        if self.contest.has_started():
            raise ValidationError("Impossible de quitter l'équipe après le début du contest")
        
        # Le capitaine ne peut pas quitter
        if user == self.capitaine:
            raise ValidationError("Le capitaine ne peut pas quitter l'équipe")
        
        self.membres.remove(user)
    
    def calculate_stats(self):
        """Calcule les statistiques de l'équipe"""
        submissions = self.submissions.filter(
            challenge__in=self.contest.challenges.all()
        )
        
        self.xp_total = sum(sub.xp_earned for sub in submissions)
        self.temps_total = sum(sub.temps_soumission for sub in submissions)
        self.save(update_fields=['xp_total', 'temps_total'])

class TeamInvitation(models.Model):
    """
    Modèle pour les invitations d'équipe
    """
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('accepted', 'Acceptée'),
        ('declined', 'Refusée'),
        ('expired', 'Expirée'),
    ]
    
    team = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='invitations',
        verbose_name="Équipe"
    )
    inviter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_invitations',
        verbose_name="Invité par"
    )
    invitee = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_invitations',
        verbose_name="Invité"
    )
    token = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Token de validation"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(verbose_name="Expire le")
    responded_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Invitation"
        verbose_name_plural = "Invitations"
        unique_together = [['team', 'invitee', 'status']]
    
    def __str__(self):
        return f"Invitation de {self.invitee.username} pour {self.team.nom}"
    
    def is_valid(self):
        """Vérifie si l'invitation est encore valide"""
        return (
            self.status == 'pending' and 
            timezone.now() < self.expires_at
        )
    
    def accept(self):
        """Accepte l'invitation"""
        if not self.is_valid():
            raise ValidationError("Cette invitation n'est plus valide")
        
        can_add, message = self.team.can_add_member(self.invitee)
        if not can_add:
            raise ValidationError(message)
        
        self.status = 'accepted'
        self.responded_at = timezone.now()
        self.save()
        
        self.team.membres.add(self.invitee)
        return True
    
    def decline(self):
        """Refuse l'invitation"""
        if self.status != 'pending':
            raise ValidationError("Cette invitation a déjà été traitée")
        
        self.status = 'declined'
        self.responded_at = timezone.now()
        self.save()
        return True
    
    def save(self, *args, **kwargs):
        # Générer un token unique si nouveau
        if not self.token:
            import secrets
            self.token = secrets.token_urlsafe(32)
        
        # Définir la date d'expiration (7 jours par défaut)
        if not self.expires_at:
            from datetime import timedelta
            self.expires_at = timezone.now() + timedelta(days=7)
        
        super().save(*args, **kwargs)


class ContestSubmission(models.Model):
    """
    Modèle pour les soumissions dans un contest
    """
    equipe = models.ForeignKey(
        Team,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name="Équipe"
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='contest_submissions',
        verbose_name="Challenge"
    )
    submitted_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contest_submissions',
        verbose_name="Soumis par"
    )
    code_soumis = models.TextField(verbose_name="Code soumis")
    xp_earned = models.IntegerField(default=0, verbose_name="XP obtenue")
    temps_soumission = models.IntegerField(
        default=0,
        verbose_name="Temps de soumission (secondes)"
    )
    tests_reussis = models.IntegerField(
        default=0,
        verbose_name="Nombre de tests réussis"
    )
    tests_total = models.IntegerField(
        default=0,
        verbose_name="Nombre total de tests"
    )
    
    submitted_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Soumission Contest"
        verbose_name_plural = "Soumissions Contest"
        unique_together = [['equipe', 'challenge']]
    
    def __str__(self):
        return f"{self.equipe.nom} - {self.challenge.title}"
    
    def clean(self):
        """Validation des contraintes"""
        contest = self.equipe.contest
        
        # Soumission uniquement pendant la période du contest
        if not contest.is_ongoing():
            raise ValidationError(
                "Les soumissions sont uniquement autorisées pendant la période du contest"
            )
        
        # Vérifier que le challenge fait partie du contest
        if not contest.challenges.filter(id=self.challenge.id).exists():
            raise ValidationError(
                "Ce challenge ne fait pas partie du contest"
            )
        
        # Seuls les membres peuvent soumettre
        if not self.equipe.membres.filter(id=self.submitted_by.id).exists():
            raise ValidationError(
                "Seuls les membres de l'équipe peuvent soumettre"
            )
        
        # Une seule soumission par équipe par challenge
        if self.pk is None:
            if ContestSubmission.objects.filter(
                equipe=self.equipe,
                challenge=self.challenge
            ).exists():
                raise ValidationError(
                    "Une soumission existe déjà pour ce challenge"
                )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
        # Recalculer les stats de l'équipe
        self.equipe.calculate_stats()