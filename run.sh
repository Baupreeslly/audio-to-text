#!/usr/bin/env bash
#
# Lance l'application depuis les sources, SANS sudo ni apt.
#
# Sur beaucoup de systèmes Debian/Ubuntu, le paquet « python3-venv » n'est pas
# installé et `python3 -m venv` ne peut pas amorcer pip (ensurepip absent).
# Comme on ne peut pas utiliser apt, ce script contourne le problème :
#   - crée le venv même sans ensurepip (option --without-pip),
#   - amorce pip via get-pip.py (téléchargé une seule fois).
#
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
CACHE="$VENV/.cache"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Erreur : python3 est introuvable." >&2
    exit 1
fi

# --- Création du venv (tolère l'absence du paquet python3-venv) ------------
if [ ! -x "$VENV/bin/python3" ]; then
    echo "→ Création de l'environnement virtuel ($VENV)…"
    if python3 -m venv "$VENV" 2>/dev/null; then
        :
    else
        echo "  ensurepip indisponible → création sans pip, puis amorçage."
        rm -rf "$VENV"
        python3 -m venv --without-pip "$VENV"
    fi
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

# --- Amorçage de pip si nécessaire -----------------------------------------
if ! python -m pip --version >/dev/null 2>&1; then
    echo "→ Amorçage de pip (téléchargement de get-pip.py)…"
    mkdir -p "$CACHE"
    if [ ! -f "$CACHE/get-pip.py" ]; then
        if command -v curl >/dev/null 2>&1; then
            curl -fsSL https://bootstrap.pypa.io/get-pip.py -o "$CACHE/get-pip.py"
        elif command -v wget >/dev/null 2>&1; then
            wget -qO "$CACHE/get-pip.py" https://bootstrap.pypa.io/get-pip.py
        else
            echo "Erreur : ni curl ni wget disponibles pour amorcer pip." >&2
            exit 1
        fi
    fi
    python "$CACHE/get-pip.py"
fi

echo "→ Vérification des dépendances…"
python -m pip install --upgrade pip >/dev/null
python -m pip install -e .

echo "→ Démarrage de l'application…"
exec python -m audiototext
