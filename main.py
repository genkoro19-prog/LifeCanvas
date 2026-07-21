from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from PySide6.QtWidgets import QApplication

from lifecanvas.completion_audit import install_completion_audit
from lifecanvas.guided_ui import LifeCanvasWindow


def main() -> None:
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    install_completion_audit(window)
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
