# api/admin.py

from django.contrib import admin
from .models import Challenge, TestCase, UserChallengeAttempt


class TestCaseInline(admin.TabularInline):
    """Affiche les test cases dans la page du challenge"""
    model = TestCase
    extra = 1
    fields = ['order', 'input_file', 'output_file', 'is_sample']


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ['title', 'difficulty', 'xp_reward', 'is_active', 'created_at']
    list_filter = ['difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'slug']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [TestCaseInline]
    
    fieldsets = (
        ('Informations de base', {
            'fields': ('title', 'slug', 'difficulty', 'is_active')
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