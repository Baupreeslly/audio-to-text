"""Catalogue des modèles Whisper et détection de leur présence locale.

Les modèles faster-whisper sont publiés par Systran sur Hugging Face et mis en
cache dans `models_dir()`. On peut savoir si un modèle est déjà téléchargé (donc
utilisable hors ligne) en cherchant le fichier `model.bin` dans le cache, sans
avoir à charger le modèle en mémoire.
"""

from __future__ import annotations

from pathlib import Path

# Ordre d'affichage dans l'interface.
CATALOG = [
    {
        "size": "small",
        "label": "Rapide (small)",
        "hint": "≈ 0,5 Go RAM · rapide · qualité correcte",
    },
    {
        "size": "medium",
        "label": "Équilibré (medium) — recommandé",
        "hint": "≈ 1,5 Go RAM · bon compromis fiabilité / vitesse",
    },
    {
        "size": "large-v3",
        "label": "Qualité maximale (large-v3)",
        "hint": "≈ 3 Go RAM · le plus fiable · plus lent sur CPU",
    },
]

_LABEL_BY_SIZE = {m["size"]: m["label"] for m in CATALOG}


def repo_id(size: str) -> str:
    return f"Systran/faster-whisper-{size}"


def label_for(size: str) -> str:
    return _LABEL_BY_SIZE.get(size, size)


def is_downloaded(size: str, root: str | Path) -> bool:
    """Vrai si le modèle est présent localement (utilisable hors ligne)."""
    cache_name = "models--" + repo_id(size).replace("/", "--")
    snapshots = Path(root) / cache_name / "snapshots"
    if not snapshots.is_dir():
        return False
    return any(snapshots.glob("*/model.bin"))
