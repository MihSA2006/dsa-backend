from rest_framework.response import Response
from rest_framework import status


from api.models import Challenge, TestCase
from api.serializers import (
    UserChallengeAttemptSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from api.models import UserChallengeAttempt, UserCodeSave

from django.shortcuts import get_object_or_404
from django.db.models import F


User = get_user_model()

import logging

# Configuration du logger
logger = logging.getLogger(__name__)




def verify_userjoin_challenge(request, challenge_id):
    print("{[verify_userjoin_challenge]} Debut Verification Challenge Rejoin ...")
    try:
        attempt = UserChallengeAttempt.objects.get(
            user=request.user,
            challenge_id=challenge_id
        )
        print("{[verify_userjoin_challenge]} Verification True ...")
        return attempt
    except UserChallengeAttempt.DoesNotExist:
        print("{[verify_userjoin_challenge]} Verification False ...")
        return Response(
            {'error': "Vous devez d'abord rejoindre ce challenge"},
            status=status.HTTP_403_FORBIDDEN
        )

def get_challenge_active(challenge_id):
    try:
        return Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )
    
def get_code(request):
    code = request.data.get('code')
    if not code:
        raise ValueError("Le code est requis")
    return code

from rest_framework.response import Response
from rest_framework import status

def get_code(request):
    code = request.data.get('code')
    if not code:
        raise ValueError("Le code est requis")
    return code


def get_test_cases(challenge):
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response(
            {'error': 'Ce challenge ne contient pas encore de tests.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    return test_cases


def build_test_data(test_cases):
    return [
        {
            'input_content': tc.get_input(),
            'expected_output': tc.get_output(),
            'order': tc.order
        }
        for tc in test_cases
    ]


def validate_code_security(code):
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
    return True



##################################################################################################


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_challenge(request, challenge_id):
    """
    Permet à un utilisateur de rejoindre un challenge
    
    POST /api/challenges/{id}/join/
    """
    
    challenge = get_challenge_active(challenge_id)
    if isinstance(challenge, Response):
        return challenge
    
    
    
    # Vérifier si l'utilisateur a déjà rejoint ce challenge
    attempt, created = UserChallengeAttempt.objects.get_or_create(
        user=request.user,
        challenge=challenge
    )
    
    if created:
        Challenge.objects.filter(id=challenge.id).update(
            participants_count=F('participants_count') + 1
        )
        
        # Première fois que l'utilisateur rejoint ce challenge
        request.user.update_stats()
        
        return Response({
            'message': True,
            # 'attempt': UserChallengeAttemptSerializer(attempt).data
        }, status=status.HTTP_201_CREATED)
    else:
        # L'utilisateur a déjà rejoint ce challenge
        return Response({
            'message': False,
            # 'attempt': UserChallengeAttemptSerializer(attempt).data
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

    # Vérifier que l'utilisateur a déjà rejoint ce challenge
    attempt = verify_userjoin_challenge(request, challenge_id)
    if isinstance(attempt, Response):
        return attempt

    # Vérifier que le challenge existe et est actif
    challenge = get_challenge_active(challenge_id)
    if isinstance(challenge, Response):
        return challenge

    # Récupérer le code envoyé dans le body de la requête
    try:
        code = get_code(request)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    # Vérifier si le code est sécurisé
    resp_security = validate_code_security(code)
    if resp_security is not True:
        return resp_security

    # Récupérer les test cases associés au challenge
    test_cases = get_test_cases(challenge)
    if isinstance(test_cases, Response):
        return test_cases

    # Convertir les test cases en données que le validateur peut exécuter
    test_data = build_test_data(test_cases)

    # Exécuter les tests du challenge avec le code soumis
    try:
        from api.challenge_validator import ChallengeValidator
        # Création du validateur avec un timeout de sécurité
        validator = ChallengeValidator(timeout=10)

        # Lancement de la validation du code par rapport aux test cases
        result = validator.validate_submission(code, test_data)

        # Ajout d'un message explicite pour le frontend selon le succès ou l'échec
        if result['success']:
            result['message'] = "✅ Tous les tests ont réussi ! Vous pouvez soumettre votre solution."
        else:
            result['message'] = (
                f"❌ {result['passed_tests']}/{result['total_tests']} tests réussis. "
                "Corrigez votre code avant de soumettre."
            )

        # Retour final de la réponse au frontend
        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        # En cas d'erreur interne (exécution du code, timeout, etc.)
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
    Soumission officielle d'une solution avec système d'XP progressif.
    Si tous les tests sont réussis et l'XP nécessaire est atteinte,
    la solution est validée et sauvegardée.
    """
    from django.utils import timezone
    from api.challenge_validator import ChallengeValidator

    # Récupérer le challenge actif
    challenge = get_challenge_active(challenge_id)
    if isinstance(challenge, Response):
        return challenge

    # Vérifier que l'utilisateur a rejoint le challenge
    attempt = verify_userjoin_challenge(request, challenge_id)
    if isinstance(attempt, Response):
        return attempt

    # Récupérer le code soumis
    try:
        code = get_code(request)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    # Vérifier la sécurité du code soumis
    resp_security = validate_code_security(code)
    if resp_security is not True:
        return resp_security

    # Récupérer les test cases du challenge
    test_cases = get_test_cases(challenge)
    if isinstance(test_cases, Response):
        return test_cases

    # Convertir les test cases dans un format exécutable par le validateur
    test_data = build_test_data(test_cases)

    # Incrémenter le nombre de tentatives pour l'utilisateur
    attempt.attempts_count += 1
    attempt.save()

    # Exécuter les tests sur le code soumis
    try:
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)

        passed_tests = result.get('passed_tests', 0)
        total_tests = result.get('total_tests', len(test_data))
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Calcul de l'XP obtenue pour cette soumission
        xp_current_submit = int(challenge.xp_reward * success_rate)

        # Si le minimum d'XP requis pour valider n'est pas atteint
        if attempt.xp_earned < challenge.xp_required and xp_current_submit < challenge.xp_required:
            return Response({
                'success': False,
                'message': (
                    f"Il faut au moins {challenge.xp_required} XP pour valider la soumission. "
                    f"Actuellement obtenu : {xp_current_submit} XP."
                ),
                'passed': passed_tests,
                'failed': total_tests - passed_tests
            }, status=status.HTTP_200_OK)

        # Mise à jour progressive de l'XP : on ne diminue jamais l'XP
        previous_xp = attempt.xp_earned
        if xp_current_submit > previous_xp:
            xp_diff = xp_current_submit - previous_xp
            attempt.xp_earned = min(previous_xp + xp_diff, challenge.xp_reward)

        # Mise à jour du temps de complétion si l'utilisateur n'a pas encore le maximum d'XP
        if attempt.completed_at is None:
            attempt.completed_at = timezone.now()
            time_diff = attempt.completed_at - attempt.started_at
            attempt.completion_time = int(time_diff.total_seconds())

        # Statut → terminé si XP max atteint
        if attempt.xp_earned >= challenge.xp_reward:
            attempt.status = "completed"

        attempt.save()

        # Si XP minimum requis est atteint → on sauvegarde le code utilisateur
        if attempt.xp_earned >= challenge.xp_required:
            UserCodeSave.objects.update_or_create(
                user=request.user,
                challenge=challenge,
                defaults={'code': code}
            )

        # Mise à jour des statistiques générales de l'utilisateur
        if hasattr(request.user, 'update_stats'):
            request.user.update_stats()

        # Réponse finale envoyée au frontend
        return Response({
            'success': True,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'xp_earned': attempt.xp_earned,
            'xp_total': challenge.xp_reward,
            'completion_time': attempt.completion_time,
            'status': attempt.status,
            'message': f"Soumission enregistrée. XP total : {attempt.xp_earned}/{challenge.xp_reward}"
        }, status=status.HTTP_200_OK)

    except Exception as e:
        # En cas d'erreur interne pendant l'exécution
        logger.error(f"Erreur lors de la validation : {str(e)}")
        return Response({'error': f'Erreur serveur : {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_specific_test_case(request, challenge_id, test_case_id):
    """
    Teste la solution d'un utilisateur pour un test case spécifique d'un challenge.

    POST /api/challenges/{challenge_id}/test-case/{test_case_id}/
    Body:
    {
        "code": "..."
    }
    """

    # Vérifier que l'utilisateur a rejoint le challenge
    attempt = verify_userjoin_challenge(request, challenge_id)
    if isinstance(attempt, Response):
        return attempt

    # Vérifier que le challenge existe et est actif
    challenge = get_challenge_active(challenge_id)
    if isinstance(challenge, Response):
        return challenge

    # Vérifier que le test case appartient bien à ce challenge
    try:
        test_case = challenge.test_cases.get(id=test_case_id)
    except TestCase.DoesNotExist:
        return Response(
            {'error': "Test case introuvable pour ce challenge"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Récupérer le code soumis par l'utilisateur
    try:
        code = get_code(request)
    except ValueError as e:
        return Response({'error': str(e)}, status=400)

    # Vérifier la sécurité du code
    resp_security = validate_code_security(code)
    if resp_security is not True:
        return resp_security

    # Exécuter uniquement ce test case spécifique
    from api.challenge_validator import ChallengeValidator
    validator = ChallengeValidator(timeout=10)
    try:
        result = validator.validate_submission(code, [{
            'input_content': test_case.get_input(),
            'expected_output': test_case.get_output(),
            'order': test_case.order
        }])

        # Ajouter un message clair pour le frontend selon succès/échec
        if result['success']:
            result['message'] = "✅ Ce test case a réussi !"
        else:
            result['message'] = "❌ Échec sur ce test case. Vérifie ton code."

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
        # En cas d'erreur interne lors de l'exécution
        logger.error(f"Erreur lors du test du test case spécifique : {str(e)}")
        return Response(
            {'success': False, 'error': f"Erreur serveur : {str(e)}"},
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

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_code(request, challenge_id):
    from api.models import UserCodeSave
    
    # Vérification du challenge
    challenge = get_object_or_404(Challenge, id=challenge_id, is_active=True)

    code = request.data.get('code')
    if code is None:
        return Response({
            "success": False,
            "message": "Le champ 'code' est requis."
        }, status=400)

    try:
        save_obj, created = UserCodeSave.objects.update_or_create(
            user=request.user,
            challenge=challenge,
            defaults={'code': code}
        )

        return Response({
            "success": True,
            "message": "Code sauvegardé avec succès" if created else "Code mis à jour avec succès",
            "saved_at": save_obj.saved_at
        }, status=200)

    except Exception as e:
        return Response({
            "success": False,
            "message": "Une erreur est survenue lors de la sauvegarde.",
            "error": str(e)
        }, status=500)