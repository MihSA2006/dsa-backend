# api/serializers.py

from rest_framework import serializers
from rest_framework import serializers
from .models import Challenge, TestCase, UserChallengeAttempt
from django.contrib.auth import get_user_model
from django.db.models import Q
import requests

User = get_user_model()


class CodeExecutionSerializer(serializers.Serializer):
    """
    Serializer pour valider les données d'exécution de code
    """
    
    # Champ obligatoire : le code à exécuter
    code = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=10000,
        error_messages={
            'required': 'Le champ "code" est obligatoire',
            'blank': 'Le code ne peut pas être vide',
            'max_length': 'Le code est trop long (maximum 10000 caractères)'
        }
    )
    
    # Champ optionnel : le langage (pour évolution future)
    language = serializers.ChoiceField(
        choices=['python'],
        default='python',
        required=False,
        error_messages={
            'invalid_choice': 'Langage non supporté. Seul "python" est accepté.'
        }
    )
    
    def validate_code(self, value):
        """
        Validation personnalisée du code
        """
        # Vérifier que le code n'est pas uniquement des espaces
        if not value.strip():
            raise serializers.ValidationError(
                "Le code ne peut pas contenir uniquement des espaces"
            )
        
        return value


class CodeExecutionResponseSerializer(serializers.Serializer):
    """
    Serializer pour formater la réponse de l'exécution
    """
    success = serializers.BooleanField()
    output = serializers.CharField(allow_null=True, required=False)
    error = serializers.CharField(allow_null=True, required=False)
    execution_time = serializers.FloatField()

class TestCaseSerializer(serializers.ModelSerializer):
    input_content = serializers.SerializerMethodField()
    output_content = serializers.SerializerMethodField()

    class Meta:
        model = TestCase
        fields = [
            'id', 'order', 'is_sample',
            'input_file', 'output_file',
            'input_content', 'output_content'
        ]

    def get_input_content(self, obj):
        """Lire le contenu du fichier d'entrée depuis Cloudinary"""
        if obj.input_file:
            try:
                response = requests.get(obj.input_file.url, timeout=10)
                if response.status_code == 200:
                    # ✅ NORMALISER LES SAUTS DE LIGNE : \r\n → \n
                    content = response.text.replace('\r\n', '\n').replace('\r', '\n')
                    return content
                return f"[Erreur lecture input: HTTP {response.status_code}]"
            except Exception as e:
                return f"[Erreur lecture input: {e}]"
        return None

    def get_output_content(self, obj):
        """Lire le contenu du fichier de sortie depuis Cloudinary"""
        if obj.output_file:
            try:
                response = requests.get(obj.output_file.url, timeout=10)
                if response.status_code == 200:
                    # ✅ NORMALISER LES SAUTS DE LIGNE : \r\n → \n
                    content = response.text.replace('\r\n', '\n').replace('\r', '\n')
                    return content
                return f"[Erreur lecture output: HTTP {response.status_code}]"
            except Exception as e:
                return f"[Erreur lecture output: {e}]"
        return None




class ChallengeListSerializer(serializers.ModelSerializer):
    test_cases_count = serializers.SerializerMethodField()
    join = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'slug', 'difficulty',
            'test_cases_count', 'created_at',
            'xp_reward', 'participants_count',
            'join', 'status'
        ]

    def get_test_cases_count(self, obj):
        return obj.test_cases.count()

    def get_join(self, obj):
        """Retourne True si l'utilisateur a rejoint le challenge"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from api.models import UserChallengeAttempt
        return UserChallengeAttempt.objects.filter(
            user=request.user,
            challenge=obj
        ).exists()

    def get_status(self, obj):
        """
        Retourne complete ou in_progress si l'utilisateur a rejoint le challenge
        Sinon return None
        """
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        from api.models import UserChallengeAttempt
        attempt = UserChallengeAttempt.objects.filter(
            user=request.user,
            challenge=obj
        ).first()
        if not attempt:
            return None
        return "complete" if attempt.status == "completed" else "in_progress"






class ChallengeDetailSerializer(serializers.ModelSerializer):
    description = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    test_cases = TestCaseSerializer(many=True, read_only=True)
    join = serializers.SerializerMethodField()

    # 🔥 nouveaux champs ajoutés
    started_at = serializers.SerializerMethodField()
    completed_at = serializers.SerializerMethodField()
    completion_time = serializers.SerializerMethodField()

    saved_code = serializers.SerializerMethodField()
    last_saved_at = serializers.SerializerMethodField()
    
    in_contest = serializers.SerializerMethodField()
    contest_id = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'slug', 'difficulty',
            'description', 'template', 'xp_reward',
            'description_pdf', 'description_img',
            'test_cases', 'created_at', 'updated_at',
            'participants_count', 'join',
            'saved_code', 'last_saved_at',
            'started_at', 'completed_at', 'completion_time',
            'in_contest',
            'contest_id',
        ]

    def get_in_contest(self, obj):
        """Vérifie si le challenge appartient à un contest en cours ou à venir"""
        from contests.models import Contest
        from django.db.models import Q
        
        ongoing_or_upcoming = Contest.objects.filter(
            challenges=obj
        ).filter(
            Q(statut='ongoing') | Q(statut='upcoming')
        ).exists()
        
        return ongoing_or_upcoming

    def get_contest_id(self, obj):
        """Retourne l'ID du contest si ongoing ou upcoming, None sinon"""
        from contests.models import Contest
        from django.db.models import Q
        
        contest = Contest.objects.filter(
            challenges=obj
        ).filter(
            Q(statut='ongoing') | Q(statut='upcoming')
        ).first()
        
        return contest.id if contest else None

    def get_description(self, obj):
        """Retourne la description du challenge depuis Cloudinary"""
        from contests.models import Contest
        from rest_framework.exceptions import PermissionDenied
        
        # Vérifier si le challenge est dans un contest À VENIR
        in_upcoming_contest = Contest.objects.filter(
            challenges=obj,
            statut='upcoming'
        ).exists()
        
        if in_upcoming_contest:
            raise PermissionDenied(
                "Ce challenge fait partie d'un contest à venir. "
                "Les détails seront accessibles une fois le contest commencé."
            )
        
        # Utiliser la méthode get_description() du modèle (qui utilise requests)
        return obj.get_description()

    def get_template(self, obj):
        """Retourne le template du challenge depuis Cloudinary"""
        from contests.models import Contest
        from rest_framework.exceptions import PermissionDenied
        
        # Vérifier si le challenge est dans un contest À VENIR
        in_upcoming_contest = Contest.objects.filter(
            challenges=obj,
            statut='upcoming'
        ).exists()
        
        if in_upcoming_contest:
            raise PermissionDenied(
                "Ce challenge fait partie d'un contest à venir. "
                "Le template sera accessible une fois le contest commencé."
            )
        
        # Utiliser la méthode get_template() du modèle (qui utilise requests)
        return obj.get_template()
    
    def get_test_cases(self, obj):
        """Retourne les test cases du challenge"""
        from contests.models import Contest
        
        # Vérifier si le challenge est dans un contest À VENIR
        in_upcoming_contest = Contest.objects.filter(
            challenges=obj,
            statut='upcoming'
        ).exists()
        
        if in_upcoming_contest:
            return []  # Retourner une liste vide
        
        return obj.test_cases.all()

    def get_join(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        from api.models import UserChallengeAttempt
        return UserChallengeAttempt.objects.filter(user=request.user, challenge=obj).exists()

    def get_saved_code(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        from api.models import UserCodeSave
        record = UserCodeSave.objects.filter(user=request.user, challenge=obj).first()
        return record.code if record else obj.get_template()

    def get_last_saved_at(self, obj):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        from api.models import UserCodeSave
        record = UserCodeSave.objects.filter(user=request.user, challenge=obj).first()
        return record.saved_at if record else None

    def _get_attempt(self, obj):
        """Récupère la tentative de l'utilisateur pour éviter répéter le code"""
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return None
        from api.models import UserChallengeAttempt
        return UserChallengeAttempt.objects.filter(user=request.user, challenge=obj).first()
    
    def get_started_at(self, obj):
        attempt = self._get_attempt(obj)
        return attempt.started_at if attempt else None
    
    def get_completed_at(self, obj):
        attempt = self._get_attempt(obj)
        return attempt.completed_at if attempt else None
    
    def get_completion_time(self, obj):
        attempt = self._get_attempt(obj)
        return attempt.completion_time if attempt else None






class ChallengeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Challenge
        fields = [
            'title', 'slug', 'difficulty',
            'description_file', 'description_pdf', 'description_img',
            'template_file', 'xp_reward'
        ]

    
    def validate_slug(self, value):
        """Valide que le slug est unique"""
        if Challenge.objects.filter(slug=value).exists():
            raise serializers.ValidationError("Ce slug existe déjà")
        return value

class TestCaseCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'un test case
    """
    
    class Meta:
        model = TestCase
        fields = ['challenge', 'input_file', 'output_file', 'order', 'is_sample']


class ChallengeSubmissionSerializer(serializers.Serializer):
    """
    Serializer pour la soumission d'une solution à un challenge
    """
    challenge_id = serializers.IntegerField(required=True)
    code = serializers.CharField(required=True, allow_blank=False)
    
    def validate_challenge_id(self, value):
        """Vérifie que le challenge existe"""
        if not Challenge.objects.filter(id=value, is_active=True).exists():
            raise serializers.ValidationError("Challenge introuvable")
        return value
    




class UserChallengeAttemptSerializer(serializers.ModelSerializer):
    """Serializer pour les tentatives de challenge"""
    challenge_title = serializers.CharField(source='challenge.title', read_only=True)
    challenge_difficulty = serializers.CharField(source='challenge.difficulty', read_only=True)
    xp_reward = serializers.IntegerField(source='challenge.xp_reward', read_only=True)
    
    class Meta:
        model = UserChallengeAttempt
        fields = [
            'id', 'challenge', 'challenge_title', 'challenge_difficulty',
            'status', 'started_at', 'completed_at', 'completion_time',
            'xp_earned', 'xp_reward', 'attempts_count'
        ]
        read_only_fields = ['started_at', 'completed_at', 'completion_time', 'xp_earned']


class ChallengeStatsSerializer(serializers.ModelSerializer):
    """Serializer avec statistiques du challenge"""
    participants_count = serializers.SerializerMethodField()
    completion_rate = serializers.SerializerMethodField()
    user_attempt = serializers.SerializerMethodField()
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'slug', 'difficulty', 'xp_reward',
            'participants_count', 'completion_rate', 'user_attempt',
            'created_at'
        ]
    
    def get_participants_count(self, obj):
        return obj.get_participants_count()
    
    def get_completion_rate(self, obj):
        return obj.get_completion_rate()
    
    def get_user_attempt(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                attempt = UserChallengeAttempt.objects.get(
                    user=request.user,
                    challenge=obj
                )
                return {
                    'status': attempt.status,
                    'started_at': attempt.started_at,
                    'completed_at': attempt.completed_at,
                    'xp_earned': attempt.xp_earned
                }
            except UserChallengeAttempt.DoesNotExist:
                return None
        return None


class ChallengeLeaderboardSerializer(serializers.Serializer):
    """Serializer pour le leaderboard d'un challenge"""
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    xp_earned = serializers.IntegerField()
    completion_time = serializers.IntegerField()
    completed_at = serializers.DateTimeField()
    status = serializers.CharField()


class GlobalLeaderboardSerializer(serializers.Serializer):
    """Serializer pour le leaderboard global"""
    rank = serializers.IntegerField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    total_xp = serializers.IntegerField()
    challenges_joined = serializers.IntegerField()
    challenges_completed = serializers.IntegerField()