import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.QtGui import QDoubleValidator, QPixmap
from PyQt6.uic import loadUi
from PyQt6.QtCore import Qt

from core.core_helpers import fmt
from core.bjt_amplifiers import design_cc_from_specs

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "amp_design.ui")


class CCDesignWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self.image_path = os.path.join(BASE_DIR, "..", "..", "assets", "images", "cc_amp.png")
        self._set_circuit_image()

        # validators
        vcc_validator = QDoubleValidator(0.0, 1000.0, 3, self)
        icmax_validator = QDoubleValidator(0.0, 1000.0, 3, self)
        beta_validator = QDoubleValidator(1.0, 10000.0, 3, self)

        vcc_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        icmax_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        beta_validator.setNotation(QDoubleValidator.Notation.StandardNotation)

        self.lineEditVcc.setValidator(vcc_validator)
        self.lineEditIcmax.setValidator(icmax_validator)
        self.lineEditBeta.setValidator(beta_validator)

        self.labelCircuitTitle.setText("Common Collector (CC)")

        # live calculation
        for field in [self.lineEditVcc, self.lineEditIcmax, self.lineEditBeta]:
            field.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_fields)

        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
        self._clear_outputs_only()

    def _set_circuit_image(self):
        if not hasattr(self, "labelCircuitImage"):
            return

        pixmap = QPixmap(self.image_path)
        if pixmap.isNull():
            return

        self.labelCircuitImage.setPixmap(
            pixmap.scaled(
                self.labelCircuitImage.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._set_circuit_image()

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
            result = design_cc_from_specs(
                Vcc=vcc,
                Icmax_mA=icmax,
                beta=beta,
            )
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        self.labelOutputRc.setText(fmt(result["Rc"], "Ω"))
        self.labelOutputRe.setText(fmt(result["Re"], "Ω"))
        self.labelOutputRb.setText(fmt(result["Rb"], "Ω"))
        self.labelOutputR1.setText(fmt(result["R1"], "Ω"))
        self.labelOutputR2.setText(fmt(result["R2"], "Ω"))
        self.labelOutputVbb.setText(fmt(result["Vbb"], "V"))
        self.labelOutputRpi.setText(fmt(result["rpi"], "Ω"))

        self.labelAvoMin.setText(f"{result['av0_min']:.3f}")
        self.labelAvoMax.setText(f"{result['av0_max']:.3f}")

        self.labelRiMin.setText(fmt(result["ri_min"], "Ω"))
        self.labelRiMax.setText(fmt(result["ri_max"], "Ω"))
        self.labelRxMin.setText(fmt(result["rx_min"], "Ω"))
        self.labelRxMax.setText(fmt(result["rx_max"], "Ω"))

        self._set_mode("DESIGNED", "#d4edda", "#155724")

    def _set_mode(self, text, bg, fg):
        self.labelMode.setText(text)
        self.labelMode.setStyleSheet(
            f"border-radius:6px; font: 700 11pt 'Rockwell'; "
            f"padding: 4px 14px; background-color:{bg}; color:{fg};"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CCDesignWidget()
    window.setWindowTitle("CC Amplifier Design")
    window.show()
    sys.exit(app.exec())