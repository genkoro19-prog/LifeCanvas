from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from lifecanvas.revision_ui import run_app


if __name__ == "__main__":
    run_app()
