import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# controllers/bjt_amplifiers_controllers/ce_design_widget.py

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.QtCore import pyqtSignal

from PyQt6.uic import loadUi

from core.core_helpers import fmt, signed_validator, positive_validator
from core.bjt_amplifiers import design_ce_from_specs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "amp_design.ui")


class CEDesignWidget(QWidget):

    send_to_analysis = pyqtSignal(dict)  # emits the result dict

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        # validators
        self.lineEditVcc.setValidator(signed_validator(self))
        self.lineEditIcmax.setValidator(positive_validator(self))
        self.lineEditBeta.setValidator(positive_validator(self))

        # live calculation
        for field in [self.lineEditVcc, self.lineEditIcmax, self.lineEditBeta]:
            field.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_fields)

        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
        self._clear_outputs_only()


        # After clicking send to ac analysis, 
        # the design widget will emit the last calculated result (if any) to the analysis widget
        self.buttonSendToAc.clicked.connect(self._emit_send)
        self._last_result = None  # initialize as None, calculate() will fill it

    def _emit_send(self):
        if hasattr(self, "_last_result") and self._last_result:
            self.send_to_analysis.emit(self._last_result)

    def _clear_outputs_only(self):
        for name in [
            "labelOutputRc",
            "labelOutputRe",
            "labelOutputRb",
            "labelOutputR1",
            "labelOutputR2",
            "labelOutputVbb",
            "labelOutputRpi",
            "labelAvoMin",
            "labelAvoMax",
            "labelRiMin",
            "labelRiMax",
            "labelRxMin",
            "labelRxMax",
        ]:
            if hasattr(self, name):
                getattr(self, name).setText("-")

    def clear_fields(self):
        for w in self.findChildren(QLineEdit):
            w.clear()

        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    def calculate(self):
        try:
            vcc = float(self.lineEditVcc.text())
            icmax = float(self.lineEditIcmax.text())   # mA
            beta = float(self.lineEditBeta.text())
        except ValueError:
            self._clear_outputs_only()
            self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
            return

        try:
            result = design_ce_from_specs(
                Vcc=vcc,
                Icmax_mA=icmax,
                beta=beta,
            )
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        # main outputs
        self.labelOutputRc.setText(fmt(result["Rc"], "Ω"))
        self.labelOutputRe.setText(fmt(result["Re"], "Ω"))
        self.labelOutputRb.setText(fmt(result["Rb"], "Ω"))
        self.labelOutputR1.setText(fmt(result["R1"], "Ω"))
        self.labelOutputR2.setText(fmt(result["R2"], "Ω"))
        self.labelOutputVbb.setText(fmt(result["Vbb"], "V"))
        self.labelOutputRpi.setText(fmt(result["rpi"], "Ω"))

        # limits
        self.labelAvoMin.setText(f"{result['av0_min']:.3f}")
        self.labelAvoMax.setText(f"{result['av0_max']:.0f}")

        # if ri_min is not returned by solver, show 0 Ω
        ri_min = result.get("ri_min", 0.0)
        self.labelRiMin.setText(fmt(ri_min, "Ω"))

        self.labelRiMax.setText(fmt(result["ri_max"], "Ω"))
        self.labelRxMin.setText(fmt(result["rx_min"], "Ω"))
        self.labelRxMax.setText(fmt(result["rx_max"], "Ω"))

        result["Vcc"]  = vcc 
        result["beta"] = beta # include input specs in the result dict for sending to analysis
        
        self._last_result = result  # store the last successful result for sending to analysis

        self._set_mode("DESIGNED", "#d4edda", "#155724")

    def _set_mode(self, text, bg, fg):
        self.labelMode.setText(text)
        self.labelMode.setStyleSheet(
            f"border-radius:6px; font: 700 11pt 'Rockwell'; "
            f"padding: 4px 14px; background-color:{bg}; color:{fg};"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CEDesignWidget()
    window.setWindowTitle("CE Amplifier Design")
    window.show()
    sys.exit(app.exec())