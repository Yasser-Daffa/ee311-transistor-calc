# controllers/bjt_amplifiers_controllers/design_analysis_menu_widget.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.uic import loadUi

from controllers.bjt_amplifiers_controllers.cc_design_widget
from controllers.bjt_amplifiers_controllers.cc_analysis_widget import CCAnalysisWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "design_analysis_menu.ui")


class DesignAnalysisMenuWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self._embed(self.page0Design, CCDesignWidget())
        self._embed(self.page1Analysis, CCAnalysisWidget())

        self.buttonDesign.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.buttonAnalysis.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))

        self.stackedWidget.setCurrentIndex(0)

    def _embed(self, page, widget):
        layout = page.layout()

        if layout is None:
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DesignAnalysisMenuWidget()
    window.setWindowTitle("CC Design / Analysis")
    window.show()
    sys.exit(app.exec())