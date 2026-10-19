#!/usr/bin/env bash
#
# Construit une AppImage autonome, SANS sudo ni apt.
#
# Principe :
#   1. Télécharge un interpréteur Python « relocatable » (python-build-standalone).
#   2. Y installe l'application et toutes ses dépendances via pip.
#   3. Ajoute AppRun + fichier .desktop + icône.
#   4. Emballe le tout avec appimagetool (lui-même une AppImage, aucun install).
#
# Prérequis : une connexion Internet (uniquement au moment de la construction),
#             bash, tar, curl. Aucun privilège administrateur.
#
# Résultat : dist/Audio-Texte-x86_64.AppImage
#
set -euo pipefail

# --- Versions épinglées (modifiables) -------------------------------------
PY_VERSION="3.11.9"
PBS_TAG="20240814"          # release python-build-standalone
ARCH="x86_64"
# --------------------------------------------------------------------------

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$ROOT/appimage-build"
APPDIR="$BUILD/AppDir"
DIST="$ROOT/dist"
CACHE="$BUILD/cache"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr" "$DIST" "$CACHE"

PBS_URL="https://github.com/astral-sh/python-build-standalone/releases/download/${PBS_TAG}/cpython-${PY_VERSION}+${PBS_TAG}-${ARCH}-unknown-linux-gnu-install_only.tar.gz"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"

echo "→ [1/4] Récupération de Python relocatable ($PY_VERSION)…"
if [ ! -f "$CACHE/python.tar.gz" ]; then
    curl -L --fail -o "$CACHE/python.tar.gz" "$PBS_URL"
fi
tar -xzf "$CACHE/python.tar.gz" -C "$BUILD"
# L'archive « install_only » se décompresse dans un dossier « python/ ».
cp -a "$BUILD/python/." "$APPDIR/usr/"
rm -rf "$BUILD/python"

PYBIN="$APPDIR/usr/bin/python3"

echo "→ [2/4] Installation de l'application et des dépendances…"
"$PYBIN" -m pip install --upgrade pip
"$PYBIN" -m pip install "$ROOT"

echo "→ [3/4] Ajout d'AppRun, du .desktop et de l'icône…"
cp "$ROOT/packaging/appimage/AppRun" "$APPDIR/AppRun"
chmod +x "$APPDIR/AppRun"
cp "$ROOT/packaging/appimage/audio-to-text.desktop" "$APPDIR/audio-to-text.desktop"
cp "$ROOT/packaging/appimage/audio-to-text.svg" "$APPDIR/audio-to-text.svg"

# Embarque les bibliothèques xcb/xkb dont dépend le plugin « xcb » de Qt.
# Le wheel PySide6 ne les fournit pas ; elles manquent souvent sur les postes
# cibles (notamment libxcb-cursor.so.0, requis depuis Qt 6.5). On les copie
# depuis la machine de construction ; AppRun les expose via LD_LIBRARY_PATH.
echo "    · embarquement des bibliothèques xcb/xkb…"
X11LIBS="$APPDIR/usr/lib/x11"
mkdir -p "$X11LIBS"
QXCB="$(find "$APPDIR/usr/lib" -path '*/PySide6/Qt/plugins/platforms/libqxcb.so' | head -1)"
if [ -z "$QXCB" ]; then
    echo "Erreur : plugin Qt xcb introuvable dans l'AppDir." >&2
    exit 1
fi
ldd "$QXCB" | awk '/(libxcb|libxkbcommon)/ && / => \// {print $3}' \
    | sort -u | while read -r lib; do
        [ -f "$lib" ] && cp -Lv "$lib" "$X11LIBS/"
    done

echo "→ [4/4] Emballage avec appimagetool…"
if [ ! -f "$CACHE/appimagetool" ]; then
    curl -L --fail -o "$CACHE/appimagetool" "$APPIMAGETOOL_URL"
    chmod +x "$CACHE/appimagetool"
fi
# appimagetool s'auto-extrait dans $TMPDIR. Sur les systèmes où /tmp est monté
# « noexec », son propre AppRun ne peut pas s'exécuter. On redirige donc
# l'extraction vers un dossier local exécutable.
EXTRACT_TMP="$BUILD/tmp"
mkdir -p "$EXTRACT_TMP"
# --appimage-extract-and-run : fonctionne même sans FUSE installé.
ARCH="$ARCH" TMPDIR="$EXTRACT_TMP" APPIMAGE_EXTRACT_AND_RUN=1 \
    "$CACHE/appimagetool" --appimage-extract-and-run \
    "$APPDIR" "$DIST/Audio-Texte-${ARCH}.AppImage"

echo
echo "✓ AppImage prête : $DIST/Audio-Texte-${ARCH}.AppImage"
echo "  Distribuez ce fichier. L'utilisateur fait : chmod +x puis double-clic."
