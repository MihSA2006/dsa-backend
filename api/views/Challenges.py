from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework import status, viewsets
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from api.models import Challenge, TestCase
from api.serializers import (
    ChallengeListSerializer,
    ChallengeDetailSerializer,
    ChallengeCreateSerializer,
    TestCaseCreateSerializer,
    ChallengeStatsSerializer
)
from django.db.models import Q

class ChallengeViewSet(viewsets.ModelViewSet):
    """ViewSet pour gérer les challenges"""
    
    parser_classes = (MultiPartParser, FormParser)
    
    def get_queryset(self):
        """
        Retourne les challenges actifs en excluant ceux qui appartiennent
        à des contests en cours ou à venir
        """
        from contests.models import Contest
        
        # Récupérer les IDs des challenges appartenant à des contests non terminés
        ongoing_or_upcoming_contests = Contest.objects.filter(
            Q(statut='ongoing') | Q(statut='upcoming')
        )
        
        excluded_challenge_ids = ongoing_or_upcoming_contests.values_list(
            'challenges__id', flat=True
        )
        
        # Retourner tous les challenges actifs sauf ceux dans les contests non terminés
        return Challenge.objects.filter(
            is_active=True
        ).exclude(
            id__in=excluded_challenge_ids
        )
    
    def get_serializer_class(self):
        if self.action == 'list':
            return ChallengeStatsSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return ChallengeCreateSerializer
        return ChallengeDetailSerializer
    
    def get_serializer_context(self):
        """Ajoute le request au contexte"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def list(self, request):
        """Liste tous les challenges (excluant ceux des contests non terminés)"""
        challenges = self.get_queryset()
        serializer = ChallengeListSerializer(challenges, many=True, context={'request': request})
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        """
        Récupère le détail d'un challenge
        
        CONTRAINTE ACTIVABLE : Décommentez le bloc ci-dessous pour bloquer
        complètement l'accès aux challenges dans des contests À VENIR
        """
        from contests.models import Contest
        
        # Vérifier si le challenge est dans un contest À VENIR
        challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
        
        # Seulement bloquer si le contest est À VENIR (pas "ongoing" ou "finished")
        in_upcoming_contest = Contest.objects.filter(
            challenges=challenge,
            statut='upcoming' 
        ).exists()
        
        if in_upcoming_contest:
            return Response({
                'error': 'Ce challenge fait partie d\'un contest à venir',
                'in_contest': True,
                'contest_status': 'upcoming',
                'message': 'Les détails de ce challenge seront accessibles une fois le contest commencé'
            }, status=status.HTTP_403_FORBIDDEN)
        
        challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
        serializer = ChallengeDetailSerializer(challenge, context={'request': request})
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