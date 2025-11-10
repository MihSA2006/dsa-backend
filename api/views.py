# api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CodeExecutionSerializer, CodeExecutionResponseSerializer
from .security import SecurityChecker
from .executor import CodeExecutor
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

from .models import Challenge, TestCase
from .serializers import (
    ChallengeListSerializer,
    ChallengeDetailSerializer,
    ChallengeCreateSerializer,
    TestCaseCreateSerializer,
    ChallengeSubmissionSerializer
)
from .challenge_validator import ChallengeValidator

import logging

# Configuration du logger
logger = logging.getLogger(__name__)


class ExecuteCodeView(APIView):
    """
    Vue API pour exécuter du code Python
    """
    
    def post(self, request):
        """
        Exécute le code Python reçu dans la requête
        """
        print("[POST] Requête reçue pour exécution de code.")
        
        # 1. Valider les données reçues
        print("[POST] Validation des données d'entrée...")
        serializer = CodeExecutionSerializer(data=request.data)
        
        if not serializer.is_valid():
            print(f"[POST] Données invalides : {serializer.errors}")
            return Response(
                {
                    'success': False,
                    'error': serializer.errors,
                    'output': None,
                    'execution_time': 0
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 2. Récupérer le code validé
        code = serializer.validated_data['code']
        language = serializer.validated_data.get('language', 'python')
        print(f"[POST] Données valides. Langage: {language}, longueur du code: {len(code)} caractères.")
        
        logger.info(f"Exécution de code demandée (langage: {language}, longueur: {len(code)})")
        
        # 3. Vérifier la sécurité du code
        print("[POST] Vérification de la sécurité du code...")
        security_checker = SecurityChecker()
        is_safe, error_message = security_checker.check_code(code)
        
        if not is_safe:
            print(f"[POST] Code dangereux détecté : {error_message}")
            logger.warning(f"Code dangereux détecté : {error_message}")
            return Response(
                {
                    'success': False,
                    'error': f'Sécurité : {error_message}',
                    'output': None,
                    'execution_time': 0
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        print("[POST] Code validé comme sûr. Passage à l'exécution...")
        
        # 4. Exécuter le code
        try:
            executor = CodeExecutor(timeout=5)
            print("[POST] Exécution du code en cours...")
            result = executor.execute(code)
            print("[POST] Exécution terminée.")
            
            # Log du résultat
            if result['success']:
                print(f"[POST] Exécution réussie. Temps: {result['execution_time']}s")
                logger.info(f"Exécution réussie (temps: {result['execution_time']}s)")
            else:
                print(f"[POST] Échec de l'exécution. Erreur : {result['error']}")
                logger.warning(f"Exécution échouée : {result['error']}")
            
            # 5. Retourner le résultat
            print("[POST] Retour du résultat au client.")
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            print(f"[POST] Erreur inattendue lors de l'exécution : {e}")
            logger.error(f"Erreur inattendue lors de l'exécution : {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': f'Erreur serveur : {str(e)}',
                    'output': None,
                    'execution_time': 0
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class HealthCheckView(APIView):
    """
    Vue pour vérifier que l'API fonctionne
    """
    
    def get(self, request):
        """
        Retourne l'état de santé de l'API
        """
        print("[HEALTHCHECK] Vérification de l'état de l'API...")
        return Response(
            {
                'status': 'ok',
                'message': 'API is running',
                'version': '1.0.0'
            },
            status=status.HTTP_200_OK
        )


class SupportedLanguagesView(APIView):
    """
    Vue pour obtenir la liste des langages supportés
    """
    
    def get(self, request):
        """
        Retourne la liste des langages supportés
        """
        print("[LANGUAGES] Récupération de la liste des langages supportés...")
        return Response(
            {
                'languages': [
                    {
                        'name': 'Python',
                        'code': 'python',
                        'version': '3.x',
                        'supported': True
                    }
                ]
            },
            status=status.HTTP_200_OK
        )


class SecurityInfoView(APIView):
    """
    Vue pour obtenir les informations de sécurité
    """
    
    def get(self, request):
        """
        Retourne les restrictions de sécurité
        """
        print("[SECURITYINFO] Récupération des informations de sécurité...")
        security_checker = SecurityChecker()
        
        print("[SECURITYINFO] Informations de sécurité préparées pour la réponse.")
        return Response(
            {
                'forbidden_imports': security_checker.get_forbidden_imports(),
                'max_code_length': security_checker.MAX_CODE_LENGTH,
                'timeout': CodeExecutor.DEFAULT_TIMEOUT,
                'memory_limit_mb': CodeExecutor.MEMORY_LIMIT / (1024 * 1024)
            },
            status=status.HTTP_200_OK
        )

class ChallengeViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les challenges
    
    - GET /api/challenges/ : Liste tous les challenges
    - GET /api/challenges/{id}/ : Détail d'un challenge
    - POST /api/challenges/ : Créer un challenge
    - PUT /api/challenges/{id}/ : Modifier un challenge
    - DELETE /api/challenges/{id}/ : Supprimer un challenge
    """
    
    queryset = Challenge.objects.filter(is_active=True)
    parser_classes = (MultiPartParser, FormParser)
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChallengeListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ChallengeCreateSerializer
        return ChallengeDetailSerializer
    
    def list(self, request):
        """Liste tous les challenges"""
        challenges = self.get_queryset()
        serializer = ChallengeListSerializer(challenges, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """Récupère le détail d'un challenge"""
        challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
        serializer = ChallengeDetailSerializer(challenge)
        return Response(serializer.data)
    
    def create(self, request):
        """Crée un nouveau challenge"""
        serializer = ChallengeCreateSerializer(data=request.data)
        if serializer.is_valid():
            challenge = serializer.save()
            return Response(
                ChallengeDetailSerializer(challenge).data,
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class TestCaseViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les test cases
    
    - GET /api/test-cases/ : Liste tous les test cases
    - POST /api/test-cases/ : Créer un test case
    """
    
    queryset = TestCase.objects.all()
    serializer_class = TestCaseCreateSerializer
    parser_classes = (MultiPartParser, FormParser)
    
    def create(self, request):
        """Crée un nouveau test case"""
        serializer = TestCaseCreateSerializer(data=request.data)
        if serializer.is_valid():
            test_case = serializer.save()
            return Response(
                {'id': test_case.id, 'message': 'Test case créé avec succès'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChallengeSubmissionView(APIView):
    """
    Vue pour soumettre une solution à un challenge
    
    POST /api/challenges/submit/
    Body: {
        "challenge_id": 1,
        "code": "..."
    }
    """
    
    def post(self, request):
        """Soumet et valide la solution d'un challenge"""
        
        # 1. Valider les données reçues
        serializer = ChallengeSubmissionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        challenge_id = serializer.validated_data['challenge_id']
        user_code = serializer.validated_data['code']
        
        # 2. Récupérer le challenge
        try:
            challenge = Challenge.objects.get(id=challenge_id, is_active=True)
        except Challenge.DoesNotExist:
            return Response(
                {'error': 'Challenge introuvable'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # 3. Vérifier la sécurité du code
        from .security import SecurityChecker
        security_checker = SecurityChecker()
        is_safe, error_message = security_checker.check_code(user_code)
        
        if not is_safe:
            return Response(
                {
                    'success': False,
                    'error': f'Sécurité : {error_message}'
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 4. Récupérer tous les test cases
        test_cases = challenge.test_cases.all()
        
        if not test_cases.exists():
            return Response(
                {'error': 'Ce challenge n\'a pas de test cases'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 5. Préparer les test cases pour la validation
        test_data = []
        for tc in test_cases:
            test_data.append({
                'input_content': tc.get_input(),
                'expected_output': tc.get_output(),
                'order': tc.order
            })
        
        # 6. Valider le code
        try:
            validator = ChallengeValidator(timeout=10)
            result = validator.validate_submission(user_code, test_data)
            
            return Response(result, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation : {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': f'Erreur serveur : {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
