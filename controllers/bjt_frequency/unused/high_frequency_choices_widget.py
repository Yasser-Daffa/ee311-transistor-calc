import os
import sys

from PyQt6.QtWidgets import QWidget, QButtonGroup
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from controllers.bjt_frequency.ce_high_frequency_widget import CEHighFrequencyWidget
from controllers.bjt_frequency.cc_high_frequency_widget import CCHighFrequencyWidget
from controllers.bjt_frequency.high_frequency_directly_given_widget import HighFrequencyDirectlyGivenWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "high_frequency_choices.ui")


class HighFrequencyChoicesWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        for button in [self.buttonCE, self.buttonCC, self.buttonDirect]:
            button.setCheckable(True)
            self.mode_group.addButton(button)

        self.buttonCE.setChecked(True)

        self.load_pages()
        self.stackedWidget.setCurrentIndex(0)

    def connect_signals(self):
        self.buttonCE.clicked.connect(lambda: self.show_page(0))
        self.buttonCC.clicked.connect(lambda: self.show_page(1))
        self.buttonDirect.clicked.connect(lambda: self.show_page(2))

    def load_pages(self):
        """
        Remove placeholder pages from Qt Designer and insert real widgets.
        """

        while self.stackedWidget.count() > 0:
            old_page = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(old_page)
            old_page.deleteLater()

        self.ce_high_page = CEHighFrequencyWidget()
        self.cc_high_page = CCHighFrequencyWidget()
        self.direct_high_page = HighFrequencyDirectlyGivenWidget()

        self.stackedWidget.addWidget(self.ce_high_page)
        self.stackedWidget.addWidget(self.cc_high_page)
        self.stackedWidget.addWidget(self.direct_high_page)

    def show_page(self, index):
        self.stackedWidget.setCurrentIndex(index)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = HighFrequencyChoicesWidget()
    w.show()
    sys.exit(app.exec())