from rest_framework import serializers
from django.utils import timezone
from .models import Contest, Team, ContestSubmission, TeamInvitation
from accounts.models import User
from api.models import Challenge


class ContestListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des contests"""
    status_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    is_ongoing = serializers.SerializerMethodField()
    is_finished = serializers.SerializerMethodField()
    challenges_count = serializers.SerializerMethodField()
    contest_img = serializers.ImageField(read_only=True)  # 🆕
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'contest_img',  # 🆕 Ajout des nouveaux champs
            'date_debut', 'date_fin', 'statut', 
            'status_display', 'type', 'type_display', 'nombre_team',
            'is_ongoing', 'is_finished', 'challenges_count', 'created_at'
        ]
    
    def get_is_ongoing(self, obj):
        return obj.is_ongoing()
    
    def get_is_finished(self, obj):
        return obj.is_finished()
    
    def get_challenges_count(self, obj):
        return obj.challenges.count()


class ContestDetailSerializer(serializers.ModelSerializer):
    """Serializer pour le détail d'un contest"""
    status_display = serializers.CharField(source='get_statut_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    is_ongoing = serializers.SerializerMethodField()
    is_finished = serializers.SerializerMethodField()
    has_started = serializers.SerializerMethodField()
    challenges = serializers.SerializerMethodField()
    contest_img = serializers.ImageField(read_only=True)  # 🆕
    
    class Meta:
        model = Contest
        fields = [
            'id', 'title', 'description', 'contest_img',  # 🆕 Ajout des nouveaux champs
            'date_debut', 'date_fin', 'statut',
            'status_display', 'type', 'type_display', 'nombre_team',
            'is_ongoing', 'is_finished', 'has_started', 'challenges',
            'created_at', 'updated_at'
        ]
    
    def get_is_ongoing(self, obj):
        return obj.is_ongoing()
    
    def get_is_finished(self, obj):
        return obj.is_finished()
    
    def get_has_started(self, obj):
        return obj.has_started()
    
    def get_challenges(self, obj):
        """Retourne les challenges seulement si le contest est en cours"""
        if obj.is_ongoing():
            from api.serializers import ChallengeListSerializer
            return ChallengeListSerializer(obj.challenges.all(), many=True).data
        return []

class UserMinimalSerializer(serializers.ModelSerializer):
    """Serializer minimal pour les utilisateurs"""
    class Meta:
        model = User
        fields = ['id', 'username', 'nom', 'prenom', 'total_xp']


class TeamMemberSerializer(serializers.ModelSerializer):
    """Serializer pour les membres d'une équipe"""
    class Meta:
        model = User
        fields = ['id', 'username', 'nom', 'prenom', 'total_xp', 'photo']


class TeamListSerializer(serializers.ModelSerializer):
    """Serializer pour la liste des équipes dans un contest"""
    capitaine = UserMinimalSerializer(read_only=True)
    membres_count = serializers.SerializerMethodField()
    rank = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'nom', 'capitaine', 'xp_total', 'temps_total',
            'membres_count', 'rank', 'created_at'
        ]
    
    def get_membres_count(self, obj):
        return obj.membres.count()
    
    def get_rank(self, obj):
        """Calcule le rang de l'équipe dans le contest"""
        contest = obj.contest
        teams = list(contest.teams.all())
        try:
            return teams.index(obj) + 1
        except ValueError:
            return None
        

class TeamInvitationSerializer(serializers.ModelSerializer):
    inviter_name = serializers.CharField(source='inviter.username', read_only=True)
    invitee_name = serializers.CharField(source='invitee.username', read_only=True)
    team_name = serializers.CharField(source='team.nom', read_only=True)
    contest_name = serializers.CharField(source='team.contest.title', read_only=True)
    is_valid = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamInvitation
        fields = [
            'id', 'team', 'team_name', 'contest_name',
            'inviter', 'inviter_name', 'invitee', 'invitee_name',
            'status', 'created_at', 'expires_at', 'responded_at',
            'is_valid'
        ]
        read_only_fields = ['token', 'status', 'responded_at']
    
    def get_is_valid(self, obj):
        return obj.is_valid()


class TeamDetailSerializer(serializers.ModelSerializer):
    """Serializer pour le détail d'une équipe"""
    capitaine = UserMinimalSerializer(read_only=True)
    membres = TeamMemberSerializer(many=True, read_only=True)
    contest_title = serializers.CharField(source='contest.title', read_only=True)
    rank = serializers.SerializerMethodField()
    is_captain = serializers.SerializerMethodField()
    is_member = serializers.SerializerMethodField()
    
    class Meta:
        model = Team
        fields = [
            'id', 'nom', 'contest', 'contest_title', 'capitaine',
            'membres', 'xp_total', 'temps_total', 'rank',
            'is_captain', 'is_member', 'created_at'
        ]
    
    def get_rank(self, obj):
        contest = obj.contest
        teams = list(contest.teams.all())
        try:
            return teams.index(obj) + 1
        except ValueError:
            return None
    
    def get_is_captain(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.capitaine == request.user
        return False
    
    def get_is_member(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.membres.filter(id=request.user.id).exists()
        return False


class TeamCreateSerializer(serializers.ModelSerializer):
    """Serializer pour créer une équipe"""
    
    class Meta:
        model = Team
        fields = ['contest', 'nom']
    
    def validate(self, data):
        contest = data.get('contest')
        
        # Vérifier que le contest n'a pas commencé
        if contest.has_started():
            raise serializers.ValidationError(
                "Impossible de créer une équipe après le début du contest"
            )
        
        # Vérifier que l'utilisateur n'est pas déjà dans une équipe pour ce contest
        request = self.context.get('request')
        if request and Team.objects.filter(
            contest=contest,
            membres=request.user
        ).exists():
            raise serializers.ValidationError(
                "Vous êtes déjà dans une équipe pour ce contest"
            )
        
        return data
    
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['capitaine'] = request.user
        return super().create(validated_data)


class ContestSubmissionSerializer(serializers.ModelSerializer):
    """Serializer pour les soumissions de contest"""
    challenge_title = serializers.CharField(source='challenge.title', read_only=True)
    equipe_nom = serializers.CharField(source='equipe.nom', read_only=True)
    submitted_by_username = serializers.CharField(source='submitted_by.username', read_only=True)
    success_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = ContestSubmission
        fields = [
            'id', 'equipe', 'equipe_nom', 'challenge', 'challenge_title',
            'submitted_by', 'submitted_by_username', 'xp_earned',
            'temps_soumission', 'tests_reussis', 'tests_total',
            'success_rate', 'submitted_at'
        ]
        read_only_fields = ['submitted_by', 'submitted_at']
    
    def get_success_rate(self, obj):
        if obj.tests_total == 0:
            return 0
        return round((obj.tests_reussis / obj.tests_total) * 100, 2)