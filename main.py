from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from PySide6.QtWidgets import QApplication

from lifecanvas.policy_audit import install_policy_audit
from lifecanvas.guided_ui import LifeCanvasWindow


def main() -> None:
    # Patch supported calculation rules before the first dashboard calculation.
    install_policy_audit()
    app = QApplication.instance() or QApplication([])
    window = LifeCanvasWindow()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()
