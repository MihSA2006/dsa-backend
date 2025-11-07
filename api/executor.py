import subprocess
import tempfile
import os
import shutil
import time
import sys
from typing import Dict, Any

# Import conditionnel de resource (seulement sur Linux/Mac)
try:
    import resource
    HAS_RESOURCE = True
except ImportError:
    # Windows n'a pas le module resource
    HAS_RESOURCE = False


class CodeExecutor:
    """
    Classe pour exécuter du code Python de manière sécurisée
    Compatible Windows, Linux et Mac
    """
    
    # Timeout par défaut (en secondes)
    DEFAULT_TIMEOUT = 5
    
    # Limite de mémoire (en bytes) - 128 MB
    MEMORY_LIMIT = 128 * 1024 * 1024
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialise l'exécuteur de code
        
        Args:
            timeout: Temps maximum d'exécution en secondes
        """
        self.timeout = timeout
        print(f"[INIT] CodeExecutor initialisé avec timeout={self.timeout}s")

    def _set_limits(self):
        """
        Définit les limites de ressources pour le processus
        Cette fonction sera appelée dans le processus enfant
        Fonctionne uniquement sur Linux/Mac
        """
        print("[LIMITS] Début de la configuration des limites de ressources")
        if not HAS_RESOURCE:
            print("[LIMITS] Module resource non disponible, aucune limite appliquée")
            return
        
        try:
            # Limite de mémoire virtuelle
            resource.setrlimit(resource.RLIMIT_AS, 
                             (self.MEMORY_LIMIT, self.MEMORY_LIMIT))
            print(f"[LIMITS] Limite mémoire fixée à {self.MEMORY_LIMIT} bytes")

            # Limite de temps CPU
            resource.setrlimit(resource.RLIMIT_CPU, 
                             (self.timeout, self.timeout))
            print(f"[LIMITS] Limite CPU fixée à {self.timeout} secondes")
        except Exception as e:
            print(f"[LIMITS][ERREUR] Impossible d'appliquer les limites : {e}")
            pass
    
    def execute(self, code: str) -> Dict[str, Any]:
        """
        Exécute le code Python et retourne le résultat
        
        Args:
            code: Le code Python à exécuter
            
        Returns:
            Dictionnaire contenant:
            - success: bool - True si l'exécution a réussi
            - output: str - La sortie standard (stdout)
            - error: str - Les erreurs (stderr)
            - execution_time: float - Temps d'exécution en secondes
        """
        
        temp_dir = None
        script_path = None
        
        try:
            print("[EXEC] Démarrage de l'exécution du code...")
            # 1. Créer un répertoire temporaire
            temp_dir = tempfile.mkdtemp(prefix='code_exec_')
            print(f"[EXEC] Répertoire temporaire créé : {temp_dir}")
            script_path = os.path.join(temp_dir, 'script.py')
            
            # 2. Écrire le code dans un fichier
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(code)
            print(f"[EXEC] Code écrit dans le fichier : {script_path}")
            
            # 3. Préparer la commande d'exécution
            command = [sys.executable, script_path]
            print(f"[EXEC] Commande d'exécution préparée : {command}")
            
            # 4. Démarrer le chronomètre
            start_time = time.time()
            print("[EXEC] Chronomètre démarré")
            
            # 5. Exécuter le code
            print("[EXEC] Lancement du subprocess...")
            if HAS_RESOURCE and os.name == 'posix':  # Linux/Mac
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=temp_dir,
                    preexec_fn=self._set_limits
                )
            else:  # Windows
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    cwd=temp_dir
                )
            print("[EXEC] Subprocess terminé")
            
            # 6. Calculer le temps d'exécution
            execution_time = time.time() - start_time
            print(f"[EXEC] Temps d'exécution : {execution_time:.3f}s")
            
            # 7. Préparer la réponse
            if result.returncode == 0:
                print("[EXEC] Exécution réussie ✅")
                print(f"[EXEC][OUTPUT] {result.stdout.strip()}")
                return {
                    'success': True,
                    'output': result.stdout,
                    'error': None,
                    'execution_time': round(execution_time, 3)
                }
            else:
                print(f"[EXEC] Erreur d'exécution ❌ Code retour : {result.returncode}")
                print(f"[EXEC][STDERR] {result.stderr.strip()}")
                return {
                    'success': False,
                    'output': None,
                    'error': result.stderr,
                    'execution_time': round(execution_time, 3)
                }
        
        except subprocess.TimeoutExpired:
            print(f"[EXEC][TIMEOUT] Le code a dépassé le délai de {self.timeout}s")
            return {
                'success': False,
                'output': None,
                'error': f'Temps d\'exécution dépassé ({self.timeout} secondes)',
                'execution_time': self.timeout
            }
        
        except Exception as e:
            print(f"[EXEC][ERREUR] Exception inattendue : {e}")
            return {
                'success': False,
                'output': None,
                'error': f'Erreur lors de l\'exécution : {str(e)}',
                'execution_time': 0
            }
        
        finally:
            # 8. Nettoyage : supprimer les fichiers temporaires
            print("[EXEC][CLEANUP] Nettoyage des fichiers temporaires...")
            try:
                if script_path and os.path.exists(script_path):
                    os.remove(script_path)
                    print(f"[EXEC][CLEANUP] Script supprimé : {script_path}")
                if temp_dir and os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                    print(f"[EXEC][CLEANUP] Répertoire supprimé : {temp_dir}")
            except Exception as e:
                print(f"[EXEC][CLEANUP][ERREUR] {e}")
