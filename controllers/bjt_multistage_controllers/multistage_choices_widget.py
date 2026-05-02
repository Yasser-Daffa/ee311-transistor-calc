import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton
from PyQt6.uic import loadUi

# controllers/bjt_multistage_controllers/multistage_choices_widget.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_choices.ui")

from controllers.bjt_multistage_controllers.ce_ce_design_widget import CECEDesignWidget
from controllers.bjt_multistage_controllers.cc_ce_design_widget import CCCEDesignWidget
from controllers.bjt_multistage_controllers.ce_cc_design_widget import CECCDesignWidget
from controllers.bjt_multistage_controllers.buffer_analysis_widget_automated import BufferAnalysisWidget


class MultistageChoicesWidget(QWidget):
    """Main multistage menu/controller.

    Pages expected in multistage_choices.ui:
        page0CECE
        page1CCCE
        page2CECC
        page3BufferSolver
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self.cece_widget = CECEDesignWidget()
        self.ccce_widget = CCCEDesignWidget()
        self.cecc_widget = CECCDesignWidget()
        self.buffer_widget = BufferAnalysisWidget()

        self._embed(self.page0CECE, self.cece_widget)
        self._embed(self.page1CCCE, self.ccce_widget)
        self._embed(self.page2CECC, self.cecc_widget)
        self._embed(self.page3BufferSolver, self.buffer_widget)

        self._setup_buttons()
        self._show_page(0)

    def _setup_buttons(self):
        self._buttons = [
            self.buttonCECE,
            self.buttonCCCE,
            self.buttonCECC,
            self.buttonBufferSolver,
        ]

        for btn in self._buttons:
            btn.setCheckable(True)
            btn.setAutoExclusive(False)

        self.buttonCECE.clicked.connect(lambda: self._show_page(0))
        self.buttonCCCE.clicked.connect(lambda: self._show_page(1))
        self.buttonCECC.clicked.connect(lambda: self._show_page(2))
        self.buttonBufferSolver.clicked.connect(lambda: self._show_page(3))

    def _show_page(self, index):
        self.stackedWidget.setCurrentIndex(index)

        for i, btn in enumerate(self._buttons):
            btn.setChecked(i == index)

    def _embed(self, page, widget):
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

        while layout.count():
            item = layout.takeAt(0)
            old = item.widget()
            if old is not None:
                old.setParent(None)

        layout.addWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MultistageChoicesWidget()
    window.setWindowTitle("Multistage Amplifiers")
    window.show()
    sys.exit(app.exec())
