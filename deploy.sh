#!/bin/bash

# Arrêter le script en cas d'erreur (et sur variable non définie / échec dans un pipe)
set -euo pipefail

# Lancé par GitHub Actions (.github/workflows/ci.yml) via une clé SSH restreinte,
# donc en SSH non interactif : npm vit dans ~/.local/bin, hors du PATH par défaut.
export PATH="$HOME/.local/bin:$PATH"

APP_DIR=/var/www/horusglobalservices/horusglobalservices
SOCKET="$APP_DIR/horus.sock"

echo "--- 🚀 Début du déploiement : $(date) ---"

# 1. Mise à jour du code
cd "$APP_DIR"
echo "📥 Mise à jour via Git..."
# fetch + reset sur origin/main : déterministe (pas de merge, pas de conflit).
# Les fichiers non suivis (media/, .env, venv/...) ne sont pas touchés.
git fetch origin main
git reset --hard origin/main
git log --oneline -1

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
if sudo -n systemctl restart gunicorn 2>/dev/null; then
    echo "   gunicorn redémarré (systemctl restart)"
else
    # sudoers : seuls certains "restart" sont autorisés sans mot de passe, pas
    # gunicorn. Il tourne sous notre utilisateur et sans --preload : un SIGHUP
    # relance les workers en douceur avec le nouveau code, sans coupure.
    echo "   sudo indisponible : rechargement gracieux de gunicorn (SIGHUP)"
    GUNICORN_PID=$(systemctl show -p MainPID --value gunicorn)
    if [ "${GUNICORN_PID:-0}" -le 0 ]; then
        echo "❌ gunicorn ne tourne pas (MainPID=${GUNICORN_PID:-?})" >&2
        exit 1
    fi
    kill -HUP "$GUNICORN_PID"
fi
sudo -n systemctl reload nginx

# 7. Vérification : gunicorn doit répondre sur son socket (X-Forwarded-Proto
# évite la redirection SSL 301 de Django, qui masquerait un vrai problème).
echo "🩺 Vérification de gunicorn..."
HTTP_CODE=000
for _ in 1 2 3 4 5 6 7 8 9 10; do
    HTTP_CODE=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
        --unix-socket "$SOCKET" \
        -H 'Host: horuservices.cloud' -H 'X-Forwarded-Proto: https' \
        http://localhost/ || true)
    [ "$HTTP_CODE" = "200" ] && break
    sleep 2
done
if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ Healthcheck KO (HTTP $HTTP_CODE)" >&2
    exit 1
fi

echo "--- ✅ Déploiement terminé avec succès ! ---"
