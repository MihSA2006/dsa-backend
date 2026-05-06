import os
import requests
from typing import Dict, Any
import uuid
from django.conf import settings

# ──────────────────────────────────────────────────────────────────────────────
# URL de base de l'API d'exécution externe.
# Configurer via la variable d'environnement EXECUTOR_API_URL.
# ──────────────────────────────────────────────────────────────────────────────
EXECUTOR_API_URL = settings.EXECUTOR_API_URL

SUPPORTED_LANGUAGES = ['python', 'c', 'javascript']

# ──────────────────────────────────────────────────────────────────────────────
# Ancien code d'exécution locale (désactivé, conservé pour référence)
# ──────────────────────────────────────────────────────────────────────────────
# import subprocess
# import tempfile
# import shutil
# import time
# import sys
#
# try:
#     import resource
#     HAS_RESOURCE = True
# except ImportError:
#     HAS_RESOURCE = False
#
#
# class CodeExecutorLocal:
#     DEFAULT_TIMEOUT = 10
#     MEMORY_LIMIT = 128 * 1024 * 1024
#
#     def __init__(self, timeout: int = DEFAULT_TIMEOUT, execution_id: str = None):
#         self.timeout = timeout
#         self.execution_id = execution_id or str(uuid.uuid4())
#         print(f"[INIT] CodeExecutor {self.execution_id} initialisé")
#
#     def _set_limits(self):
#         if not HAS_RESOURCE:
#             return
#         try:
#             resource.setrlimit(resource.RLIMIT_AS, (self.MEMORY_LIMIT, self.MEMORY_LIMIT))
#             resource.setrlimit(resource.RLIMIT_CPU, (self.timeout, self.timeout))
#         except Exception as e:
#             pass
#
#     def execute(self, code: str) -> Dict[str, Any]:
#         temp_dir = None
#         script_path = None
#         try:
#             temp_dir = tempfile.mkdtemp(prefix=f'code_exec_{self.execution_id}_')
#             script_path = os.path.join(temp_dir, f'script_{self.execution_id}.py')
#             with open(script_path, 'w', encoding='utf-8') as f:
#                 f.write(code)
#             command = [sys.executable, script_path]
#             start_time = time.time()
#             if HAS_RESOURCE and os.name == 'posix':
#                 result = subprocess.run(
#                     command, capture_output=True, text=True,
#                     timeout=self.timeout, cwd=temp_dir, preexec_fn=self._set_limits
#                 )
#             else:
#                 result = subprocess.run(
#                     command, capture_output=True, text=True,
#                     timeout=self.timeout, cwd=temp_dir
#                 )
#             execution_time = time.time() - start_time
#             if result.returncode == 0:
#                 return {'success': True, 'output': result.stdout, 'error': None, 'execution_time': round(execution_time, 3)}
#             else:
#                 return {'success': False, 'output': None, 'error': result.stderr, 'execution_time': round(execution_time, 3)}
#         except subprocess.TimeoutExpired:
#             return {'success': False, 'output': None, 'error': f"Temps d'exécution dépassé ({self.timeout} secondes)", 'execution_time': self.timeout}
#         except Exception as e:
#             return {'success': False, 'output': None, 'error': f"Erreur lors de l'exécution : {str(e)}", 'execution_time': 0}
#         finally:
#             try:
#                 if script_path and os.path.exists(script_path):
#                     os.remove(script_path)
#                 if temp_dir and os.path.exists(temp_dir):
#                     shutil.rmtree(temp_dir)
#             except Exception:
#                 pass
# ──────────────────────────────────────────────────────────────────────────────


class CodeExecutor:
    """
    Exécute du code via l'API externe EXECUTOR_API_URL.
    Langages supportés : python, c, javascript.
    """

    DEFAULT_TIMEOUT = 10
    MEMORY_LIMIT = 128 * 1024 * 1024  # conservé pour compatibilité SecurityInfoView

    def __init__(self, timeout: int = DEFAULT_TIMEOUT, execution_id: str = None):
        self.timeout = timeout
        self.execution_id = execution_id or str(uuid.uuid4())
        print(f"[INIT] CodeExecutor {self.execution_id} initialisé (API externe)")

    def execute(self, code: str, language: str = 'python') -> Dict[str, Any]:
        """
        Envoie le code à l'API externe et retourne le résultat normalisé.

        Returns dict avec:
            success (bool), output (str|None), error (str|None), execution_time (float)
        """
        if language not in SUPPORTED_LANGUAGES:
            return {
                'success': False,
                'output': None,
                'error': f"Langage '{language}' non supporté. Langages acceptés : {', '.join(SUPPORTED_LANGUAGES)}",
                'execution_time': 0
            }

        payload = {
            'language': language,
            'code': code,
        }

        print(f"[EXEC-{self.execution_id}] Envoi vers API externe (langage={language})")

        try:
            response = requests.post(
                EXECUTOR_API_URL,
                json=payload,
                timeout=self.timeout + 5,
            )
            response.raise_for_status()
            data = response.json()

            error = data.get('error')
            output = data.get('output')
            execution_time = data.get('execution_time', 0)
            success = error is None

            print(f"[EXEC-{self.execution_id}] Réponse reçue — success={success}, time={execution_time}s")
            return {
                'success': success,
                'output': output,
                'error': error,
                'execution_time': round(float(execution_time), 3),
            }

        except requests.exceptions.Timeout:
            print(f"[EXEC-{self.execution_id}] Timeout de l'API externe")
            return {
                'success': False,
                'output': None,
                'error': f"L'API d'exécution n'a pas répondu dans le délai imparti ({self.timeout + 5}s)",
                'execution_time': 0,
            }
        except requests.exceptions.RequestException as e:
            print(f"[EXEC-{self.execution_id}] Erreur réseau : {e}")
            return {
                'success': False,
                'output': None,
                'error': f"Erreur de connexion à l'API d'exécution : {str(e)}",
                'execution_time': 0,
            }
        except Exception as e:
            print(f"[EXEC-{self.execution_id}] Erreur inattendue : {e}")
            return {
                'success': False,
                'output': None,
                'error': f"Erreur inattendue : {str(e)}",
                'execution_time': 0,
            }
