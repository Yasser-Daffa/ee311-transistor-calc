import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.uic import loadUi

from core.core_helpers import fmt, signed_validator, positive_validator
from core.bjt_amplifiers import analyze_cc_general

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "amp_analysis_inovative.ui")


class CCAnalysisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self._setup_validators()
        self._setup_connections()
        self._setup_cc_ui()
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
        

    def _setup_validators(self):
        signed_fields = [
            "lineEditVcc",
        ]

        positive_fields = [
            "lineEditBeta",
            "lineEditR1",
            "lineEditR2",
            "lineEditRc",
            "lineEditRe",
            "lineEditRs",
            "lineEditRl",
            "lineEditChoice",
        ]

        for name in signed_fields:
            if hasattr(self, name):
                getattr(self, name).setValidator(signed_validator(self))

        for name in positive_fields:
            if hasattr(self, name):
                getattr(self, name).setValidator(positive_validator(self))

    def _setup_connections(self):
        for name in [
            "lineEditVcc",
            "lineEditBeta",
            "lineEditR1",
            "lineEditRe",
            "lineEditRs",
            "lineEditRl",
        ]:
            if hasattr(self, name):
                getattr(self, name).textChanged.connect(self.calculate)

        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

    def _setup_cc_ui(self):
        # R1 input is reused as RB
        if hasattr(self, "labelR1"):
            self.labelR1.setText("<b>R<sub>B</sub></b>")

        if hasattr(self, "labelR1Info"):
            self.labelR1Info.setText("Base Resistor                ")

        # hide unused input rows
        for name in [
            "labelR2", "labelR2Info", "lineEditR2", "labelR2Unit",
            "labelRc", "labelRcInfo", "lineEditRc", "labelRcUnit",
        ]:
            if hasattr(self, name):
                getattr(self, name).setVisible(False)

        # hide whole choice section
        for name in [
            "labelGivenTitle",
            "pushButtonGivenRx", "pushButtonGivenAv0", "pushButtonGivenRi", "pushButtonGivenAvt",
            "labelChoiceSymbol", "labelChoiceInfo", "lineEditChoice", "labelChoiceUnit",
        ]:
            if hasattr(self, name):
                getattr(self, name).setVisible(False)

        # CC output label tweaks
        self._set_label("labelOutputVbbTitle", "—")


    def _read_inputs(self):
        vcc = float(self.lineEditVcc.text())
        beta = float(self.lineEditBeta.text())

        # In CC, use R1 input field as RB
        rb = float(self.lineEditR1.text()) * 1e3

        re = float(self.lineEditRe.text()) * 1e3
        rs = float(self.lineEditRs.text() or 0) * 1e3
        rl = float(self.lineEditRl.text() or 0) * 1e3

        if rl == 0:
            rl = None

        return vcc, beta, rb, re, rs, rl

    def calculate(self):
        try:
            vcc, beta, rb, re, rs, rl = self._read_inputs()
        except ValueError:
            self._clear_outputs_only()
            self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
            return

        try:
            result = analyze_cc_general(
                Vcc=vcc,
                beta=beta,
                Rb=rb,
                Re=re,
                Rs=rs,
                RL=rl,
            )
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        self._push_outputs(result)
        self._set_mode("CC ANALYZED", "#d4edda", "#155724")

    def _push_outputs(self, r):
        # DC outputs
        self._set_label("labelOutputIb", fmt(r["Ib"], "A", scale="µA"))
        self._set_label("labelOutputRb", fmt(r["Rb"], "Ω"))
        self._set_label("labelOutputRpi", fmt(r["rpi"], "Ω"))
        self._set_label("labelOutputVbb", "—")
        self._set_label("labelOutputVc", fmt(r["Vc"], "V"))
        self._set_label("labelOutputVb", fmt(r["Vb"], "V"))

        # AC outputs
        self._set_label("labelOutputRx", "—")
        self._set_label("labelOutputRxx", fmt(r["Rxx"], "Ω"))
        self._set_label("labelOutputRi", fmt(r["Ri"], "Ω"))
        self._set_label("labelOutputRo", fmt(r["Ro"], "Ω"))
        self._set_label("labelOutputKo", f"{r['Ko']:.4f}")
        self._set_label("labelOutputAvo", f"{r['Av0']:.4f}")
        self._set_label("labelOutputAvt", f"{r['AvT']:.4f}")
        self._set_label("labelOutputAvot", f"{r['Av_loaded']:.4f}")

        # Limits
        self._set_label("labelAvoMin", f"{r['av0_min']:.4f}")
        self._set_label("labelAvoMax", f"{r['av0_max']:.4f}")
        self._set_label("labelRiMin", fmt(r["ri_min"], "Ω"))
        self._set_label("labelRiMax", fmt(r["ri_max"], "Ω"))
        self._set_label("labelRxMin", "—")
        self._set_label("labelRxMax", "—")

    def _set_label(self, name, text):
        if hasattr(self, name):
            getattr(self, name).setText(text)

    def _clear_outputs_only(self):
        for name in [
            "labelOutputIb",
            "labelOutputRb",
            "labelOutputRpi",
            "labelOutputVbb",
            "labelOutputVc",
            "labelOutputVb",
            "labelOutputRx",
            "labelOutputRi",
            "labelOutputAvo",
            "labelOutputRxx",
            "labelOutputRo",
            "labelOutputKo",
            "labelOutputAvt",
            "labelOutputAvot",
            "labelAvoMin",
            "labelAvoMax",
            "labelRiMin",
            "labelRiMax",
            "labelRxMin",
            "labelRxMax",
        ]:
            self._set_label(name, "-")

    def clear_fields(self):
        for w in self.findChildren(QLineEdit):
            w.clear()

        self._setup_cc_ui()
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    def _set_mode(self, text, bg, fg):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)
            self.labelMode.setStyleSheet(
                f"border-radius:6px; font: 700 11pt 'Rockwell'; "
                f"padding: 4px 14px; background-color:{bg}; color:{fg};"
            )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CCAnalysisWidget()
    window.setWindowTitle("CC Amplifier Analysis")
    window.show()
    sys.exit(app.exec())