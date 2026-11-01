#!/bin/sh
# Genere un fichier .env a partir de .env.example avec des secrets aleatoires.
# Usage : ./scripts/init-env.sh
# Le script refuse d'ecraser un .env existant.
set -eu

cd "$(dirname "$0")/.."

if [ -f .env ]; then
    echo "Erreur : .env existe deja. Supprimez-le ou editez-le manuellement." >&2
    exit 1
fi

if ! command -v openssl >/dev/null 2>&1; then
    echo "Erreur : openssl est requis pour generer les secrets." >&2
    echo "Alternative : renseigner les variables a la main dans .env.example," >&2
    echo "puis copier le fichier vers .env." >&2
    exit 1
fi

umask 077
cp .env.example .env

# Remplace la valeur d'une cle "CLE=" sans toucher aux commentaires.
set_value() {
    key="$1"
    value="$2"
    tmp="$(mktemp)"
    awk -v k="$key" -v v="$value" '
        $0 ~ "^" k "=" { print k "=" v; next }
        { print }
    ' .env > "$tmp"
    mv "$tmp" .env
}

set_value REDIS_PASSWORD "$(openssl rand -hex 32)"
set_value S3_ACCESS_KEY "mp_$(openssl rand -hex 12)"
set_value S3_SECRET_KEY "$(openssl rand -hex 32)"
set_value SESSION_SECRET "$(openssl rand -hex 32)"
set_value DOWNLOAD_SIGNING_SECRET "$(openssl rand -hex 32)"

chmod 600 .env

echo "Fichier .env cree (mode 600) avec des secrets aleatoires."
echo
echo "Prochaines etapes :"
echo "  1. Renseigner PUBLIC_BASE_URL (ex. https://posters.example.com) si besoin."
echo "  2. docker compose up -d --build"
echo "  3. docker compose ps"
