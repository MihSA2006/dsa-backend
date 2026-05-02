# Documentation du Module Contest (Backend Django)

Ce document décrit en détail les points de terminaison (endpoints) de l'API utilisés par le système de compétitions (Contest), ainsi que le déroulement étape par étape d'une compétition complète.

---

## 1. Liste des Endpoints

### 🏆 1.1. Consultation des Compétitions (Contests)

**Tous ces endpoints nécessitent `Authorization: Bearer <token>`**

#### a. Liste des contests
*   **Endpoint** : `GET /api/contests/`
*   **Description** : Récupère la liste de tous les contests avec leur statut mis à jour en temps réel.
*   **Requête (Body)** : Aucun
*   **Réponse (200 OK)** : Retourne un tableau d'objets. Voici les 3 cas possibles selon le moment :
    ```json
    [
        {
            "id": 1,
            "title": "Hackathon - En préparation",
            "statut": "upcoming",
            "status_display": "À venir",
            "is_ongoing": false,
            "is_finished": false,
            "challenges_count": 5
        },
        {
            "id": 2,
            "title": "Battle Code - En cours",
            "statut": "ongoing",
            "status_display": "En cours",
            "is_ongoing": true,
            "is_finished": false,
            "challenges_count": 8
        },
        {
            "id": 3,
            "title": "Algo Challenge - Terminé",
            "statut": "finished",
            "status_display": "Terminé",
            "is_ongoing": false,
            "is_finished": true,
            "challenges_count": 4
        }
    ]
    ```

#### b. Détails d'un contest
*   **Endpoint** : `GET /api/contests/{id}/`
*   **Description** : Récupère le détail (si `is_ongoing` est `true`, le tableau `challenges` contient les données).
*   **Requête** : Aucun
*   **Réponse (200 OK)** : Même format que ci-dessus, avec en plus le tableau `"challenges": [...]`.

#### c. Rôle de l'utilisateur dans un contest
*   **Endpoint** : `GET /api/contests/{contest_id}/check-role/`
*   **Description** : Vérifie le statut de l'utilisateur connecté dans ce contest ("captain", "member", ou "none").
*   **Requête** : Aucun
*   **Réponse (200 OK)** :
    ```json
    {
        "is_member": true,
        "is_captain": true,
        "team_id": 5,
        "team_name": "Les Codeurs Fous",
        "member_count": 3,
        "role": "captain",
        "contest_id": 1,
        "contest_title": "Hackathon 2026"
    }
    ```

#### d. Classement (Leaderboard)
*   **Endpoint** : `GET /api/contests/{id}/leaderboard/`
*   **Description** : Récupère le classement en temps réel des équipes du contest (trié par XP total décroissant puis par temps de soumission maximum croissant).
*   **Réponse (200 OK)** :
    ```json
    {
        "contest_id": 1,
        "contest_title": "Hackathon 2026",
        "contest_status": "ongoing",
        "leaderboard": [
             {
                 "id": 5,
                 "nom": "Les Codeurs Fous",
                 "xp_total": 450,
                 "temps_total": 3600,
                 "rank": 1
             }
        ]
    }
    ```

---

### 🛡 1.2. Gestion des Équipes et Invitations

#### a. Créer une équipe
*   **Endpoint** : `POST /api/teams/create/`
*   **Description** : L'utilisateur connecté crée une équipe et en devient le capitaine.
*   **Requête (Body JSON)** :
    ```json
    {
        "contest": 1,
        "nom": "Les Codeurs Fous"
    }
    ```
*   **Réponse (201 Created)** : Détails de la team.

#### b. Inviter des membres (Bulk)
*   **Endpoint** : `POST /api/teams/{team_id}/invite/`
*   **Description** : (Réservé au capitaine). Crée des notifications/invitations pour un ou plusieurs utilisateurs.
*   **Requête (Cas 1 - Un seul utilisateur)** :
    ```json
    {
        "user_email": "john@example.com"
    }
    ```
*   **Requête (Cas 2 - Plusieurs utilisateurs)** :
    ```json
    {
        "emails": ["john@example.com", "jane@example.com"]
    }
    ```
*   **Réponse (200 OK)** : Retourne le statut pour chaque email.
    ```json
    {
        "team_id": 5,
        "team_name": "Les Codeurs Fous",
        "results": [
            {
                "email": "john@example.com",
                "status": "success",
                "username": "JohnDoe",
                "invitation": { "token": "...", "status": "pending" }
            },
            {
                "email": "jane@example.com",
                "status": "error",
                "message": "Utilisateur non trouvé"
            }
        ]
    }
    ```

#### c. Mes Invitations
*   **Endpoint** : `GET /api/invitations/me/`
*   **Description** : Permet à l'utilisateur de lister les invitations qu'il a reçues.
*   **Réponse (200 OK)** : Exemple d'objet dans la liste :
    ```json
    [
        {
            "id": 12,
            "team_name": "Les Codeurs Fous",
            "contest_name": "Hackathon 2026",
            "token": "TOKEN_A_UTILISER_POUR_ACCEPTER",
            "status": "pending",
            "is_valid": true
        }
    ]
    ```

#### d. Accepter une invitation
*   **Endpoint** : `POST /api/invitations/accept/{token}/` (ou `GET`)
*   **Description** : Accepte de rejoindre l'équipe liée au token. Pas besoin d'être authentifié (le token fait foi).
*   **Réponse (200 OK)** :
    ```json
    {
        "success": true,
        "message": "Félicitations ! Vous avez rejoint l'équipe Les Codeurs Fous",
        "team": {
            "id": 5,
            "nom": "Les Codeurs Fous",
            "contest": "Hackathon 2026",
            "capitaine": "Admin",
            "nombre_membres": 2
        }
    }
    ```

#### e. Refuser une invitation
*   **Endpoint** : `POST /api/invitations/decline/{token}/` (ou `GET`)
*   **Description** : Refuse l'invitation.
*   **Réponse (200 OK)** :
    ```json
    {
        "success": true,
        "message": "Vous avez refusé l'invitation à rejoindre l'équipe Les Codeurs Fous"
    }
    ```
*   **Réponse (400 Bad Request - déjà traité)** :
    ```json
    {
        "success": false,
        "error": "Cette invitation a déjà été acceptée...",
        "status": "accepted"
    }
    ```

---

### 💻 1.3. Challenges : Test et Soumission

#### a. Tester du code (Exécution locale, sans sauvegarde)
*   **Endpoint** : `POST /api/contests/{contest_id}/challenges/{challenge_id}/test/`
*   **Description** : Exécute le code contre tous les « Test cases » du challenge, mais sans l'enregistrer dans les scores officiels.
*   **Requête (Body JSON)** :
    ```json
    {
        "code": "def solve():\n    print('Hello')",
        "team_id": 5
    }
    ```
*   **Réponse (200 OK)** :
    ```json
    {
        "success": true,
        "passed_tests": 2,
        "total_tests": 5,
        "message": "❌ 2/5 tests réussis."
    }
    ```

#### b. Soumettre le code (Officiel)
*   **Endpoint** : `POST /api/contests/{contest_id}/challenges/{challenge_id}/submit/`
*   **Description** : Enregistre officiellement la soumission ("Une seule soumission autorisée par challenge par équipe"). Le succès défini l'XP gagné et le score / timer de l'équipe évolue.
*   **Requête (Body JSON)** :
    ```json
    {
        "code": "def solve():\n    return a + b",
        "team_id": 5
    }
    ```
*   **Réponse (200 OK si valide)** :
    ```json
    {
        "success": true,
        "passed": 5,
        "failed": 0,
        "xp_earned": 100,
        "xp_total": 100,
        "temps_soumission": 1500,
        "message": "Soumission enregistrée. XP : 100/100"
    }
    ```

---

## 2. Workflow Complet d'un Contest (Étape par Étape)

### Étape 1 : Phase de préparation (`upcoming`)
1. L'application charge la liste des contests (`GET /api/contests/`). S'il y a un contest à venir, ses `challenges` sont toujours masqués.
2. Un utilisateur Lambda veut participer. Il crée une équipe en envoyant `POST /api/teams/create/` (Ex: `{"contest": 1, "nom": "Team Alpha"}`). Il devient capitaine.
3. Il souhaite convier ses amis. Il appelle `POST /api/teams/5/invite/` avec l'email `ami@db.com`.
4. L'ami se connecte, son UI appelle (en fond) `GET /api/invitations/me/`. Il y voit une invitation "pending" et son `token`.
5. L'ami clique sur "Accepter", ce qui lance `POST /api/invitations/accept/{token}`. La base de données ajoute l'ami dans l'équipe *Team Alpha*. L'équipe est prête.

### Étape 2 : Le signal de départ (`ongoing`)
6. L'heure de `date_debut` passe. L'utilisateur lance `GET /api/contests/1/`. Le backend détecte que le contest a démarré et le marque comme `ongoing`. 
7. **Conséquence** : Désormais les routes de modifications d'équipes (`invite`, `leave`, `create`, `remove`) renvoient `400 Bad Request`.
8. Le champ `challenges` est enfin rempli dans la réponse. L'équipe peut lister les exercices.

### Étape 3 : Codage et Entraînement
9. L'application récupère l'identifiant de son équipe en appelant `GET /api/contests/1/check-role/` qui lui donne `"team_id": 5`.
10. L'utilisateur code sur l'éditeur frontend. Il clique sur « **RUN** » (pour tester sans valider). L'interface appelle `POST /api/contests/1/challenges/20/test/`.
11. La réponse (par ex: `passed_tests: 3/5`) lui indique qu'il y a un bug dans son algorithme. Il corrige son code et refait autant de tests (`/test/`) qu'il le souhaite.

### Étape 4 : Soumission Officielle et Classement en direct
12. L'algorithme marche à 100%. L'interface clique sur « **SUBMIT** ». La requête est envoyée à `POST /api/contests/1/challenges/20/submit/`.
13. Le backend exécute et donne la note maximale (XP selon le ratio validé, et il récupère surtout le `temps_soumission` correspondant à `(now - contest.date_debut)`).
14. Les statuts de l'équipe `Team Alpha` sont mis à jour (Son xp grandit, et son timer passe au timer du dernier challenge complété grâce au module de `TeamAction.calculate_stats`).
15. Sur l'écran géant, une requête régulière (polling ou actualisation manuelle) sur `GET /api/contests/1/leaderboard/` montre "Team Alpha" remonter immédiatement à la première place avec le temps qu'il vient de claquer. Ce challenge est verrouillé et ne peut plus être soumis.

### Étape 5 : La Clôture (`finished`)
16. La date `date_fin` passe. Au prochain appel, le backend le passe en `finished`. L'endpoint `/submit/` se verrouille (`403 Forbidden`).
17. Le `GET /api/contests/1/leaderboard/` donne le vainqueur définitif immuable. 
