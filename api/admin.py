# api/admin.py

from django.contrib import admin
from .models import Challenge, TestCase, UserChallengeAttempt, Team, TeamInvitation


class TestCaseInline(admin.TabularInline):
    """Affiche les test cases dans la page du challenge"""
    model = TestCase
    extra = 1
    fields = ['order', 'input_file', 'output_file', 'is_sample']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'xp_reward', 'is_active', 'created_at', 'participants_count']
    list_filter = ['difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TestCaseInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'slug', 'difficulty', 'is_active', 'participants_count')
        }),
        ('Récompense', {
            'fields': ('xp_reward',)
        }),
        ('Fichiers', {
            'fields': ('description_file', 'template_file')
        }),
    )


@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['challenge', 'order', 'is_sample']
    list_filter = ['challenge', 'is_sample']
    ordering = ['challenge', 'order']


@admin.register(UserChallengeAttempt)
class UserChallengeAttemptAdmin(admin.ModelAdmin):
    list_display = ['user', 'challenge', 'status', 'xp_earned', 'started_at', 'completed_at', 'attempts_count']
    list_filter = ['status', 'started_at', 'completed_at']
    search_fields = ['user__username', 'challenge__title']
    readonly_fields = ['started_at', 'completed_at', 'completion_time', 'xp_earned']
    
    fieldsets = (
        ('Informations', {
            'fields': ('user', 'challenge', 'status')
        }),
        ('Dates', {
            'fields': ('started_at', 'completed_at', 'completion_time')
        }),
        ('Performance', {
            'fields': ('xp_earned', 'attempts_count')
        }),
    )





@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'challenge', 'leader', 'created_at')
    list_filter = ('challenge', 'created_at')
    search_fields = ('name', 'leader__username', 'challenge__title')
    # ❌ Supprimer ou commenter cette ligne :
    # filter_horizontal = ('members',)
    autocomplete_fields = ('leader', 'challenge')


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = ('team', 'invited_user', 'invited_by', 'is_accepted', 'created_at')
    list_filter = ('is_accepted', 'created_at', 'team__challenge')
    search_fields = ('team__name', 'invited_user__username', 'invited_by__username', 'token')
    readonly_fields = ('token', 'created_at')

    autocomplete_fields = ('team', 'invited_user', 'invited_by')
    ordering = ('-created_at',)
