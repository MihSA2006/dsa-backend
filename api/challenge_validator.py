# api/challenge_validator.py

from typing import Dict, List, Any
from .executor import CodeExecutor
import io
import sys
import uuid

class ChallengeValidator:
    """
    Classe pour valider les soumissions de challenges
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialise le validateur
        
        Args:
            timeout: Temps maximum d'exécution par test case
        """
        self.timeout = timeout
        self.validation_id = str(uuid.uuid4())
        self.executor = CodeExecutor(timeout=timeout)
    
    def validate_submission(
        self, 
        user_code: str, 
        test_cases: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Valide le code de l'utilisateur contre tous les test cases
        
        Args:
            user_code: Le code Python de l'utilisateur
            test_cases: Liste de dictionnaires contenant:
                - input_content: Le contenu de l'input
                - output_content: Le contenu attendu de l'output
                - order: L'ordre du test case
        
        Returns:
            Dictionnaire contenant:
            - success: bool - True si tous les tests passent
            - passed_tests: int - Nombre de tests réussis
            - total_tests: int - Nombre total de tests
            - results: list - Détails de chaque test
        """
        
        results = []
        passed_tests = 0
        total_tests = len(test_cases)
        
        for idx, test_case in enumerate(test_cases, 1):
            input_content = test_case['input_content']
            expected_output = test_case['expected_output']
            
            # Exécuter le code avec l'input spécifique
            result = self._run_with_input(user_code, input_content)
            
            if not result['success']:
                # Erreur d'exécution
                results.append({
                    'test_number': idx,
                    'passed': False,
                    'error': result['error'],
                    'expected_output': expected_output,
                    'user_output': None,
                    'execution_time': result['execution_time']
                })
            else:
                # Comparer les outputs
                user_output = result['output']
                is_correct = self._compare_outputs(user_output, expected_output)
                
                if is_correct:
                    passed_tests += 1
                
                results.append({
                    'test_number': idx,
                    'passed': is_correct,
                    'error': None,
                    'expected_output': expected_output if not is_correct else None,
                    'user_output': user_output,
                    'execution_time': result['execution_time']
                })
        
        return {
            'success': passed_tests == total_tests,
            'passed_tests': passed_tests,
            'total_tests': total_tests,
            'results': results
        }
    
    def _run_with_input(self, code: str, input_data: str) -> Dict[str, Any]:
        """
        Exécute le code avec un input spécifique
        
        Args:
            code: Le code Python à exécuter
            input_data: Les données d'input à fournir au programme
        
        Returns:
            Résultat de l'exécution
        """
        
        # Créer un code modifié qui utilise l'input fourni
        # On remplace les appels input() par des lectures depuis une liste
        executor = CodeExecutor(
            timeout=self.timeout,
            execution_id=f"{self.validation_id}_{uuid.uuid4()}"
        )
        # modified_code = self._inject_input(code, input_data)
        modified_code = self._inject_input(code, input_data)
        
        # Exécuter le code modifié
        # return self.executor.execute(modified_code)
        return executor.execute(modified_code)
    
    def _inject_input(self, code: str, input_data: str) -> str:
        """
        Injecte les données d'input dans le code
        
        Args:
            code: Le code original
            input_data: Les données d'input (une par ligne)
        
        Returns:
            Code modifié avec input injecté
        """
        
        # Préparer les lignes d'input
        input_lines = input_data.strip().split('\n')
        
        # Créer le code qui simule input()
        injected_code = f"""
import sys
from io import StringIO

# Injecter l'input
_input_data = {repr(input_data)}
sys.stdin = StringIO(_input_data)

# Code utilisateur
{code}
"""
        
        print("--------\nInjected Code : \n", injected_code)
        
        return injected_code
    
    def _compare_outputs(self, user_output: str, expected_output: str) -> bool:
        """
        Compare deux outputs en ignorant les espaces/lignes vides superflus
        
        Args:
            user_output: Output de l'utilisateur
            expected_output: Output attendu
        
        Returns:
            True si les outputs correspondent
        """
        
        # Normaliser les outputs
        user_lines = [line.strip() for line in user_output.strip().split('\n') if line.strip()]
        expected_lines = [line.strip() for line in expected_output.strip().split('\n') if line.strip()]
        
        # Comparer ligne par ligne
        return user_lines == expected_lines