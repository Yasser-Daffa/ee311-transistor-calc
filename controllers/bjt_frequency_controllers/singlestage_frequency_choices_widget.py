import os
import sys

from PyQt6.QtWidgets import QWidget, QButtonGroup, QLabel, QVBoxLayout
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from controllers.bjt_frequency_controllers.ce_low_high_frequency_widget import CELowHighFrequencyWidget
from controllers.bjt_frequency_controllers.cc_low_high_frequency_widget import CCLowHighFrequencyWidget
from controllers.bjt_frequency_controllers.high_frequency_directly_given_widget import HighFrequencyDirectlyGivenWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "singlestage_frequency_choices.ui")


class PlaceholderPage(QWidget):
    """ self expalanatory :) """
    def __init__(self, text):
        super().__init__()

        layout = QVBoxLayout(self)
        label = QLabel(text)
        label.setStyleSheet("""
            QLabel {
                color: #64748b;
                font-size: 18px;
                font-weight: 600;
                qproperty-alignment: AlignCenter;
            }
        """)
        layout.addWidget(label)


class SingleStageFrequencyChoicesWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        for button in [self.buttonCE, self.buttonCC, self.buttonDirectRpi]:
            button.setCheckable(True)
            self.mode_group.addButton(button)

        self.buttonCE.setChecked(True)

        self.load_pages()
        self.stackedWidget.setCurrentIndex(0)

    def connect_signals(self):
        self.buttonCE.clicked.connect(lambda: self.show_page(0))
        self.buttonCC.clicked.connect(lambda: self.show_page(1))
        self.buttonDirectRpi.clicked.connect(lambda: self.show_page(2))

    def load_pages(self):
        """
        Remove placeholder pages from Qt Designer and insert real widgets. (after I add freq page)
        """

        while self.stackedWidget.count() > 0:
            old_page = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(old_page)
            old_page.deleteLater()

        self.ce_low_high_page = CELowHighFrequencyWidget()
        self.cc_low_high_page = CCLowHighFrequencyWidget()
        self.direct_Rpi_page = HighFrequencyDirectlyGivenWidget()
        self.direct_low_freq_page = PlaceholderPage(
            "Direct Low-Frequency Points page is not built yet.\n"
            "Use CE Stage or CC Stage for now."
        )

        self.stackedWidget.addWidget(self.ce_low_high_page)
        self.stackedWidget.addWidget(self.cc_low_high_page)
        self.stackedWidget.addWidget(self.direct_Rpi_page)
        self.stackedWidget.addWidget(self.direct_low_freq_page)

    def show_page(self, index):
        self.stackedWidget.setCurrentIndex(index)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = SingleStageFrequencyChoicesWidget()
    w.show()
    sys.exit(app.exec())