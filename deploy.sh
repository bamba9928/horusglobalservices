#!/bin/bash

# Arrêter le script en cas d'erreur
set -e

echo "--- 🚀 Début du déploiement : $(date) ---"

# 1. Mise à jour du code
cd /var/www/horusglobalservices/horusglobalservices
echo "📥 Mise à jour via Git..."
git reset --hard HEAD
git pull origin main

# 2. Activation de l'environnement virtuel
echo "🐍 Activation du venv..."
source venv/bin/activate
pip install -r requirements.txt

# 3. Base de données
# NOTE : plus de "makemigrations" ici. Les migrations se génèrent en local et
# se commitent — c'est le schéma de la base, il fait partie du code. Les
# générer sur le serveur laissait la prod décider du schéma, sans historique
# et sans possibilité de rejouer le même déploiement ailleurs.
# Pensez à un dump avant toute migration :
#   pg_dump -U "$DB_USER" "$DB_NAME" > ~/backups/horus-$(date +%F-%H%M).sql
echo "🗄️ Application des migrations..."
python3 manage.py migrate --noinput

# 4. Compilation Tailwind (AVANT collectstatic)
# npm ci installe exactement les versions du package-lock.json : sans lui, le
# build dépendait d'un node_modules installé à la main sur le serveur.
# npm run build:css utilise le binaire local (@tailwindcss/cli) au lieu de
# laisser npx résoudre une version arbitraire depuis le registre.
echo "🎨 Compilation et minification de Tailwind CSS..."
npm ci
npm run build:css

# 5. Fichiers Statiques
echo "📦 Collecte des fichiers statiques..."
# --clear vide l'ancien dossier static pour éviter les résidus
python3 manage.py collectstatic --noinput --clear

# 6. Redémarrage des services
echo "⚙️ Redémarrage de Gunicorn et Nginx..."
sudo systemctl restart gunicorn
sudo systemctl reload nginx

echo "--- ✅ Déploiement terminé avec succès ! ---"
