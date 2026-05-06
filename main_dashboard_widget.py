# controllers/bjt_amplifiers_controllers/main_dashboard_widget.py

import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QVBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

from controllers.bjt_transistors_controllers.bjt_topologies_widget import BJTTopologiesWidget
from controllers.bjt_amplifiers_controllers.ce_design_analysis_menu_widget import CEDesignAnalysisMenuWidget
from controllers.bjt_amplifiers_controllers.cc_design_analysis_menu_widget import CCDesignAnalysisMenuWidget
from controllers.bjt_multistage_controllers.multistage_choices_widget import MultistageChoicesWidget

from controllers.bjt_frequency_controllers.singlestage_frequency_choices_widget import SingleStageFrequencyChoicesWidget
from controllers.bjt_frequency_controllers.multistage_frequency_choices_widget import MultistageFrequencyChoicesWidget

from controllers.bjt_frequency_controllers.cutoff_frequency_choices_widget import CutoffFrequencyChoicesWidget
from controllers.bjt_frequency_controllers.capacitor_finder_choices_widget import CapacitorChoicesWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "ui", "main_dashboard.ui")


class MainDashboardWidget(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self._embed(self.page0BjtTransistor, BJTTopologiesWidget())
        self._embed(self.page1CommonEmitter, CEDesignAnalysisMenuWidget())
        self._embed(self.page2CommonCollector, CCDesignAnalysisMenuWidget())
        self._embed(self.page3MultiStage, MultistageChoicesWidget())
        self._embed(self.page4SingleStageFrequency, SingleStageFrequencyChoicesWidget())
        self._embed(self.page5MultiStageFrequency, MultistageFrequencyChoicesWidget())
        self._embed(self.page6CutOffFrequency, CutoffFrequencyChoicesWidget())
        self._embed(self.page7CapacitorsCalc, CapacitorChoicesWidget())


        self.add_placeholder(self.page8Mosfets, "MOSFETs Under Development!")

        
        self.buttonBjtTransistor.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.buttonCommonEmitter.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))
        self.buttonCommonCollector.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(2))
        self.buttonMultiStage.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(3))
        self.buttonSingleStageFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(4))
        self.buttonMultiStageFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(5))
        self.buttonCutOffFrequency.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(6))
        self.buttonCapacitorsCalc.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(7))
        self.buttonMosfets.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(8))

        self.buttonExit.clicked.connect(self.close)

        # start on page 0
        self.stackedWidget.setCurrentIndex(0)

    def _embed(self, page, widget):
        layout = page.layout()

        if layout is None:
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(widget)

    def add_placeholder(self, page, text="🚧 Under Development"):
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color:#888; font: 600 22pt 'Segoe UI';")

        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)

        layout.addWidget(label)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainDashboardWidget()
    window.setWindowTitle("Main Dashboard")
    window.show()
    sys.exit(app.exec())