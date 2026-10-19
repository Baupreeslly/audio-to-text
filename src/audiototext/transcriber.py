"""Enveloppe autour de faster-whisper.

Isole la logique de reconnaissance vocale de l'interface graphique :
  - chargement / téléchargement du modèle,
  - transcription d'un fichier avec remontée de la progression.

Le décodage audio est assuré par PyAV (embarqué par faster-whisper), donc
aucun `ffmpeg` système n'est requis. Les formats courants (mp3, wav, m4a, ogg,
flac, opus, et pistes audio de vidéos) sont pris en charge.
"""

from __future__ import annotations

from typing import Callable, Optional

# Extensions proposées dans le sélecteur de fichiers de l'interface.
SUPPORTED_EXTENSIONS = [
    ".mp3", ".wav", ".m4a", ".ogg", ".oga", ".opus",
    ".flac", ".aac", ".wma", ".mp4", ".mkv", ".webm", ".mov",
]


def load_model(model_size: str, compute_type: str, download_root: str,
               local_only: bool = False):
    """Charge un modèle Whisper (le télécharge si nécessaire et autorisé)."""
    from faster_whisper import WhisperModel

    return WhisperModel(
        model_size,
        device="cpu",
        compute_type=compute_type,
        download_root=download_root,
        local_files_only=local_only,
    )


def transcribe(model, audio_path: str, language: Optional[str],
               on_progress: Callable[[float], None] | None = None,
               on_segment: Callable[[str], None] | None = None,
               should_stop: Callable[[], bool] | None = None) -> dict:
    """Transcrit un fichier audio.

    Renvoie un dict : {"text", "language", "duration", "segments"}.
    Les callbacks permettent à la GUI d'afficher la progression en temps réel.
    `language=None` (ou "auto") laisse Whisper détecter la langue.
    """
    lang = None if (language in (None, "auto", "")) else language

    segments, info = model.transcribe(
        audio_path,
        language=lang,
        beam_size=5,
        # Le filtre d'activité vocale (VAD) supprime les silences et améliore
        # nettement la fiabilité sur les enregistrements réels.
        vad_filter=True,
    )

    parts: list[str] = []
    collected: list[dict] = []
    duration = info.duration or 0.0

    for seg in segments:
        if should_stop and should_stop():
            break
        text = seg.text.strip()
        parts.append(text)
        collected.append({"start": seg.start, "end": seg.end, "text": text})
        if on_segment:
            on_segment(text)
        if on_progress and duration:
            on_progress(min(1.0, seg.end / duration))

    if on_progress:
        on_progress(1.0)

    return {
        "text": " ".join(parts).strip(),
        "language": info.language,
        "duration": duration,
        "segments": collected,
    }
