# contests/admin.py

from django.contrib import admin
from django.utils.html import format_html
from .models import Contest, Team, ContestSubmission


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    """Administration des contests"""
    
    list_display = [
        'title', 'type', 'statut_badge', 'date_debut',
        'date_fin', 'nombre_team', 'challenges_count'
    ]
    list_filter = ['statut', 'type', 'date_debut']
    search_fields = ['title']
    filter_horizontal = ['challenges']
    readonly_fields = ['nombre_team', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'type')
        }),
        ('Dates', {
            'fields': ('date_debut', 'date_fin', 'statut')
        }),
        ('Challenges', {
            'fields': ('challenges',)
        }),
        ('Statistiques', {
            'fields': ('nombre_team',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def statut_badge(self, obj):
        """Badge coloré pour le statut"""
        colors = {
            'upcoming': '#FFA500',
            'ongoing': '#28a745',
            'finished': '#6c757d'
        }
        color = colors.get(obj.statut, '#000')
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_statut_display()
        )
    statut_badge.short_description = 'Statut'
    
    def challenges_count(self, obj):
        """Nombre de challenges"""
        return obj.challenges.count()
    challenges_count.short_description = 'Challenges'
    
    def save_model(self, request, obj, form, change):
        """Mise à jour du statut avant sauvegarde"""
        obj.update_status()
        super().save_model(request, obj, form, change)


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Administration des équipes"""
    
    list_display = [
        'nom', 'contest', 'capitaine', 'membres_count',
        'xp_total', 'temps_total_formatted'
    ]
    list_filter = ['contest', 'created_at']
    search_fields = ['nom', 'capitaine__username']
    filter_horizontal = ['membres']
    readonly_fields = ['xp_total', 'temps_total', 'created_at']
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('contest', 'nom', 'capitaine')
        }),
        ('Membres', {
            'fields': ('membres',)
        }),
        ('Statistiques', {
            'fields': ('xp_total', 'temps_total'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def membres_count(self, obj):
        """Nombre de membres"""
        return obj.membres.count()
    membres_count.short_description = 'Membres'
    
    def temps_total_formatted(self, obj):
        """Temps formaté en heures:minutes:secondes"""
        hours = obj.temps_total // 3600
        minutes = (obj.temps_total % 3600) // 60
        seconds = obj.temps_total % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    temps_total_formatted.short_description = 'Temps total'


@admin.register(ContestSubmission)
class ContestSubmissionAdmin(admin.ModelAdmin):
    """Administration des soumissions"""
    
    list_display = [
        'equipe', 'challenge', 'submitted_by', 'success_badge',
        'xp_earned', 'submitted_at'
    ]
    list_filter = ['submitted_at', 'equipe__contest', 'challenge']
    search_fields = [
        'equipe__nom', 'challenge__title', 'submitted_by__username'
    ]
    readonly_fields = [
        'equipe', 'challenge', 'submitted_by', 'code_soumis',
        'xp_earned', 'temps_soumission', 'tests_reussis',
        'tests_total', 'submitted_at'
    ]
    
    fieldsets = (
        ('Informations', {
            'fields': ('equipe', 'challenge', 'submitted_by')
        }),
        ('Résultats', {
            'fields': (
                'xp_earned', 'temps_soumission',
                'tests_reussis', 'tests_total'
            )
        }),
        ('Code', {
            'fields': ('code_soumis',),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('submitted_at',),
            'classes': ('collapse',)
        }),
    )
    
    def success_badge(self, obj):
        """Badge pour le taux de réussite"""
        if obj.tests_total == 0:
            return '-'
        
        rate = (obj.tests_reussis / obj.tests_total) * 100
        color = '#28a745' if rate == 100 else '#FFA500' if rate >= 50 else '#dc3545'
        
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 10px; border-radius: 3px;">{}/{} ({}%)</span>',
            color,
            obj.tests_reussis,
            obj.tests_total,
            round(rate, 1)
        )
    success_badge.short_description = 'Réussite'
    
    def has_add_permission(self, request):
        """Désactiver l'ajout manuel"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Désactiver la modification"""
        return False