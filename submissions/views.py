# submissions/views.py

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count, Avg

from .models import ChallengeAttempt, Submission, ChallengeRanking
from api.models import Challenge
from .serializers import (
    ChallengeAttemptSerializer,
    SubmissionSerializer,
    ChallengeLeaderboardSerializer,
    GlobalRankingSerializer,
    UserStatsSerializer
)
from api.serializers import ChallengeSubmissionSerializer
from api.security import SecurityChecker
from api.challenge_validator import ChallengeValidator

import logging

logger = logging.getLogger(__name__)


class ChallengeSubmitView(APIView):
    """
    Vue pour soumettre une solution à un challenge
    NÉCESSITE AUTHENTIFICATION
    """
    permission_classes = [IsAuthenticated]
    
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
        
        # 4. Récupérer ou créer la tentative (attempt)
        attempt, created = ChallengeAttempt.objects.get_or_create(
            user=request.user,
            challenge=challenge,
            defaults={
                'total_points': challenge.test_cases.count()
            }
        )
        
        # Si l'attempt existe déjà, mettre à jour total_points si nécessaire
        if not created:
            current_total = challenge.test_cases.count()
            if attempt.total_points != current_total:
                attempt.total_points = current_total
                attempt.save()
        
        # 5. Récupérer tous les test cases
        test_cases = challenge.test_cases.all()
        
        if not test_cases.exists():
            return Response(
                {'error': 'Ce challenge n\'a pas de test cases'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 6. Préparer les test cases pour la validation
        test_data = []
        for tc in test_cases:
            test_data.append({
                'input_content': tc.get_input(),
                'expected_output': tc.get_output(),
                'order': tc.order
            })
        
        # 7. Valider le code
        try:
            validator = ChallengeValidator(timeout=10)
            result = validator.validate_submission(user_code, test_data)
            
            # 8. Enregistrer la soumission
            submission = Submission.objects.create(
                attempt=attempt,
                code=user_code,
                is_correct=result['success'],
                points_earned=result['passed_tests'],
                passed_tests=result['passed_tests'],
                total_tests=result['total_tests'],
                execution_time=sum(r['execution_time'] for r in result['results']),
                error_message=str(result['results']) if not result['success'] else ''
            )
            
            # 9. Mettre à jour la tentative
            attempt.submission_count += 1
            attempt.last_submitted_code = user_code
            
            # Si tous les tests sont passés
            if result['success']:
                attempt.status = 'completed'
                attempt.points_earned = result['passed_tests']
                
                # Marquer comme terminé si pas déjà fait
                if not attempt.completed_at:
                    attempt.completed_at = timezone.now()
                    attempt.total_time_seconds = attempt.calculate_time_taken()
                
                # Mettre à jour le classement global
                self._update_user_ranking(request.user)
            else:
                # Mise à jour partielle des points (meilleur score)
                if result['passed_tests'] > attempt.points_earned:
                    attempt.points_earned = result['passed_tests']
            
            attempt.save()
            
            # 10. Calculer le rang
            rank = attempt.get_rank_in_challenge() if result['success'] else None
            
            # 11. Préparer la réponse
            response_data = {
                'success': result['success'],
                'passed_tests': result['passed_tests'],
                'total_tests': result['total_tests'],
                'points_earned': result['passed_tests'],
                'results': result['results'],
                'rank': rank,
                'attempt_id': attempt.id,
                'submission_id': submission.id,
                'status': attempt.status
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Erreur lors de la validation : {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': f'Erreur serveur : {str(e)}'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _update_user_ranking(self, user):
        """Met à jour le classement global de l'utilisateur"""
        ranking, created = ChallengeRanking.objects.get_or_create(user=user)
        ranking.update_stats()


class UserChallengeAttemptsView(APIView):
    """
    Vue pour récupérer les tentatives d'un utilisateur
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Liste toutes les tentatives de l'utilisateur connecté"""
        attempts = ChallengeAttempt.objects.filter(
            user=request.user
        ).select_related('challenge')
        
        # Filtrer par statut si demandé
        status_filter = request.query_params.get('status')
        if status_filter:
            attempts = attempts.filter(status=status_filter)
        
        serializer = ChallengeAttemptSerializer(attempts, many=True)
        return Response(serializer.data)


class ChallengeLeaderboardView(APIView):
    """
    Vue pour récupérer le classement d'un challenge spécifique
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request, challenge_id):
        """Récupère le classement d'un challenge"""
        challenge = get_object_or_404(Challenge, id=challenge_id, is_active=True)
        
        # Récupérer toutes les tentatives terminées, triées par points et temps
        attempts = ChallengeAttempt.objects.filter(
            challenge=challenge,
            status='completed'
        ).select_related('user').order_by(
            '-points_earned',
            'total_time_seconds'
        )
        
        serializer = ChallengeLeaderboardSerializer(attempts, many=True)
        return Response({
            'challenge_id': challenge.id,
            'challenge_title': challenge.title,
            'total_participants': attempts.count(),
            'leaderboard': serializer.data
        })


class GlobalLeaderboardView(APIView):
    """
    Vue pour récupérer le classement global
    """
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get(self, request):
        """Récupère le classement global"""
        
        # Mettre à jour les rangs
        self._update_global_ranks()
        
        rankings = ChallengeRanking.objects.select_related('user').order_by(
            '-total_points',
            '-challenges_completed'
        )[:100]  # Top 100
        
        serializer = GlobalRankingSerializer(rankings, many=True)
        return Response(serializer.data)
    
    def _update_global_ranks(self):
        """Met à jour les rangs globaux"""
        rankings = ChallengeRanking.objects.order_by(
            '-total_points',
            '-challenges_completed'
        )
        
        for index, ranking in enumerate(rankings, start=1):
            if ranking.global_rank != index:
                ranking.global_rank = index
                ranking.save(update_fields=['global_rank'])


class UserStatsView(APIView):
    """
    Vue pour récupérer les statistiques d'un utilisateur
    """
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Récupère les statistiques de l'utilisateur connecté"""
        user = request.user
        
        # Calculer les statistiques
        attempts = ChallengeAttempt.objects.filter(user=user)
        completed = attempts.filter(status='completed')
        in_progress = attempts.filter(status='in_progress')
        
        total_points = sum(attempt.points_earned for attempt in completed)
        
        # Taux de réussite moyen
        success_rates = [attempt.get_success_rate() for attempt in completed]
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0
        
        # Rang global
        ranking, created = ChallengeRanking.objects.get_or_create(user=user)
        if created:
            ranking.update_stats()
        
        # Tentatives récentes
        recent = attempts.order_by('-started_at')[:5]
        
        stats = {
            'total_attempts': attempts.count(),
            'completed_challenges': completed.count(),
            'in_progress_challenges': in_progress.count(),
            'total_points': total_points,
            'average_success_rate': round(avg_success_rate, 2),
            'global_rank': ranking.global_rank or 0,
            'recent_attempts': ChallengeAttemptSerializer(recent, many=True).data
        }
        
        serializer = UserStatsSerializer(stats)
        return Response(serializer.data)