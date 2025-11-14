from rest_framework.response import Response
from rest_framework import status


from api.models import Challenge, TestCase, TeamInvitation, Team
from api.serializers import (
    UserChallengeAttemptSerializer
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import get_user_model
from api.models import UserChallengeAttempt

from django.shortcuts import get_object_or_404


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
    Soumet une solution pour un challenge (une seule fois par utilisateur)
    L’XP gagnée dépend du nombre de tests réussis.
    """
    from django.utils import timezone
    from api.security import SecurityChecker
    from api.challenge_validator import ChallengeValidator

    # Vérifier que le challenge existe
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response({'error': 'Challenge introuvable'}, status=status.HTTP_404_NOT_FOUND)

    # Vérifier que l'utilisateur a rejoint le challenge
    try:
        attempt = UserChallengeAttempt.objects.get(user=request.user, challenge=challenge)
    except UserChallengeAttempt.DoesNotExist:
        return Response({'error': 'Vous devez d\'abord rejoindre ce challenge'}, status=status.HTTP_403_FORBIDDEN)

    # Vérifier si le challenge est déjà terminé pour cet utilisateur
    if attempt.status == 'completed':
        return Response({
            'error': 'Vous avez déjà soumis une solution pour ce challenge. Challenge terminé.'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Récupérer le code soumis
    code = request.data.get('code')
    if not code:
        return Response({'error': 'Le code est requis'}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier la sécurité du code
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)
    if not is_safe:
        return Response({'error': f'Sécurité : {error_message}'}, status=status.HTTP_400_BAD_REQUEST)

    # Récupérer les test cases
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response({'error': 'Ce challenge n\'a pas de test cases'}, status=status.HTTP_400_BAD_REQUEST)

    # Préparer les tests à exécuter
    test_data = [{
        'input_content': tc.get_input(),
        'expected_output': tc.get_output(),
        'order': tc.order
    } for tc in test_cases]

    # Incrémenter le nombre de tentatives
    attempt.attempts_count += 1
    attempt.save()

    # Valider le code
    try:
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)

        total_tests = len(test_data)
        passed_tests = result.get('passed', 0)
        failed_tests = result.get('failed', 0)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        # Calculer l'XP obtenue
        xp_gained = int(challenge.xp_reward * success_rate)
        attempt.xp_earned = xp_gained
        attempt.completed_at = timezone.now()
        attempt.status = 'completed'

        # Calculer le temps de résolution
        time_diff = attempt.completed_at - attempt.started_at
        attempt.completion_time = int(time_diff.total_seconds())
        attempt.save()

        # Mettre à jour les stats de l'utilisateur (si ta méthode existe)
        if hasattr(request.user, 'update_stats'):
            request.user.update_stats()

        message = (
            f'Challenge terminé. Tests réussis : {passed_tests}/{total_tests}. '
            f'XP gagnée : {xp_gained}/{challenge.xp_reward}.'
        )

        return Response({
            'success': True,
            'passed': passed_tests,
            'failed': failed_tests,
            'xp_earned': xp_gained,
            'xp_total': challenge.xp_reward,
            'completion_time': attempt.completion_time,
            'message': message
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur lors de la validation : {str(e)}")
        return Response({'error': f'Erreur serveur : {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def team_submit_solution(request, team_id):
    """
    Un membre soumet une solution pour l'équipe.
    Si un membre soumet, le challenge est terminé pour toute l'équipe.
    """
    from django.utils import timezone
    from api.security import SecurityChecker
    from api.challenge_validator import ChallengeValidator

    try:
        team = Team.objects.select_related('challenge').prefetch_related('members').get(id=team_id)
    except Team.DoesNotExist:
        return Response({'error': 'Équipe introuvable'}, status=status.HTTP_404_NOT_FOUND)

    challenge = team.challenge

    # Vérifier si le challenge est déjà terminé pour l’équipe
    if team.is_completed:
        return Response({'error': 'Cette équipe a déjà terminé le challenge.'}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier que le user fait bien partie de l’équipe
    if request.user not in team.members.all():
        return Response({'error': 'Vous ne faites pas partie de cette équipe.'}, status=status.HTTP_403_FORBIDDEN)

    # Récupérer le code soumis
    code = request.data.get('code')
    if not code:
        return Response({'error': 'Le code est requis.'}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier la sécurité du code
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)
    if not is_safe:
        return Response({'error': f'Sécurité : {error_message}'}, status=status.HTTP_400_BAD_REQUEST)

    # Récupérer les test cases du challenge
    test_cases = challenge.test_cases.all()
    if not test_cases.exists():
        return Response({'error': 'Ce challenge n’a pas de test cases.'}, status=status.HTTP_400_BAD_REQUEST)

    test_data = [{
        'input_content': tc.get_input(),
        'expected_output': tc.get_output(),
        'order': tc.order
    } for tc in test_cases]

    # Valider la solution
    try:
        validator = ChallengeValidator(timeout=10)
        result = validator.validate_submission(code, test_data)

        total_tests = len(test_data)
        passed_tests = result.get('passed', 0)
        failed_tests = result.get('failed', 0)
        success_rate = passed_tests / total_tests if total_tests > 0 else 0

        xp_gained = int(challenge.xp_reward * success_rate)

        # Temps de complétion (celui du membre qui a soumis)
        completion_time = int((timezone.now() - timezone.now()).total_seconds())  # (tu peux ajuster si tu stockes started_at)

        # Marquer l’équipe comme terminée
        team.mark_as_completed(xp_earned=xp_gained, completion_time=completion_time)

        message = (
            f"Challenge terminé pour l’équipe '{team.name}'. "
            f"Tests réussis : {passed_tests}/{total_tests}. "
            f"XP gagnée : {xp_gained}/{challenge.xp_reward}."
        )

        return Response({
            'success': True,
            'passed': passed_tests,
            'failed': failed_tests,
            'xp_earned_per_member': xp_gained,
            'xp_total': challenge.xp_reward,
            'completion_time': completion_time,
            'message': message
        }, status=status.HTTP_200_OK)

    except Exception as e:
        logger.error(f"Erreur de soumission équipe : {str(e)}")
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
    try:
        UserChallengeAttempt.objects.get(user=request.user, challenge_id=challenge_id)
    except UserChallengeAttempt.DoesNotExist:
        return Response(
            {'error': "Vous devez d'abord rejoindre ce challenge"},
            status=status.HTTP_403_FORBIDDEN
        )

    # Vérifier que le challenge existe
    try:
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
    except Challenge.DoesNotExist:
        return Response(
            {'error': 'Challenge introuvable'},
            status=status.HTTP_404_NOT_FOUND
        )

    # Vérifier que le test case appartient bien à ce challenge
    try:
        test_case = challenge.test_cases.get(id=test_case_id)
    except TestCase.DoesNotExist:
        return Response(
            {'error': "Test case introuvable pour ce challenge"},
            status=status.HTTP_404_NOT_FOUND
        )

    # Vérifier le code envoyé
    code = request.data.get('code')
    if not code:
        return Response({'error': 'Le code est requis'}, status=status.HTTP_400_BAD_REQUEST)

    # Vérifier la sécurité du code
    from api.security import SecurityChecker
    security_checker = SecurityChecker()
    is_safe, error_message = security_checker.check_code(code)

    if not is_safe:
        return Response(
            {'success': False, 'error': f"Sécurité : {error_message}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Exécuter uniquement ce test case
    from api.challenge_validator import ChallengeValidator
    validator = ChallengeValidator(timeout=10)
    try:
        result = validator.validate_submission(code, [{
            'input_content': test_case.get_input(),
            'expected_output': test_case.get_output(),
            'order': test_case.order
        }])

        # Ajouter un message convivial
        if result['success']:
            result['message'] = "✅ Ce test case a réussi !"
        else:
            result['message'] = "❌ Échec sur ce test case. Vérifie ton code."

        return Response(result, status=status.HTTP_200_OK)

    except Exception as e:
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

