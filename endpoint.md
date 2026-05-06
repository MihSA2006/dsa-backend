# Documentation des Endpoints API - DSA Platform

Voici la liste complète des endpoints exposés par le backend de la plateforme DSA.

## 1. Comptes & Authentification (Accounts)

### Inscription
- **POST** `/api/accounts/register/initiate/`
  - **Description :** L'admin initie l'inscription d'un utilisateur.
  - **Permissions :** Admin
  - **Body :** 
    ```json
    { "email": "user@example.com" }
    ```
  - **Response (201) :** `{ "message": "...", "email": "...", "token": "..." }`

- **GET** `/api/accounts/verify-back/register/?token={token}`
  - **Description :** Vérification du token d'inscription. Redirige vers le frontend.
  - **Response (302) :** Redirection.

- **POST** `/api/accounts/register/complete/`
  - **Description :** Complète l'inscription.
  - **Body (Multipart/form-data ou JSON) :** `nom`, `prenom`, `username`, `password`, `numero_inscription`, `classe`, `parcours`, `photo` (optionnel), `token`.
  - **Response (201) :** `{ "message": true, "user": { ... } }`

### Connexion et Jetons (JWT)
- **POST** `/api/accounts/login/`
  - **Body :** `{ "username": "...", "password": "..." }` *(username ou email peut souvent être utilisé selon la configuration JWT)*
  - **Response (200) :** `{ "access": "...", "refresh": "..." }`

- **POST** `/api/accounts/token/refresh/`
  - **Body :** `{ "refresh": "..." }`
  - **Response (200) :** `{ "access": "...", "refresh": "..." }`

- **POST** `/api/accounts/token/verify-refresh/`
  - **Body :** `{ "refresh": "..." }`
  - **Response (200) :** `{ "valid": true/false }`

- **POST** `/api/accounts/token/verify-access/`
  - **Body :** `{ "access": "..." }`
  - **Response (200) :** `{ "valid": true/false }`

### Profil et Utilisateurs
- **GET** `/api/accounts/users/`
  - **Description :** Liste tous les utilisateurs (Admin uniquement).
  - **Response (200) :** `[{ "id": 1, "username": "...", ... }]`

- **GET, PUT, PATCH** `/api/accounts/profile/`
  - **Description :** Modifie ou récupère le profil de l'utilisateur connecté.
  - **Body (Pour PUT/PATCH) :** `nom`, `prenom`, `photo`, etc.
  - **Response (200) :** Profil de l'utilisateur.

- **PUT, PATCH** `/api/accounts/profile/edit/`
  - **Description :** Édition du profil (nom, prenom, photo, numero_inscription, classe, parcours).
  - **Response (200) :** `{ "message": "...", "user": { ... } }`

- **GET** `/api/accounts/is-admin/`
  - **Response (200) :** `{ "is_admin": true/false }`

- **GET** `/api/accounts/users/profiles/<int:user_id>/`
  - **Description :** Récupère le profil complet d’un utilisateur avec ses statistiques (challenges terminés, classement).
  - **Response (200) :** `{ "user": { ... }, "challenges": { ... }, "ranking": { ... } }`

### Réinitialisation de Mot de Passe
- **POST** `/api/accounts/password-reset/initiate/`
  - **Body :** `{ "email": "..." }`
  - **Response (201) :** `{ "message": "...", "email": "...", "token": "..." }`

- **GET** `/api/accounts/verify-back/password-reset/?token={token}`
  - **Response (302) :** Redirection vers le frontend pour définir le nouveau mot de passe.

- **POST** `/api/accounts/password-reset/complete/`
  - **Body :** `{ "token": "...", "new_password": "..." }`
  - **Response (200) :** `{ "message": true, "detail": "..." }`


## 2. API Générale, CodeRunner et Leaderboards (Api)

### Utilitaires
- **GET** `/api/health/`
  - **Response (200) :** `{ "status": "ok", "message": "API is running", "version": "1.0.0" }`

- **GET** `/api/languages/`
  - **Response (200) :** `{ "languages": [{ "name": "Python", "code": "python", "version": "3.x", "supported": true }] }`

- **GET** `/api/security-info/`
  - **Response (200) :** `{ "forbidden_imports": [...], "max_code_length": 50000, "timeout": 5, "memory_limit_mb": 50 }`

- **POST** `/api/execute/`
  - **Description :** Exécute du code indépendamment (sandbox).
  - **Body :** `{ "code": "print('hello')", "language": "python" }`
  - **Response (200) :** `{ "success": true/false, "output": "hello", "execution_time": 0.05, "error": null }`

### Gestion des Challenges (CRUD)
- **GET** `/api/challenges/`
  - **Description :** Liste tous les challenges actifs (hors contests en cours/à venir).
  - **Response (200) :** `[{ "id": 1, "title": "...", "difficulty": "...", "xp_reward": 100, ... }]`

- **GET, PUT, PATCH, DELETE** `/api/challenges/<int:id>/`
  - **Description :** Récupération ou modification d'un challenge spécifique.

- **POST** `/api/challenges/`
  - **Description :** Création d'un challenge.

### Actions Utilisateur sur Challenges
- **GET** `/api/challenges/my-challenges/`
  - **Response (200) :** `[{ "challenge": { ... }, "status": "completed", "xp_earned": 100, ... }]`

- **POST** `/api/challenges/<int:challenge_id>/join/`
  - **Response (201/200) :** `{ "message": true/false }` (selon s'il vient de rejoindre ou avait déjà rejoint).

- **POST** `/api/challenges/<int:challenge_id>/save-code/`
  - **Body :** `{ "code": "..." }`
  - **Response (200) :** `{ "success": true, "message": "Code sauvegardé...", "saved_at": "..." }`

- **POST** `/api/challenges/<int:challenge_id>/test/`
  - **Description :** Teste une solution (sandbox) sur tous les test cases du challenge.
  - **Body :** `{ "code": "...", "language": "python" }`
  - **Response (200) :** `{ "success": true/false, "passed_tests": 3, "total_tests": 3, "message": "..." }`

- **POST** `/api/challenges/<int:challenge_id>/test-case/<int:test_case_id>/`
  - **Description :** Teste sur un seul test case spécifique.
  - **Body :** `{ "code": "...", "language": "python" }`
  - **Response (200) :** `{ "success": true/false, "message": "..." }`

- **POST** `/api/challenges/<int:challenge_id>/submit/`
  - **Description :** Soumission officielle (valide la réussite, attribue l'XP).
  - **Body :** `{ "code": "...", "language": "python" }`
  - **Response (200) :** `{ "success": true/false, "passed": 3, "failed": 0, "xp_earned": 100, "status": "completed", "message": "..." }`

### Test Cases (CRUD)
- **GET, POST** `/api/test-cases/`
- **GET, PUT, PATCH, DELETE** `/api/test-cases/<int:id>/`

### Leaderboards et Statistiques
- **GET** `/api/challenges/<int:challenge_id>/leaderboard/`
  - **Response (200) :** `{ "challenge": { ... }, "leaderboard": [{ "rank": 1, "username": "...", "xp_earned": 100, "completion_time": 120, ... }] }`

- **GET** `/api/leaderboard/global/`
  - **Response (200) :** `{ "total_users": 50, "leaderboard": [{ "rank": 1, "username": "...", "total_xp": 1500, "total_completion_time": 3600, ... }] }`

- **GET** `/api/my-stats/`
  - **Response (200) :** `{ "user": { ... }, "challenges": { "joined": 5, "completed": 3, "completion_rate": 60.0 }, "ranking": { "global_rank": 12, "total_users": 50 }, "performance": { ... } }`


## 3. Contests et Équipes (Contests)

### Gestion des Contests
- **GET** `/api/contests/`
  - **Description :** Liste tous les contests (statuts mis à jour automatiquement).
  - **Response (200) :** `[{ "id": 1, "title": "...", "statut": "upcoming/ongoing/finished", ... }]`

- **GET** `/api/contests/<int:id>/`
  - **Description :** Détails d'un contest spécifique.

- **GET** `/api/contests/<int:id>/teams/`
  - **Response (200) :** `{ "contest_id": 1, "total_teams": 3, "teams": [{ "id": 1, "nom": "Alpha", ... }] }`

- **GET** `/api/contests/<int:id>/challenges/`
  - **Description :** Disponible uniquement si le contest est en cours.
  - **Response (200) :** `{ "contest_id": 1, "challenges": [...] }`

- **GET** `/api/contests/<int:id>/leaderboard/`
  - **Response (200) :** Classement des équipes du contest.

### Actions sur le Contest (Utilisateur/Équipes)
- **POST** `/api/contests/<int:contest_id>/challenges/<int:challenge_id>/test/`
  - **Description :** Teste un code sans l'enregistrer.
  - **Body :** `{ "code": "...", "team_id": 1 }`
  - **Response (200) :** `{ "success": true/false, "passed_tests": 2, "total_tests": 2, "message": "..." }`

- **POST** `/api/contests/<int:contest_id>/challenges/<int:challenge_id>/submit/`
  - **Description :** Soumission officielle en équipe lors d'un contest.
  - **Body :** `{ "code": "...", "team_id": 1 }`
  - **Response (200) :** `{ "success": true, "xp_earned": 50, "passed": 2, "failed": 0, "temps_soumission": 300, ... }`

- **GET** `/api/contests/<int:contest_id>/check-membership/`
  - **Response (200) :** `{ "is_member": true/false, "team_id": 1, "team_name": "Alpha", ... }`

- **GET** `/api/contests/<int:contest_id>/check-captain/`
  - **Response (200) :** `{ "is_captain": true/false, ... }`

- **GET** `/api/contests/<int:contest_id>/check-role/`
  - **Response (200) :** `{ "role": "captain", "is_member": true, "is_captain": true, ... }`

### Équipes (Teams)
- **POST** `/api/teams/create/`
  - **Body :** `{ "contest": 1, "nom": "Mon Équipe" }`
  - **Response (201) :** `{ "id": 1, "nom": "Mon Équipe", "capitaine": { ... } }`

- **DELETE** `/api/teams/<int:team_id>/delete/`
  - **Description :** Supprime l'équipe (Seulement si le contest n'a pas commencé, par le capitaine).
  - **Response (200) :** `{ "success": true, "message": "..." }`

- **GET** `/api/teams/<int:team_id>/members/`
  - **Response (200) :** `{ "team_id": 1, "members": [...] }`

- **POST** `/api/teams/<int:team_id>/remove/`
  - **Body :** `{ "user_id": 2 }`
  - **Response (200) :** `{ "success": true, "message": "..." }`

- **POST** `/api/teams/<int:team_id>/leave/`
  - **Description :** Un membre quitte l'équipe de lui-même.
  - **Body :** `{}`
  - **Response (200) :** `{ "success": true, "message": "..." }`

### Invitations
- **POST** `/api/teams/<int:team_id>/invite/`
  - **Body :** `{ "user_email": "user@example.com" }` ou `{ "emails": ["u1@e.com", "u2@e.com"] }`
  - **Response (200) :** Résultat pour chaque invitation.

- **GET** `/api/invitations/me/`
  - **Response (200) :** Liste de vos invitations reçues.

- **GET / POST** `/api/invitations/accept/<str:token>/`
  - **Description :** Accepte l'invitation. Retire l'utilisateur des autres invitations du contest.
  - **Response (200) :** `{ "success": true, "message": "...", "team": { ... } }`

- **GET / POST** `/api/invitations/decline/<str:token>/`
  - **Description :** Décline et supprime l'invitation en cours.
  - **Response (200) :** `{ "success": true, "message": "..." }`
