#!/bin/bash
# dsa-backend/entrypoint.sh

# Attendre que la base de données soit prête
echo "⌛ En attente de la base de données..."
while ! nc -z db 5432; do
  sleep 0.1
done
echo "✅ Base de données disponible!"

# Appliquer les migrations
echo "🗃️ Application des migrations..."
python manage.py migrate

# Créer le superuser
echo "👤 Création du superuser..."
python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin-dsa', 'dsa.insi.platform@gmail.com', 'dsa-admin-password')
    print('Superuser admin créé')
else:
    print('Superuser existe déjà')
"

# Collecter les fichiers statiques
echo "📦 Collecte des fichiers statiques..."
python manage.py collectstatic --noinput

# Démarrer Gunicorn
echo "🚀 Démarrage de Gunicorn..."
exec gunicorn --bind 0.0.0.0:8888 backend.wsgi:application