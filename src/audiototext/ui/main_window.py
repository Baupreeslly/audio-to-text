"""Fenêtre principale : interface volontairement simple et guidée.

Parcours utilisateur :
  1. Choisir un fichier audio (bouton ou glisser-déposer).
  2. (Optionnel) ajuster le modèle et la langue.
  3. Cliquer sur « Transcrire ».
  4. Relire/corriger le texte, puis « Enregistrer… ».
"""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
    QMessageBox, QProgressBar, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from .. import APP_TITLE, __version__, config, exporters, models
from ..transcriber import SUPPORTED_EXTENSIONS
from .worker import TranscribeWorker

# Langues proposées : "Détection automatique" en tête, puis les plus courantes.
LANGUAGES = [
    ("Détection automatique", "auto"),
    ("Français", "fr"),
    ("Anglais", "en"),
    ("Espagnol", "es"),
    ("Allemand", "de"),
    ("Italien", "it"),
    ("Portugais", "pt"),
    ("Néerlandais", "nl"),
    ("Arabe", "ar"),
    ("Russe", "ru"),
    ("Chinois", "zh"),
    ("Japonais", "ja"),
]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.cfg = config.load()
        self.audio_path: str | None = None
        self.worker: TranscribeWorker | None = None
        self.result_meta: dict = {}

        self.setWindowTitle(f"{APP_TITLE}")
        self.setMinimumSize(720, 620)
        self.setAcceptDrops(True)
        self._build_ui()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(14)

        # Titre
        title = QLabel(APP_TITLE)
        f = QFont()
        f.setPointSize(20)
        f.setBold(True)
        title.setFont(f)
        subtitle = QLabel("Transcription audio → texte · 100% hors ligne")
        subtitle.setStyleSheet("color: gray;")
        root.addWidget(title)
        root.addWidget(subtitle)

        # Zone de dépôt / sélection du fichier
        self.drop_zone = QFrame()
        self.drop_zone.setFrameShape(QFrame.StyledPanel)
        self.drop_zone.setStyleSheet(
            "QFrame { border: 2px dashed #9aa0a6; border-radius: 10px; "
            "padding: 18px; }"
        )
        dz = QVBoxLayout(self.drop_zone)
        dz.setAlignment(Qt.AlignCenter)
        self.file_label = QLabel("Glissez un fichier audio ici")
        self.file_label.setAlignment(Qt.AlignCenter)
        ff = QFont()
        ff.setPointSize(12)
        self.file_label.setFont(ff)
        choose_btn = QPushButton("Choisir un fichier audio…")
        choose_btn.clicked.connect(self._choose_file)
        dz.addWidget(self.file_label)
        dz.addSpacing(8)
        dz.addWidget(choose_btn, alignment=Qt.AlignCenter)
        root.addWidget(self.drop_zone)

        # Options : modèle + langue
        opts = QHBoxLayout()
        opts.addWidget(QLabel("Modèle :"))
        self.model_combo = QComboBox()
        for m in models.CATALOG:
            self.model_combo.addItem(m["label"], m["size"])
            self.model_combo.setItemData(
                self.model_combo.count() - 1, m["hint"], Qt.ToolTipRole
            )
        self._select_combo_data(self.model_combo, self.cfg["model"])
        self.model_combo.currentIndexChanged.connect(self._on_options_changed)
        opts.addWidget(self.model_combo, stretch=2)

        opts.addSpacing(12)
        opts.addWidget(QLabel("Langue :"))
        self.lang_combo = QComboBox()
        for label, code in LANGUAGES:
            self.lang_combo.addItem(label, code)
        self._select_combo_data(self.lang_combo, self.cfg["language"])
        self.lang_combo.currentIndexChanged.connect(self._on_options_changed)
        opts.addWidget(self.lang_combo, stretch=1)
        root.addLayout(opts)

        # Boutons d'action
        actions = QHBoxLayout()
        self.transcribe_btn = QPushButton("  Transcrire  ")
        self.transcribe_btn.setMinimumHeight(40)
        bf = QFont()
        bf.setPointSize(12)
        bf.setBold(True)
        self.transcribe_btn.setFont(bf)
        self.transcribe_btn.clicked.connect(self._start)
        self.transcribe_btn.setEnabled(False)

        self.cancel_btn = QPushButton("Annuler")
        self.cancel_btn.setMinimumHeight(40)
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.hide()

        actions.addWidget(self.transcribe_btn, stretch=1)
        actions.addWidget(self.cancel_btn)
        root.addLayout(actions)

        # Progression
        self.progress = QProgressBar()
        self.progress.setValue(0)
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: gray;")
        root.addWidget(self.progress)
        root.addWidget(self.status_label)

        # Résultat éditable
        root.addWidget(QLabel("Résultat (modifiable) :"))
        self.result_edit = QTextEdit()
        self.result_edit.setPlaceholderText(
            "La transcription apparaîtra ici. Vous pourrez la corriger avant "
            "de l'enregistrer."
        )
        root.addWidget(self.result_edit, stretch=1)

        # Bas de page : enregistrer / effacer
        bottom = QHBoxLayout()
        self.save_btn = QPushButton("Enregistrer le texte…")
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setEnabled(False)
        clear_btn = QPushButton("Effacer")
        clear_btn.clicked.connect(self._clear_result)
        bottom.addWidget(self.save_btn, stretch=1)
        bottom.addWidget(clear_btn)
        root.addLayout(bottom)

        version = QLabel(f"v{__version__}")
        version.setStyleSheet("color: #b0b0b0;")
        version.setAlignment(Qt.AlignRight)
        root.addWidget(version)

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _select_combo_data(combo: QComboBox, data) -> None:
        idx = combo.findData(data)
        combo.setCurrentIndex(idx if idx >= 0 else 0)

    def _on_options_changed(self, *_) -> None:
        self.cfg["model"] = self.model_combo.currentData()
        self.cfg["language"] = self.lang_combo.currentData()
        config.save(self.cfg)

    def _set_file(self, path: str) -> None:
        self.audio_path = path
        self.file_label.setText(f"📄  {Path(path).name}")
        self.transcribe_btn.setEnabled(True)
        self.cfg["last_input_dir"] = str(Path(path).parent)
        config.save(self.cfg)

    # -------------------------------------------------------- glisser-déposer
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path and Path(path).suffix.lower() in SUPPORTED_EXTENSIONS:
                self._set_file(path)
                return
        QMessageBox.warning(
            self, "Format non reconnu",
            "Ce fichier ne semble pas être un fichier audio pris en charge.",
        )

    # ------------------------------------------------------------- actions
    def _choose_file(self) -> None:
        patterns = " ".join(f"*{e}" for e in SUPPORTED_EXTENSIONS)
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir un fichier audio",
            self.cfg.get("last_input_dir", str(Path.home())),
            f"Fichiers audio ({patterns});;Tous les fichiers (*)",
        )
        if path:
            self._set_file(path)

    def _start(self) -> None:
        if not self.audio_path:
            return
        if not os.path.exists(self.audio_path):
            QMessageBox.warning(self, "Fichier introuvable",
                                "Le fichier sélectionné n'existe plus.")
            return

        self.result_edit.clear()
        self._set_running(True)

        self.worker = TranscribeWorker(
            audio_path=self.audio_path,
            model_size=self.model_combo.currentData(),
            language=self.lang_combo.currentData(),
            compute_type=self.cfg.get("compute_type", "int8"),
            root=str(config.models_dir()),
        )
        self.worker.status.connect(self.status_label.setText)
        self.worker.progress.connect(self._on_progress)
        self.worker.segment.connect(self._append_segment)
        self.worker.done.connect(self._on_done)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(lambda: self._set_running(False))
        self.worker.start()

    def _cancel(self) -> None:
        if self.worker and self.worker.isRunning():
            self.status_label.setText("Annulation…")
            self.worker.request_stop()

    def _on_progress(self, value: int) -> None:
        if value < 0:
            self.progress.setRange(0, 0)  # animation indéterminée
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(value)

    def _append_segment(self, text: str) -> None:
        cursor = self.result_edit.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(text + " ")
        self.result_edit.setTextCursor(cursor)

    def _on_done(self, text: str, meta: dict) -> None:
        # On remplace par le texte complet propre (au cas où l'affichage
        # incrémental aurait des espaces superflus).
        self.result_edit.setPlainText(text)
        self.result_meta = meta
        self.save_btn.setEnabled(bool(text))
        lang = meta.get("language", "?")
        self.status_label.setText(f"Terminé · langue détectée : {lang}")

    def _on_error(self, message: str) -> None:
        QMessageBox.critical(self, "Erreur", message)
        self.status_label.setText("Échec.")

    def _set_running(self, running: bool) -> None:
        self.transcribe_btn.setVisible(not running)
        self.cancel_btn.setVisible(running)
        self.model_combo.setEnabled(not running)
        self.lang_combo.setEnabled(not running)
        if not running:
            self.progress.setRange(0, 100)

    def _clear_result(self) -> None:
        self.result_edit.clear()
        self.save_btn.setEnabled(False)
        self.status_label.setText("")
        self.progress.setValue(0)

    def _save(self) -> None:
        text = self.result_edit.toPlainText().strip()
        if not text:
            return
        default_name = "transcription.txt"
        if self.audio_path:
            default_name = Path(self.audio_path).stem + ".txt"
        start_dir = self.cfg.get("last_output_dir", str(Path.home()))
        path, selected = QFileDialog.getSaveFileName(
            self, "Enregistrer la transcription",
            str(Path(start_dir) / default_name),
            "Texte (*.txt);;Word (*.docx);;Markdown (*.md)",
        )
        if not path:
            return

        # Ajoute l'extension du filtre choisi si l'utilisateur l'a omise.
        if Path(path).suffix.lower() not in exporters.EXPORTERS:
            for ext in (".txt", ".docx", ".md"):
                if ext[1:] in selected.lower():
                    path += ext
                    break

        try:
            exporters.export(path, text, self.result_meta)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erreur d'enregistrement", str(exc))
            return

        self.cfg["last_output_dir"] = str(Path(path).parent)
        config.save(self.cfg)
        self.status_label.setText(f"Enregistré : {path}")

    # -------------------------------------------------------------- fermeture
    def closeEvent(self, event) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
            self.worker.wait(3000)
        config.save(self.cfg)
        super().closeEvent(event)
