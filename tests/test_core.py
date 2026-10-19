"""Tests unitaires légers du cœur non graphique (sans dépendances lourdes).

Exécution :  python -m pytest    ou    python tests/test_core.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from audiototext import exporters, models  # noqa: E402


def test_model_catalog_non_empty():
    assert models.CATALOG
    assert {"small", "medium", "large-v3"} <= {m["size"] for m in models.CATALOG}


def test_repo_id():
    assert models.repo_id("medium") == "Systran/faster-whisper-medium"


def test_is_downloaded_false_on_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        assert models.is_downloaded("medium", d) is False


def test_exporters_txt_and_md(tmp_path=None):
    d = Path(tempfile.mkdtemp())
    meta = {"language": "fr", "duration": 65, "source": "audio.mp3"}

    txt = d / "out.txt"
    exporters.export(txt, "Bonjour le monde.", meta)
    assert "Bonjour le monde." in txt.read_text(encoding="utf-8")

    md = d / "out.md"
    exporters.export(md, "Bonjour le monde.", meta)
    content = md.read_text(encoding="utf-8")
    assert content.startswith("# Transcription")
    assert "Langue détectée : fr" in content


def test_duration_formatting():
    assert exporters._fmt_duration(None) == "inconnue"
    assert exporters._fmt_duration(5) == "5 s"
    assert "min" in exporters._fmt_duration(65)
    assert "h" in exporters._fmt_duration(3700)


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"ok  {name}")
    print("Tous les tests sont passés.")
