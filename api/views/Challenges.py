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
            return ChallengeStatsSerializer  # 🆕 Changé
        elif self.action in ['create', 'update', 'partial_update']:
            return ChallengeCreateSerializer
        return ChallengeDetailSerializer
    
    def get_serializer_context(self):
        """Ajoute le request au contexte"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    

    
    def list(self, request):
        """Liste tous les challenges"""
        challenges = self.get_queryset()
        serializer = ChallengeListSerializer(challenges, many=True, context={'request': request})
        return Response(serializer.data)

    
    def retrieve(self, request, pk=None):
        """Récupère le détail d'un challenge"""
        challenge = get_object_or_404(Challenge, pk=pk, is_active=True)
        serializer = ChallengeDetailSerializer(challenge, context={'request': request})  # 🆕 ajout du contexte
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