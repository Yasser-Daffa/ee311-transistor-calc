import os
import sys

from PyQt6.QtWidgets import QWidget, QButtonGroup, QLabel, QVBoxLayout
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from controllers.bjt_frequency.ce_cc_multistage_frequency_widget import (
    CECCMultistageFrequencyWidget,
)

from controllers.bjt_frequency.cutoff_frequency import CutoffFrequencyWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(
    BASE_DIR,
    "..",
    "..",
    "ui",
    "frequency",
    "multistage_frequency_choices.ui",
)


class PlaceholderPage(QWidget):
    def __init__(self, text):
        super().__init__()

        layout = QVBoxLayout(self)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 18px;
                font-weight: 600;
                qproperty-alignment: AlignCenter;
            }
        """)

        layout.addWidget(label)


class MultistageFrequencyChoicesWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.button_to_page = {}

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        self.setup_button_group()
        self.load_pages()

        # Default page
        self.show_page(self.ce_cc_page)
        self.buttonCECC.setChecked(True)

    def setup_button_group(self):
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        buttons = [
            self.buttonCECE,
            self.buttonCCCE,
            self.buttonCECC,
            self.buttonCutoffFreqPoints,
        ]

        for button in buttons:
            button.setCheckable(True)
            self.mode_group.addButton(button)

    def connect_signals(self):
        self.buttonCECE.clicked.connect(lambda: self.show_page(self.ce_ce_page))
        self.buttonCCCE.clicked.connect(lambda: self.show_page(self.cc_ce_page))
        self.buttonCECC.clicked.connect(lambda: self.show_page(self.ce_cc_page))
        self.buttonCutoffFreqPoints.clicked.connect(lambda: self.show_page(self.cutoff_frequency_points_page))

    # ------------------------------------------------------------
    # Page loading
    # ------------------------------------------------------------

    def load_pages(self):
        """
        Remove placeholder pages from Qt Designer and insert real pages.

        Pages:
        CE-CE              → placeholder for now
        CC-CE              → placeholder for now
        CE-CC              → real page
        Cutoff freq points → placeholder for now
        """

        while self.stackedWidget.count() > 0:
            old_page = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(old_page)
            old_page.deleteLater()

        self.ce_ce_page = PlaceholderPage(
            "CE-CE Multistage Frequency page is not built yet.\n\n"
            "This will later calculate CE-CE low/high cutoff points."
        )

        self.cc_ce_page = PlaceholderPage(
            "CC-CE Multistage Frequency page is not built yet.\n\n"
            "This will later calculate CC-CE low/high cutoff points."
        )

        self.ce_cc_page = CECCMultistageFrequencyWidget()

        self.cutoff_frequency_points_page = CutoffFrequencyWidget()

        self.stackedWidget.addWidget(self.ce_ce_page)
        self.stackedWidget.addWidget(self.cc_ce_page)
        self.stackedWidget.addWidget(self.ce_cc_page)
        self.stackedWidget.addWidget(self.cutoff_frequency_points_page)

    def show_page(self, page):
        self.stackedWidget.setCurrentWidget(page)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = MultistageFrequencyChoicesWidget()
    w.show()
    sys.exit(app.exec())