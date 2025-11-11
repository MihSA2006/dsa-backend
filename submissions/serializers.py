# submissions/serializers.py

from rest_framework import serializers
from .models import ChallengeAttempt, Submission, ChallengeRanking
from api.serializers import ChallengeListSerializer


class SubmissionSerializer(serializers.ModelSerializer):
    """Serializer pour les soumissions individuelles"""
    
    class Meta:
        model = Submission
        fields = [
            'id', 'code', 'is_correct', 'points_earned',
            'passed_tests', 'total_tests', 'execution_time',
            'error_message', 'submitted_at'
        ]
        read_only_fields = [
            'id', 'is_correct', 'points_earned', 'passed_tests',
            'total_tests', 'execution_time', 'error_message', 'submitted_at'
        ]


class ChallengeAttemptSerializer(serializers.ModelSerializer):
    """Serializer pour les tentatives de challenge"""
    
    challenge_title = serializers.CharField(source='challenge.title', read_only=True)
    challenge_difficulty = serializers.CharField(source='challenge.difficulty', read_only=True)
    success_rate = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    submissions = SubmissionSerializer(many=True, read_only=True)
    
    class Meta:
        model = ChallengeAttempt
        fields = [
            'id', 'challenge', 'challenge_title', 'challenge_difficulty',
            'started_at', 'completed_at', 'status', 'points_earned',
            'total_points', 'success_rate', 'rank', 'time_taken',
            'submission_count', 'last_submitted_code', 'submissions'
        ]
        read_only_fields = [
            'id', 'started_at', 'points_earned', 'total_points',
            'submission_count', 'last_submitted_code'
        ]
    
    def get_success_rate(self, obj):
        return obj.get_success_rate()
    
    def get_rank(self, obj):
        if obj.status == 'completed':
            return obj.get_rank_in_challenge()
        return None
    
    def get_time_taken(self, obj):
        return obj.calculate_time_taken()


class ChallengeLeaderboardSerializer(serializers.ModelSerializer):
    """Serializer pour le classement d'un challenge"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    user_nom = serializers.CharField(source='user.nom', read_only=True)
    user_prenom = serializers.CharField(source='user.prenom', read_only=True)
    rank = serializers.SerializerMethodField()
    time_taken = serializers.SerializerMethodField()
    
    class Meta:
        model = ChallengeAttempt
        fields = [
            'rank', 'username', 'user_nom', 'user_prenom',
            'points_earned', 'total_points', 'time_taken',
            'completed_at', 'submission_count'
        ]
    
    def get_rank(self, obj):
        return obj.get_rank_in_challenge()
    
    def get_time_taken(self, obj):
        time_seconds = obj.calculate_time_taken()
        if time_seconds:
            # Convertir en format lisible
            hours = int(time_seconds // 3600)
            minutes = int((time_seconds % 3600) // 60)
            seconds = int(time_seconds % 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return None


class GlobalRankingSerializer(serializers.ModelSerializer):
    """Serializer pour le classement global"""
    
    username = serializers.CharField(source='user.username', read_only=True)
    user_nom = serializers.CharField(source='user.nom', read_only=True)
    user_prenom = serializers.CharField(source='user.prenom', read_only=True)
    
    class Meta:
        model = ChallengeRanking
        fields = [
            'global_rank', 'username', 'user_nom', 'user_prenom',
            'total_points', 'challenges_completed', 'challenges_attempted'
        ]


class UserStatsSerializer(serializers.Serializer):
    """Serializer pour les statistiques d'un utilisateur"""
    
    total_attempts = serializers.IntegerField()
    completed_challenges = serializers.IntegerField()
    in_progress_challenges = serializers.IntegerField()
    total_points = serializers.IntegerField()
    average_success_rate = serializers.FloatField()
    global_rank = serializers.IntegerField()
    recent_attempts = ChallengeAttemptSerializer(many=True)