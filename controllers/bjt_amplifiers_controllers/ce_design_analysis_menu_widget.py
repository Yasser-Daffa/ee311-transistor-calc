import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.uic import loadUi

from controllers.bjt_amplifiers_controllers.ce_design_widget import CEDesignWidget
from controllers.bjt_amplifiers_controllers.ce_analysis_widget import CEAnalysisWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "design_analysis_menu.ui")


class CEDesignAnalysisMenuWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        # create once
        self.design_widget   = CEDesignWidget()
        self.analysis_widget = CEAnalysisWidget()

        # embed the same instances
        self._embed(self.page0Design,   self.design_widget)
        self._embed(self.page1Analysis, self.analysis_widget)

        # buttons switch the stack
        self.buttonDesign.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(0))
        self.buttonAnalysis.clicked.connect(lambda: self.stackedWidget.setCurrentIndex(1))

        # send to AC wires design -> analysis
        self.design_widget.send_to_analysis.connect(self._populate_analysis)

        self.stackedWidget.setCurrentIndex(0)

    def _populate_analysis(self, result: dict):
        w = self.analysis_widget

        def _set(field, value):
            if hasattr(w, field):
                getattr(w, field).setText(str(round(value, 6)))

        _set("lineEditVcc",  result["Vcc"])
        _set("lineEditBeta", result["beta"])
        _set("lineEditR1",   result["R1"] / 1e3)
        _set("lineEditR2",   result["R2"] / 1e3)
        _set("lineEditRc",   result["Rc"] / 1e3)
        _set("lineEditRe",   result["Re"] / 1e3)

        # change to analysis page
        # and switch from design button to analysis button
        self.buttonDesign.setChecked(False)
        self.buttonAnalysis.setChecked(True)
        self.stackedWidget.setCurrentIndex(1)

    def _embed(self, page, widget):
        layout = page.layout()
        if layout is None:
            layout = QVBoxLayout(page)
            layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CEDesignAnalysisMenuWidget()
    window.setWindowTitle("CE Design / Analysis")
    window.show()
    sys.exit(app.exec())