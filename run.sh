#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Script tout-en-un : installe les dépendances et collecte les données
# Usage : bash run.sh
# ─────────────────────────────────────────────────────────────
set -e

# 1. Charger le .env si présent
if [ -f ".env" ]; then
    echo "📄 Chargement de .env…"
    set -a
    source .env
    set +a
fi

# 2. Vérifier les variables
if [ -z "$INTERVALS_ATHLETE_ID" ] || [ -z "$INTERVALS_API_KEY" ]; then
    echo ""
    echo "❌ Variables manquantes. Fais ceci :"
    echo "   cp .env.example .env"
    echo "   nano .env   # ou ouvre .env dans ton éditeur"
    echo "   # puis remplis INTERVALS_ATHLETE_ID et INTERVALS_API_KEY"
    echo ""
    echo "   Clé API → https://intervals.icu/settings (bas de page)"
    exit 1
fi

# 3. Installer les dépendances si besoin
echo ""
echo "📦 Vérification des dépendances…"
pip install -q -r requirements.txt

# 4. Collecter les données
# Ajoute FETCH_INTERVALS=1 dans .env (ou en variable d'env) pour télécharger les intervalles
echo ""
echo "📥 Collecte des données (Intervals.icu)…"
INTERVALS_FLAG=""
[ "${FETCH_INTERVALS:-0}" = "1" ] && INTERVALS_FLAG="--fetch-intervals"

python3 fetch_training_data.py \
    --start "${START:-2025-12-01}" \
    --end   "${END:-$(date +%Y-%m-%d)}" \
    --fcm   "${FCM:-196}" \
    --lthr  "${LTHR:-181}" \
    --out   training_data.json \
    ${INTERVALS_FLAG}

echo ""
echo "✅ Terminé !"
echo "   📄 Données → training_data.json"
