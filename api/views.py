# api/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import CodeExecutionSerializer, CodeExecutionResponseSerializer
from .security import SecurityChecker
from .executor import CodeExecutor
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
