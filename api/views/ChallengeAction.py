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
    
SUPPORTED_LANGUAGES = ['python', 'c', 'javascript']

def get_code(request):
    code = request.data.get('code')
    if not code:
        raise ValueError("Le code est requis")
    return code

def get_language(request):
    language = request.data.get('language')
    if not language:
        raise ValueError("Le champ 'language' est requis.")
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Langage '{language}' non supporté. Langages acceptés : {', '.join(SUPPORTED_LANGUAGES)}.")
    return language


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
            'order': tc.order,
            'xp_reward': tc.xp_reward
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



@api_view(['POST'])
@permission_classes([IsAuthenticated])
def join_challenge(request, challenge_id):
    """
    Permet à un utilisateur de rejoindre un challenge.
    Si l'utilisateur appartient à une équipe, tous les membres de l'équipe
    rejoignent également le challenge automatiquement.
    """
    from contests.models import Team
    
    challenge = get_challenge_active(challenge_id)
    if isinstance(challenge, Response):
        return challenge
    
    # Vérifier si l'utilisateur a déjà rejoint ce challenge
    attempt, created = UserChallengeAttempt.objects.get_or_create(
        user=request.user,
        challenge=challenge
    )
    
    if created:
        print(f"[join_challenge] L'utilisateur {request.user.email} a rejoint le challenge {challenge_id}")
        new_participants = 1
        
        # Mettre à jour les stats du créateur
        if hasattr(request.user, 'update_stats'):
            request.user.update_stats()
            
        # Si le challenge appartient à au moins un contest, 
        # on inscrit aussi les membres de ses équipes
        if challenge.contests.exists():
            # Trouver tous les membres de toutes les équipes de l'utilisateur
            # pour les inscrire également
            team_members = User.objects.filter(
                team_memberships__in=Team.objects.filter(membres=request.user)
            ).distinct().exclude(id=request.user.id)
            
            for member in team_members:
                _, m_created = UserChallengeAttempt.objects.get_or_create(
                    user=member,
                    challenge=challenge
                )
                if m_created:
                    print(f"[join_challenge] Co-membre {member.email} rejoint automatiquement (Challenge de Contest)")
                    new_participants += 1
                    if hasattr(member, 'update_stats'):
                        member.update_stats()
        else:
            print(f"[join_challenge] Challenge {challenge_id} n'appartient à aucun contest, pas d'auto-join d'équipe.")
        
        # Mettre à jour le compteur global de participants
        Challenge.objects.filter(id=challenge.id).update(
            participants_count=F('participants_count') + new_participants
        )
        
        return Response({
            'message': True,
            'joined_count': new_participants
        }, status=status.HTTP_201_CREATED)
    else:
        # L'utilisateur a déjà rejoint ce challenge
        return Response({
            'message': False,
            'detail': "Challenge déjà rejoint"
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

    # Récupérer le code et le langage envoyés dans le body de la requête
    try:
        code = get_code(request)
        language = get_language(request)
        print(f"\n--- [test_challenge_solution] ---\nChallenge ID: {challenge_id}\nUser: {request.user.email}\nLanguage: {language}\nCode length: {len(code)}\n---")
    except ValueError as e:
        print(f"!!! [test_challenge_solution] ValueError: {str(e)}")
        return Response({'error': str(e)}, status=400)

    # Vérifier si le code est sécurisé (désactivé — géré par l'API externe)
    # resp_security = validate_code_security(code)
    # if resp_security is not True:
    #     return resp_security

    # Récupérer les test cases associés au challenge
    test_cases = get_test_cases(challenge)
    if isinstance(test_cases, Response):
        return test_cases

    # Convertir les test cases en données que le validateur peut exécuter
    test_data = build_test_data(test_cases)

    # Exécuter les tests du challenge avec le code soumis
    try:
        from api.challenge_validator import ChallengeValidator
        validator = ChallengeValidator(timeout=10)

        result = validator.validate_submission(code, test_data, language)

        # Ajout d'un message explicite pour le frontend selon le succès ou l'échec
        if result['success']:
            result['message'] = "✅ Tous les tests ont réussi ! Vous pouvez soumettre votre solution."
        else:
            result['message'] = (
                f"❌ {result['passed_tests']}/{result['total_tests']} tests réussis. "
                "Corrigez votre code avant de soumettre."
            )

        # Retour final de la réponse au frontend
        print(f"--- [test_challenge_solution] Response ---\nSuccess: {result['success']}\nPassed: {result['passed_tests']}/{result['total_tests']}\nMessage: {result['message']}\n---")
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

    # Récupérer le code et le langage soumis
    try:
        print(f"DEBUG: request.data type: {type(request.data)}")
        print(f"DEBUG: request.data keys: {list(request.data.keys())}")
        code = get_code(request)
        language = get_language(request)
        print(f"\n=== [submit_challenge_solution] ===\nChallenge ID: {challenge_id}\nUser: {request.user.email}\nLanguage: {language}\nCode length: {len(code)}\n===")
    except ValueError as e:
        print(f"!!! [submit_challenge_solution] ValueError: {str(e)}")
        print(f"DEBUG payload: {request.data}")
        return Response({'error': str(e)}, status=400)

    # Vérification de sécurité désactivée — gérée par l'API externe
    # resp_security = validate_code_security(code)
    # if resp_security is not True:
    #     return resp_security

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
        result = validator.validate_submission(code, test_data, language)

        passed_tests = result.get('passed_tests', 0)
        total_tests = result.get('total_tests', len(test_data))

        # Calcul de l'XP obtenue basé sur chaque test case réussi
        xp_current_submit = 0
        for test_result in result.get('results', []):
            if test_result.get('passed'):
                test_num = test_result.get('test_number', 1) - 1
                if 0 <= test_num < len(test_data):
                    xp_current_submit += test_data[test_num].get('xp_reward', 0)

        # Si le minimum d'XP requis pour valider n'est pas atteint
        if xp_current_submit < challenge.xp_required:
            return Response({
                'success': False,
                'message': (
                    f"Il faut au moins {challenge.xp_required} XP pour valider la soumission. "
                    f"Actuellement obtenu : {xp_current_submit} XP."
                ),
                'passed': passed_tests,
                'failed': total_tests - passed_tests
            }, status=status.HTTP_200_OK)

        # Mise à jour de l'XP : on ne diminue jamais l'XP
        if xp_current_submit > attempt.xp_earned:
            attempt.xp_earned = xp_current_submit

        # Mise à jour du temps de complétion à la première réussite
        if attempt.completed_at is None:
            attempt.completed_at = timezone.now()
            time_diff = attempt.completed_at - attempt.started_at
            attempt.completion_time = int(time_diff.total_seconds())

        # Statut → terminé si tous les tests sont passés
        if passed_tests == total_tests:
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

        # Calculer le XP total possible pour ce challenge
        xp_total_possible = sum(tc.get('xp_reward', 0) for tc in test_data)

        # Réponse finale envoyée au frontend
        print(f"=== [submit_challenge_solution] Response ===\nSuccess: True\nPassed: {passed_tests}\nFailed: {total_tests - passed_tests}\nXP Earned: {attempt.xp_earned}/{xp_total_possible}\nStatus: {attempt.status}\n===")
        return Response({
            'success': True,
            'passed': passed_tests,
            'failed': total_tests - passed_tests,
            'xp_earned': attempt.xp_earned,
            'xp_total': xp_total_possible,
            'completion_time': attempt.completion_time,
            'status': attempt.status,
            'message': f"Soumission enregistrée. XP total : {attempt.xp_earned}/{xp_total_possible}"
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
    
    # print("---------\n---------\n---------Test Case : \n", test_case)

    # Récupérer le code et le langage soumis par l'utilisateur
    try:
        code = get_code(request)
        language = get_language(request)
        print(f"\n+++ [test_specific_test_case] +++\nChallenge ID: {challenge_id}\nTestCase ID: {test_case_id}\nUser: {request.user.email}\nLanguage: {language}\nCode length: {len(code)}\n+++")
    except ValueError as e:
        print(f"!!! [test_specific_test_case] ValueError: {str(e)}")
        return Response({'error': str(e)}, status=400)

    # Vérification de sécurité désactivée — gérée par l'API externe
    # resp_security = validate_code_security(code)
    # if resp_security is not True:
    #     return resp_security

    # Exécuter uniquement ce test case spécifique
    from api.challenge_validator import ChallengeValidator
    validator = ChallengeValidator(timeout=10)
    try:
        result = validator.validate_submission(code, [{
            'input_content': test_case.get_input(),
            'expected_output': test_case.get_output(),
            'order': test_case.order
        }], language)

        # print("----------------\n Result : \n", result)

        # Ajouter un message clair pour le frontend selon succès/échec
        if result['success']:
            result['message'] = "✅ Ce test case a réussi !"
        else:
            result['message'] = "❌ Échec sur ce test case. Vérifie ton code."

        print(f"+++ [test_specific_test_case] Response +++\nSuccess: {result['success']}\nMessage: {result['message']}\nUser Output: {result.get('results', [{}])[0].get('user_output')}\n+++")
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