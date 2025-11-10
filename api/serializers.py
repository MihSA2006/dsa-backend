# api/serializers.py

from rest_framework import serializers
from rest_framework import serializers
from .models import Challenge, TestCase

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
    """
    Serializer pour les test cases
    """
    input_content = serializers.SerializerMethodField()
    output_content = serializers.SerializerMethodField()
    
    class Meta:
        model = TestCase
        fields = ['id', 'order', 'is_sample', 'input_content', 'output_content']
    
    def get_input_content(self, obj):
        """Retourne le contenu du fichier input si c'est un exemple"""
        if obj.is_sample:
            return obj.get_input()
        return None
    
    def get_output_content(self, obj):
        """Retourne le contenu du fichier output si c'est un exemple"""
        if obj.is_sample:
            return obj.get_output()
        return None


class ChallengeListSerializer(serializers.ModelSerializer):
    """
    Serializer pour la liste des challenges (vue simplifiée)
    """
    test_cases_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Challenge
        fields = ['id', 'title', 'slug', 'difficulty', 'test_cases_count', 'created_at']
    
    def get_test_cases_count(self, obj):
        return obj.test_cases.count()


class ChallengeDetailSerializer(serializers.ModelSerializer):
    """
    Serializer pour le détail d'un challenge
    """
    description = serializers.SerializerMethodField()
    template = serializers.SerializerMethodField()
    test_cases = TestCaseSerializer(many=True, read_only=True)
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'title', 'slug', 'difficulty', 
            'description', 'template', 'test_cases',
            'created_at', 'updated_at'
        ]
    
    def get_description(self, obj):
        return obj.get_description()
    
    def get_template(self, obj):
        return obj.get_template()


class ChallengeCreateSerializer(serializers.ModelSerializer):
    """
    Serializer pour la création d'un challenge avec upload de fichiers
    """
    
    class Meta:
        model = Challenge
        fields = [
            'title', 'slug', 'difficulty',
            'description_file', 'template_file'
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