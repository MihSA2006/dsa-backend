from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Contest, Team, ContestSubmission, TeamInvitation


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    """Administration des contests"""
    
    list_display = [
        'title', 
        'statut_badge', 
        'type', 
        'date_debut', 
        'date_fin',
        'nombre_team',
        'challenges_count',
        'created_at'
    ]
    
    list_filter = [
        'statut',
        'type',
        'date_debut',
        'date_fin'
    ]
    
    search_fields = ['title']
    
    filter_horizontal = ['challenges']
    
    readonly_fields = [
        'nombre_team',
        'statut',
        'created_at',
        'updated_at',
        'status_info'
    ]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('title', 'type')
        }),
        ('Dates et statut', {
            'fields': ('date_debut', 'date_fin', 'statut', 'status_info')
        }),
        ('Challenges', {
            'fields': ('challenges',)
        }),
        ('Statistiques', {
            'fields': ('nombre_team',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'upcoming': '#FFA500',  # Orange
            'ongoing': '#28A745',   # Vert
            'finished': '#6C757D'   # Gris
        }
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}</span>',
            colors.get(obj.statut, '#000'),
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def challenges_count(self, obj):
        """Nombre de challenges"""
        count = obj.challenges.count()
        return format_html(
            '<span style="font-weight: bold;">{}</span>',
            count
        )
    challenges_count.short_description = 'Challenges'
    
    def status_info(self, obj):
        """Informations détaillées sur le statut"""
        html = f"""
        <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
            <p><strong>En cours:</strong> {'✅ Oui' if obj.is_ongoing() else '❌ Non'}</p>
            <p><strong>Terminé:</strong> {'✅ Oui' if obj.is_finished() else '❌ Non'}</p>
            <p><strong>Commencé:</strong> {'✅ Oui' if obj.has_started() else '❌ Non'}</p>
            <p><strong>Peut ajouter des challenges:</strong> {'✅ Oui' if obj.can_add_challenges() else '❌ Non'}</p>
        </div>
        """
        return mark_safe(html)
    status_info.short_description = 'État du contest'
    
    def save_model(self, request, obj, form, change):
        """Mise à jour automatique du statut avant sauvegarde"""
        obj.update_status()
        super().save_model(request, obj, form, change)


class ContestSubmissionInline(admin.TabularInline):
    """Inline pour les soumissions dans une équipe"""
    model = ContestSubmission
    extra = 0
    readonly_fields = [
        'challenge',
        'submitted_by',
        'xp_earned',
        'temps_soumission',
        'tests_reussis',
        'tests_total',
        'submitted_at'
    ]
    fields = readonly_fields
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Administration des équipes"""
    
    list_display = [
        'nom',
        'contest_link',
        'capitaine_link',
        'membres_count',
        'xp_total',
        'temps_total',
        'rank_badge',
        'created_at'
    ]
    
    list_filter = [
        'contest',
        'created_at'
    ]
    
    search_fields = [
        'nom',
        'capitaine__username',
        'capitaine__nom',
        'capitaine__prenom'
    ]
    
    filter_horizontal = ['membres']
    
    readonly_fields = [
        'xp_total',
        'temps_total',
        'created_at',
        'team_stats',
        'rank_info'
    ]
    
    fieldsets = (
        ('Informations', {
            'fields': ('contest', 'nom', 'capitaine')
        }),
        ('Membres', {
            'fields': ('membres',)
        }),
        ('Statistiques', {
            'fields': ('xp_total', 'temps_total', 'rank_info', 'team_stats')
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [ContestSubmissionInline]
    
    def contest_link(self, obj):
        """Lien vers le contest"""
        url = reverse('admin:contests_contest_change', args=[obj.contest.id])
        return format_html('<a href="{}">{}</a>', url, obj.contest.title)
    contest_link.short_description = 'Contest'
    
    def capitaine_link(self, obj):
        """Lien vers le capitaine"""
        url = reverse('admin:accounts_user_change', args=[obj.capitaine.id])
        return format_html('<a href="{}">{}</a>', url, obj.capitaine.username)
    capitaine_link.short_description = 'Capitaine'
    
    def membres_count(self, obj):
        """Nombre de membres"""
        count = obj.membres.count()
        return format_html(
            '<span style="font-weight: bold;">{}/5</span>',
            count
        )
    membres_count.short_description = 'Membres'
    
    def rank_badge(self, obj):
        """Badge du rang"""
        contest = obj.contest
        teams = list(contest.teams.all())
        try:
            rank = teams.index(obj) + 1
            color = '#FFD700' if rank == 1 else '#C0C0C0' if rank == 2 else '#CD7F32' if rank == 3 else '#6C757D'
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 10px; '
                'border-radius: 50%; font-weight: bold;">{}</span>',
                color,
                rank
            )
        except ValueError:
            return '-'
    rank_badge.short_description = 'Rang'
    
    def rank_info(self, obj):
        """Informations sur le rang"""
        contest = obj.contest
        teams = list(contest.teams.all())
        try:
            rank = teams.index(obj) + 1
            total = len(teams)
            return format_html(
                '<strong>Rang {}/{}</strong>',
                rank, total
            )
        except ValueError:
            return '-'
    rank_info.short_description = 'Classement'
    
    def team_stats(self, obj):
        """Statistiques détaillées de l'équipe"""
        submissions = obj.submissions.all()
        total_submissions = submissions.count()
        
        html = f"""
        <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
            <h3>Statistiques</h3>
            <p><strong>Soumissions:</strong> {total_submissions}</p>
            <p><strong>XP Total:</strong> {obj.xp_total}</p>
            <p><strong>Temps Total:</strong> {obj.temps_total}s ({obj.temps_total // 60} min)</p>
            <p><strong>Membres:</strong> {obj.membres.count()}/5</p>
        </div>
        """
        return mark_safe(html)
    team_stats.short_description = 'Statistiques détaillées'


@admin.register(ContestSubmission)
class ContestSubmissionAdmin(admin.ModelAdmin):
    """Administration des soumissions de contest"""
    
    list_display = [
        'id',
        'equipe_link',
        'challenge_link',
        'submitted_by_link',
        'success_badge',
        'xp_earned',
        'temps_display',
        'submitted_at'
    ]
    
    list_filter = [
        'equipe__contest',
        'challenge',
        'submitted_at'
    ]
    
    search_fields = [
        'equipe__nom',
        'challenge__title',
        'submitted_by__username'
    ]
    
    readonly_fields = [
        'equipe',
        'challenge',
        'submitted_by',
        'xp_earned',
        'temps_soumission',
        'tests_reussis',
        'tests_total',
        'submitted_at',
        'code_preview',
        'submission_stats'
    ]
    
    fieldsets = (
        ('Informations', {
            'fields': ('equipe', 'challenge', 'submitted_by', 'submitted_at')
        }),
        ('Résultats', {
            'fields': (
                'tests_reussis',
                'tests_total',
                'xp_earned',
                'temps_soumission',
                'submission_stats'
            )
        }),
        ('Code', {
            'fields': ('code_preview',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """Pas de création manuelle"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Lecture seule"""
        return False
    
    def equipe_link(self, obj):
        """Lien vers l'équipe"""
        url = reverse('admin:contests_team_change', args=[obj.equipe.id])
        return format_html('<a href="{}">{}</a>', url, obj.equipe.nom)
    equipe_link.short_description = 'Équipe'
    
    def challenge_link(self, obj):
        """Lien vers le challenge"""
        url = reverse('admin:api_challenge_change', args=[obj.challenge.id])
        return format_html('<a href="{}">{}</a>', url, obj.challenge.title)
    challenge_link.short_description = 'Challenge'
    
    def submitted_by_link(self, obj):
        """Lien vers l'utilisateur"""
        url = reverse('admin:accounts_user_change', args=[obj.submitted_by.id])
        return format_html('<a href="{}">{}</a>', url, obj.submitted_by.username)
    submitted_by_link.short_description = 'Soumis par'
    
    def success_badge(self, obj):
        """Badge de réussite"""
        success_rate = (obj.tests_reussis / obj.tests_total * 100) if obj.tests_total > 0 else 0
        color = '#28A745' if success_rate == 100 else '#FFA500' if success_rate >= 50 else '#DC3545'
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; '
            'border-radius: 3px; font-weight: bold;">{}/{} ({}%)</span>',
            color,
            obj.tests_reussis,
            obj.tests_total,
            round(success_rate, 1)
        )
    success_badge.short_description = 'Tests'
    
    def temps_display(self, obj):
        """Affichage formaté du temps"""
        minutes = obj.temps_soumission // 60
        seconds = obj.temps_soumission % 60
        return f"{minutes}m {seconds}s"
    temps_display.short_description = 'Temps'
    
    def code_preview(self, obj):
        """Aperçu du code soumis"""
        code = obj.code_soumis[:500] + '...' if len(obj.code_soumis) > 500 else obj.code_soumis
        return format_html(
            '<pre style="background: #f8f9fa; padding: 10px; border-radius: 5px; '
            'overflow-x: auto;">{}</pre>',
            code
        )
    code_preview.short_description = 'Code soumis'
    
    def submission_stats(self, obj):
        """Statistiques de la soumission"""
        success_rate = (obj.tests_reussis / obj.tests_total * 100) if obj.tests_total > 0 else 0
        xp_rate = (obj.xp_earned / obj.challenge.xp_reward * 100) if obj.challenge.xp_reward > 0 else 0
        
        html = f"""
        <div style="padding: 10px; background: #f8f9fa; border-radius: 5px;">
            <h3>Détails</h3>
            <p><strong>Taux de réussite:</strong> {success_rate:.1f}%</p>
            <p><strong>XP obtenue:</strong> {obj.xp_earned}/{obj.challenge.xp_reward} ({xp_rate:.1f}%)</p>
            <p><strong>Tests réussis:</strong> {obj.tests_reussis}/{obj.tests_total}</p>
            <p><strong>Temps:</strong> {obj.temps_soumission}s ({obj.temps_soumission // 60}m {obj.temps_soumission % 60}s)</p>
        </div>
        """
        return mark_safe(html)
    submission_stats.short_description = 'Statistiques'


admin.site.register(TeamInvitation)