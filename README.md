# Audio → Texte

Transcription de fichiers **audio en texte**, **100 % hors ligne**, avec une
interface graphique simple pour **Linux (Debian / Ubuntu / Linux Mint…)**.

Conçu pour fonctionner **sans `sudo` ni `apt`** : aucune dépendance système à
installer. Le moteur de reconnaissance vocale est
[Whisper](https://github.com/openai/whisper) (via
[faster-whisper](https://github.com/SYSTRAN/faster-whisper)), exécuté
localement sur le processeur.

## Fonctionnalités

- 🔒 **Hors ligne** : une fois le modèle téléchargé (au premier lancement),
  plus aucune connexion n'est requise. Vos fichiers ne quittent jamais la
  machine.
- 🖱️ **Interface intuitive** : glissez un fichier, cliquez sur *Transcrire*.
- 🌍 **Multilingue** : détection automatique de la langue (~90 langues).
- ⚙️ **Modèle réglable** : *small* (rapide) → *medium* (recommandé) →
  *large-v3* (qualité maximale).
- 💾 **Exports** : texte brut (`.txt`), Word (`.docx`), Markdown (`.md`).
- 🎧 **Formats acceptés** : mp3, wav, m4a, ogg, flac, opus… et pistes audio de
  vidéos (mp4, mkv, webm).

## Installation & utilisation

### Option A — AppImage (recommandé pour les utilisateurs)

1. Récupérez le fichier `Audio-Texte-x86_64.AppImage`.
2. Rendez-le exécutable puis lancez-le :
   ```bash
   chmod +x Audio-Texte-x86_64.AppImage
   ./Audio-Texte-x86_64.AppImage
   ```
   (ou clic droit → *Autoriser l'exécution* → double-clic)

Aucune installation, aucun droit administrateur.

> **Si l'AppImage refuse de démarrer** (« Permission denied » sur un
> `AppRun` dans `/tmp`) : votre `/tmp` est monté `noexec` et FUSE est absent.
> Lancez alors avec un dossier temporaire exécutable :
> ```bash
> TMPDIR=$HOME/.cache/a2t APPIMAGE_EXTRACT_AND_RUN=1 ./Audio-Texte-x86_64.AppImage
> ```

### Option B — depuis les sources (développeurs)

Nécessite `python3` (≥ 3.9) avec le module `venv`. Aucun autre prérequis
système.

```bash
./run.sh
```

Le script crée un environnement virtuel isolé, installe les dépendances via
`pip`, puis lance l'application.

> **Premier lancement** : le modèle choisi est téléchargé une seule fois
> (nécessite Internet), puis mis en cache dans
> `~/.local/share/audio-to-text/models/`. Les lancements suivants sont
> entièrement hors ligne.

## Construire l'AppImage

Sur une machine avec accès Internet (aucun `sudo` requis) :

```bash
./packaging/build_appimage.sh
```

Le résultat est déposé dans `dist/`.

## Architecture

```
src/audiototext/
├── app.py            # point d'entrée (QApplication)
├── config.py         # préférences & chemins XDG (~/.config, ~/.local/share)
├── models.py         # catalogue des modèles + détection du cache local
├── transcriber.py    # enveloppe faster-whisper (chargement + transcription)
├── exporters.py      # écriture .txt / .md / .docx
└── ui/
    ├── main_window.py  # fenêtre et parcours utilisateur
    └── worker.py       # thread de transcription (interface fluide)
```

**Choix techniques**

- *faster-whisper* (CTranslate2) : rapide et sobre en mémoire sur CPU.
- *PyAV* (embarqué par faster-whisper) décode l'audio : **pas de `ffmpeg`
  système requis**.
- *PySide6* : les wheels pip embarquent Qt → aucune bibliothèque système.
- Filtre **VAD** activé : supprime les silences, améliore la fiabilité.

## Configuration matérielle

Fonctionne sur CPU (aucun GPU requis). Ordre de grandeur pour ~1 min d'audio,
selon le modèle et la machine :

| Modèle    | RAM approx. | Vitesse (CPU) | Fiabilité      |
|-----------|-------------|---------------|----------------|
| small     | ~0,5 Go     | rapide        | correcte       |
| medium    | ~1,5 Go     | moyenne       | bonne (défaut) |
| large-v3  | ~3 Go       | lente         | maximale       |

## Développement

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m pytest        # tests du cœur (sans dépendances lourdes)
```

## Licence

MIT — voir [LICENSE](LICENSE).
