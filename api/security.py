# api/security.py

import re
from typing import Tuple

class SecurityChecker:
    """
    Classe pour vérifier la sécurité du code Python avant exécution
    """
    
    # Imports interdits (dangereux pour le système)
    FORBIDDEN_IMPORTS = [
        'os',           # Accès système de fichiers
        'sys',          # Accès système
        'subprocess',   # Exécution de commandes
        'socket',       # Connexions réseau
        'requests',     # Requêtes HTTP
        'urllib',       # Requêtes HTTP
        'pathlib',      # Accès fichiers
        'shutil',       # Opérations fichiers
        'glob',         # Recherche fichiers
        'pickle',       # Sérialisation (dangereux)
        'ctypes',       # Appels C (dangereux)
        'importlib',    # Import dynamique
        'threading',    # Threads (peut causer des problèmes)
        'multiprocessing', # Processus multiples
    ]
    
    # Patterns de code dangereux
    DANGEROUS_PATTERNS = [
        r'\beval\s*\(',           # eval() - exécution de code dynamique
        r'\bexec\s*\(',           # exec() - exécution de code dynamique
        r'\b__import__\s*\(',     # __import__() - import dynamique
        r'\bcompile\s*\(',        # compile() - compilation de code
        r'\bopen\s*\(',           # open() - ouverture de fichiers
        r'\bfile\s*\(',           # file() - ancienne fonction fichier
        r'\binput\s*\(',          # input() - attend entrée utilisateur (bloque)
        r'\b__builtins__',        # Accès aux builtins
        r'\b__globals__',         # Accès aux variables globales
        r'\b__locals__',          # Accès aux variables locales
        r'\bdir\s*\(',            # dir() - introspection
        r'\bvars\s*\(',           # vars() - introspection
        r'\bglobals\s*\(',        # globals() - variables globales
        r'\blocals\s*\(',         # locals() - variables locales
    ]
    
    # Taille maximale du code (en caractères)
    MAX_CODE_LENGTH = 10000  # 10 000 caractères
    
    def check_code(self, code: str) -> Tuple[bool, str]:
        """
        Vérifie si le code est sûr à exécuter
        
        Args:
            code: Le code Python à vérifier
            
        Returns:
            Tuple (is_safe, error_message)
            - is_safe: True si le code est sûr, False sinon
            - error_message: Message d'erreur si le code n'est pas sûr
        """

        print("Debut Verification de securite du code ...")
        
        # 1. Vérifier que le code n'est pas vide
        if not code or not code.strip():
            print("Le code ne peut pas être vide")
            return False, "Le code ne peut pas être vide"
        
        # 2. Vérifier la longueur du code
        if len(code) > self.MAX_CODE_LENGTH:
            print(f"Le code est trop long (max {self.MAX_CODE_LENGTH} caractères)")
            return False, f"Le code est trop long (max {self.MAX_CODE_LENGTH} caractères)"
        
        # 3. Vérifier les imports interdits
        for forbidden in self.FORBIDDEN_IMPORTS:
            # Pattern pour détecter "import xxx" ou "from xxx import"
            pattern1 = rf'\bimport\s+{forbidden}\b'
            pattern2 = rf'\bfrom\s+{forbidden}\b'
            
            if re.search(pattern1, code) or re.search(pattern2, code):
                print(f"Import interdit détecté : {forbidden}")
                return False, f"Import interdit détecté : {forbidden}"
        
        # 4. Vérifier les patterns dangereux
        for pattern in self.DANGEROUS_PATTERNS:
            if re.search(pattern, code):
                match = re.search(pattern, code)
                print(f"Pattern dangereux détecté : {match.group()}")
                return False, f"Pattern dangereux détecté : {match.group()}"
        
        # 5. Si toutes les vérifications passent
        return True, ""
    
    def get_forbidden_imports(self) -> list:
        """Retourne la liste des imports interdits"""
        return self.FORBIDDEN_IMPORTS.copy()