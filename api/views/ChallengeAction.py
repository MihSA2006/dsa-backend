from rest_framework.response import Response
from rest_framework import status


from api.models import Challenge
from api.serializers import (
    UserChallengeAttemptSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from api.models import UserChallengeAttempt


User = get_user_model()

import logging

# Configuration du logger
logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_challenge(request, challenge_id):
    """
    Permet à un utilisateur de rejoindre un challenge
    
    POST /api/challenges/{id}/join/
    """
    
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Vérifier si l'utilisateur a déjà rejoint ce challenge
    attempt, created = UserChallengeAttempt.objects.get_or_create(
        user=request.user,
        challenge=challenge
    )
    
    if created:
        # Première fois que l'utilisateur rejoint ce challenge
        request.user.update_stats()
        
        return Response({
            'message': 'Challenge rejoint avec succès',
            'attempt': UserChallengeAttemptSerializer(attempt).data
        }, status=status.HTTP_201_CREATED)
    else:
        # L'utilisateur a déjà rejoint ce challenge
        return Response({
            'message': 'Vous avez déjà rejoint ce challenge',
            'attempt': UserChallengeAttemptSerializer(attempt).data
        }, status=status.HTTP_200_OK)
    


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_challenge_solution(request, challenge_id):
    """
    Teste une solution pour un challenge sans l'enregistrer.
    Permet à l'utilisateur de voir si son code passe tous les tests
    avant de le soumettre officiellement.
    
    POST /api/challenges/{id}/test/
    Body: {
        "code": "..."
    }
    """
    # Vérifier que l'utilisateur a rejoint le challenge
    try:
        attempt = UserChallengeAttempt.objects.get(
            user=request.user,
            challenge_id=challenge_id
        )
    except UserChallengeAttempt.DoesNotExist:
        return Response(
            {'error': "Vous devez d'abord rejoindre ce challenge"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Récupérer le challenge actif
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Récupérer le code
    code = request.data.get('code')
    if not code:
        return Response(
            {'error': 'Le code est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Vérifier la sécurité du code
    from api.security import SecurityChecker
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)

    if not is_safe:
        return Response(
            {
                'success': False,
                'error': f"Sécurité : {error_message}"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    # Récupérer les test cases
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response(
            {'error': 'Ce challenge ne contient pas encore de tests.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Préparer les test data
    test_data = []
    for tc in test_cases:
        test_data.append({
            'input_content': tc.get_input(),
            'expected_output': tc.get_output(),
            'order': tc.order
        })

    # Valider la solution sans enregistrer le résultat
    try:
        from api.challenge_validator import ChallengeValidator
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)

        # Ajout d'un message clair pour le frontend
        if result['success']:
            result['message'] = "✅ Tous les tests ont réussi ! Vous pouvez soumettre votre solution."
        else:
            result['message'] = f"❌ {result['passed_tests']}/{result['total_tests']} tests réussis. Corrigez votre code avant de soumettre."

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur lors du test de la solution : {str(e)}")
        return Response(
            {
                'success': False,
                'error': f"Erreur serveur : {str(e)}"
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_challenge_solution(request, challenge_id):
    """
    Soumet une solution pour un challenge
    L'utilisateur doit avoir rejoint le challenge au préalable
    
    POST /api/challenges/{id}/submit/
    Body: {
        "code": "..."
    }
    """
    
    # Vérifier que l'utilisateur a rejoint le challenge
    try:
        attempt = UserChallengeAttempt.objects.get(
            user=request.user,
            challenge_id=challenge_id
        )
    except UserChallengeAttempt.DoesNotExist:
        return Response(
            {'error': 'Vous devez d\'abord rejoindre ce challenge'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    # Récupérer le challenge
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Récupérer le code
    code = request.data.get('code')
    if not code:
        return Response(
            {'error': 'Le code est requis'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Vérifier la sécurité du code
    from api.security import SecurityChecker
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)
    
    if not is_safe:
        return Response(
            {
                'success': False,
                'error': f'Sécurité : {error_message}'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Incrémenter le nombre de tentatives
    attempt.attempts_count += 1
    attempt.save()
    
    # Récupérer tous les test cases
    test_cases = challenge.test_cases.all()
    
    if not test_cases.exists():
        return Response(
            {'error': 'Ce challenge n\'a pas de test cases'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Préparer les test cases pour la validation
    test_data = []
    for tc in test_cases:
        test_data.append({
            'input_content': tc.get_input(),
            'expected_output': tc.get_output(),
            'order': tc.order
        })
    
    # Valider le code
    try:
        from api.challenge_validator import ChallengeValidator
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)
        
        # Si tous les tests passent, marquer comme complété
        if result['success'] and attempt.status != 'completed':
            attempt.mark_as_completed()
            
            return Response({
                **result,
                'xp_earned': attempt.xp_earned,
                'completion_time': attempt.completion_time,
                'message': f'Félicitations ! Vous avez gagné {attempt.xp_earned} XP !'
            }, status=status.HTTP_200_OK)
        
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

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_challenges(request):
    """
    Liste tous les challenges rejoints par l'utilisateur
    
    GET /api/challenges/my-challenges/
    """
    
    attempts = UserChallengeAttempt.objects.filter(
        user=request.user
    ).select_related('challenge').order_by('-started_at')
    
    serializer = UserChallengeAttemptSerializer(attempts, many=True)
    return Response(serializer.data)
