import os
import sys

from PyQt6.QtWidgets import QWidget, QButtonGroup, QLabel, QVBoxLayout
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from controllers.bjt_frequency_controllers.cpi_cmu_widget import CpiCmuWidget
from controllers.bjt_frequency_controllers.capacitor_finder_widget import CapacitorFinderWidget



BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "capacitor_choices.ui")


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


class CapacitorChoicesWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.setup_ui()
        self.connect_signals()

    def setup_ui(self):
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        for button in [self.buttonCpiCmu, self.buttonLowFreqCapFinder]:
            button.setCheckable(True)
            self.mode_group.addButton(button)

        self.buttonCpiCmu.setChecked(True)

        self.load_pages()
        self.stackedWidget.setCurrentIndex(0)

    def connect_signals(self):
        self.buttonCpiCmu.clicked.connect(lambda: self.show_page(0))
        self.buttonLowFreqCapFinder.clicked.connect(lambda: self.show_page(1))

    def load_pages(self):
        """
        Remove placeholder pages from Qt Designer and insert real widgets. (after I add freq page)
        """

        while self.stackedWidget.count() > 0:
            old_page = self.stackedWidget.widget(0)
            self.stackedWidget.removeWidget(old_page)
            old_page.deleteLater()

        self.cpi_cmu_page = CpiCmuWidget()
        self.low_freq_capacitor_finder_page = CapacitorFinderWidget()

        self.stackedWidget.addWidget(self.cpi_cmu_page)
        self.stackedWidget.addWidget(self.low_freq_capacitor_finder_page)

    def show_page(self, index):
        self.stackedWidget.setCurrentIndex(index)


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = CapacitorChoicesWidget()
    w.show()
    sys.exit(app.exec())