import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH  = os.path.join(BASE_DIR, "..", "..", "ui", "bjt_transistors", "topologies_menu.ui")

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QButtonGroup
from PyQt6.uic import loadUi

from controllers.bjt_transistors_controllers.bjt_emitter_fixed_bias_widget         import BJTEmitterBiasWidget
from controllers.bjt_transistors_controllers.bjt_voltage_divider_bias_widget       import BJTVoltageDividerBiasWidget
from controllers.bjt_transistors_controllers.bjt_collector_feedback_bias_widget    import BJTCollectorFeedbackBiasWidget


class BJTTopologiesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        # embed sub-widgets into each stacked page 
        self._embed(self.page0FixedEmitterBias,    BJTEmitterBiasWidget())
        self._embed(self.page1VoltageDividerBias,  BJTVoltageDividerBiasWidget())
        self._embed(self.page2CollectorFeedbackBias, BJTCollectorFeedbackBiasWidget())

        # wire nav buttons to stacked widget
        self.buttonProfileFixedEmitterBias.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.buttonProfileVoltageDividerBias.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))
        self.buttonProfileCollectorFeedbackBias.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(2))

        # start on page 0
        self.stackedWidget.setCurrentIndex(0)

    def _embed(self, page, widget):
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BJTTopologiesWidget()
    window.setWindowTitle("BJT Transistor Calculator")
    window.show()
    sys.exit(app.exec())