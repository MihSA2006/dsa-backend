# submissions/admin.py

from django.contrib import admin
from .models import ChallengeAttempt, Submission, ChallengeRanking


@admin.register(ChallengeAttempt)
class ChallengeAttemptAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'challenge', 'status', 'points_earned',
        'total_points', 'started_at', 'completed_at'
    ]
    list_filter = ['status', 'challenge', 'started_at']
    search_fields = ['user__username', 'challenge__title']
    readonly_fields = ['started_at', 'submission_count']
    
    fieldsets = (
        ('Informations', {
            'fields': ('user', 'challenge', 'status')
        }),
        ('Scores', {
            'fields': ('points_earned', 'total_points', 'submission_count')
        }),
        ('Dates', {
            'fields': ('started_at', 'completed_at', 'total_time_seconds')
        }),
        ('Code', {
            'fields': ('last_submitted_code',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = [
        'attempt', 'is_correct', 'points_earned',
        'passed_tests', 'total_tests', 'submitted_at'
    ]
    list_filter = ['is_correct', 'submitted_at']
    search_fields = ['attempt__user__username', 'attempt__challenge__title']
    readonly_fields = ['submitted_at']


@admin.register(ChallengeRanking)
class ChallengeRankingAdmin(admin.ModelAdmin):
    list_display = [
        'global_rank', 'user', 'total_points',
        'challenges_completed', 'challenges_attempted'
    ]
    list_filter = ['challenges_completed']
    search_fields = ['user__username']
    readonly_fields = ['last_updated']
    
    actions = ['update_all_rankings']
    
    def update_all_rankings(self, request, queryset):
        for ranking in queryset:
            ranking.update_stats()
        self.message_user(request, "Classements mis à jour avec succès")
    update_all_rankings.short_description = "Mettre à jour les classements"