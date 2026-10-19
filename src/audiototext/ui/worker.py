"""Thread de travail : charge le modèle et transcrit sans figer l'interface.

Le chargement du modèle (et son éventuel premier téléchargement) ainsi que la
transcription sont exécutés hors du thread graphique. La communication se fait
uniquement par signaux Qt, ce qui garantit une interface fluide.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from .. import models, transcriber


class TranscribeWorker(QThread):
    # Message d'état lisible (« Chargement du modèle… », etc.).
    status = Signal(str)
    # Progression 0–100, ou -1 pour une barre indéterminée.
    progress = Signal(int)
    # Texte d'un segment dès qu'il est disponible (affichage au fil de l'eau).
    segment = Signal(str)
    # Fin réussie : texte complet + métadonnées.
    done = Signal(str, dict)
    # Erreur : message destiné à l'utilisateur.
    error = Signal(str)

    def __init__(self, audio_path: str, model_size: str, language: str,
                 compute_type: str, root: str):
        super().__init__()
        self.audio_path = audio_path
        self.model_size = model_size
        self.language = language
        self.compute_type = compute_type
        self.root = root
        self._stop = False

    def request_stop(self) -> None:
        self._stop = True

    def run(self) -> None:  # exécuté dans le thread
        try:
            already = models.is_downloaded(self.model_size, self.root)
            if already:
                self.status.emit("Chargement du modèle…")
            else:
                self.status.emit(
                    "Téléchargement du modèle (une seule fois, nécessite "
                    "Internet)…"
                )
            self.progress.emit(-1)  # indéterminé pendant le chargement

            model = transcriber.load_model(
                self.model_size, self.compute_type, self.root,
                local_only=False,
            )

            if self._stop:
                return

            self.status.emit("Transcription en cours…")
            self.progress.emit(0)

            result = transcriber.transcribe(
                model,
                self.audio_path,
                self.language,
                on_progress=lambda f: self.progress.emit(int(f * 100)),
                on_segment=lambda t: self.segment.emit(t),
                should_stop=lambda: self._stop,
            )

            if self._stop:
                return

            self.status.emit("Terminé.")
            self.done.emit(result["text"], {
                "language": result["language"],
                "duration": result["duration"],
                "source": self.audio_path,
            })
        except Exception as exc:  # noqa: BLE001 — remonté à l'utilisateur
            self.error.emit(self._friendly_error(exc))

    @staticmethod
    def _friendly_error(exc: Exception) -> str:
        msg = str(exc)
        low = msg.lower()
        if any(k in low for k in ("connection", "resolve", "network",
                                  "timed out", "offline", "huggingface")):
            return (
                "Impossible de télécharger le modèle. Une connexion Internet "
                "est nécessaire lors de la toute première utilisation. "
                "Vérifiez votre connexion puis réessayez.\n\nDétail : " + msg
            )
        return "La transcription a échoué.\n\nDétail : " + msg
