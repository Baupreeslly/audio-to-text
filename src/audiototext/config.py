"""Gestion des chemins standard XDG et des préférences persistantes.

Tout est stocké dans le répertoire personnel de l'utilisateur, sans droits
administrateur :
  - configuration : ~/.config/audio-to-text/config.json
  - données (modèles) : ~/.local/share/audio-to-text/models/
"""

from __future__ import annotations

import json
import os
from pathlib import Path

APP_NAME = "audio-to-text"

DEFAULTS = {
    "model": "medium",          # small | medium | large-v3
    "language": "auto",         # "auto" ou code ISO (fr, en, ...)
    "compute_type": "int8",     # quantification CPU : rapide et léger
    "last_input_dir": str(Path.home()),
    "last_output_dir": str(Path.home()),
}


def _xdg(env_var: str, default_subpath: str) -> Path:
    """Renvoie un répertoire XDG, en tolérant une variable vide ou absente."""
    base = os.environ.get(env_var) or str(Path.home() / default_subpath)
    return Path(base)


def config_dir() -> Path:
    d = _xdg("XDG_CONFIG_HOME", ".config") / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def data_dir() -> Path:
    d = _xdg("XDG_DATA_HOME", ".local/share") / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def models_dir() -> Path:
    d = data_dir() / "models"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _config_file() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    """Charge les préférences, en complétant avec les valeurs par défaut."""
    cfg = dict(DEFAULTS)
    try:
        stored = json.loads(_config_file().read_text(encoding="utf-8"))
        if isinstance(stored, dict):
            cfg.update({k: v for k, v in stored.items() if k in DEFAULTS})
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        pass
    return cfg


def save(cfg: dict) -> None:
    """Enregistre les préférences (échoue silencieusement si non inscriptible)."""
    try:
        clean = {k: cfg[k] for k in DEFAULTS if k in cfg}
        _config_file().write_text(
            json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    except OSError:
        pass
