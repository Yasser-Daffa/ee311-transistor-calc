import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.uic import loadUi

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from controllers.bjt_amplifiers_controllers.multistage_design_controller import MultistageDesignWidget

CHOICE_UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_amp_choice.ui")


class MultistageAmpChoiceWidget(QWidget):
    """Small wrapper: top buttons choose topology, same design widget stays embedded."""

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(CHOICE_UI_PATH, self)

        self.design_widget = MultistageDesignWidget("CE-CE")
        self._embed_design_widget()
        self._setup_buttons()
        self.select_topology("CE-CE")

    def _embed_design_widget(self):
        page = getattr(self, "page0CECE", None)
        if page is None:
            return

        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(self.design_widget)

        if hasattr(self, "stackedWidget"):
            self.stackedWidget.setCurrentWidget(page)

    def _setup_buttons(self):
        self._buttons = {
            "CE-CE": getattr(self, "buttonCECE", None),
            "CC-CE": getattr(self, "buttonCCCE", None),
            "CE-CC": getattr(self, "buttonCECC", None),
        }

        for topology, button in self._buttons.items():
            if isinstance(button, QPushButton):
                button.setCheckable(True)
                button.setAutoExclusive(False)
                button.clicked.connect(lambda checked=False, t=topology: self.select_topology(t))

    def select_topology(self, topology):
        for name, button in self._buttons.items():
            if isinstance(button, QPushButton):
                button.setChecked(name == topology)

        self.design_widget.set_topology(topology)

        if hasattr(self, "stackedWidget") and hasattr(self, "page0CECE"):
            self.stackedWidget.setCurrentWidget(self.page0CECE)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MultistageAmpChoiceWidget()
    w.show()
    sys.exit(app.exec())
