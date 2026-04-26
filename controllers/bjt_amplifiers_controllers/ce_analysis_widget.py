import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.uic import loadUi

from core.core_helpers import fmt, positive_validator, signed_validator
from core.bjt_amplifiers import analyze_ce_general

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "ce_cc_analysis_design", "amp_analysis_inovative.ui")


class CEAnalysisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self.mode = "given_rx"

        self._setup_validators()
        self._setup_connections()
        self._set_choice_ui("<b>R<sub>X</sub></b>", "Emitter bypass resistor", "kΩ")
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
            "lineEditR2",
            "lineEditRc",
            "lineEditRe",
            "lineEditRs",
            "lineEditRl",
            "lineEditChoice",
        ]:
            if hasattr(self, name):
                getattr(self, name).textChanged.connect(self.calculate)

        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

        # Change these button names if your Designer names differ
        # These buttons set which parameter is the "given" one that the user wants to specify directly

        # the lambda is needed to capture the current value of data in the loop, otherwise it will always use the last value
        # the <b> tags in the symbols are for bold formatting in the UI labels, the <sub> tags are for subscripts.

        button_map = {
            "pushButtonGivenRx":   ("given_rx",  "<b>R<sub>X</sub></b>",   "Emitter bypass resistor", "kΩ"),
            "pushButtonGivenAv0":  ("given_av0", "<b>Av0</b>",  "Open-circuit voltage gain", ""),
            "pushButtonGivenRi":   ("given_ri",  "<b>Ri</b>",   "Input resistance", "kΩ"),
            "pushButtonGivenAvt":  ("given_avt", "<b>Avt</b>",  "Total voltage gain", ""),
        }

        for btn_name, data in button_map.items():
            if hasattr(self, btn_name):
                getattr(self, btn_name).clicked.connect(
                    lambda checked=False, d=data: self._select_given_mode(*d)
                )

    def _select_given_mode(self, mode, symbol, desc, unit):
        self.mode = mode
        self._set_choice_ui(symbol, desc, unit)
        self.calculate()

    def _set_choice_ui(self, symbol, desc, unit):
        if hasattr(self, "labelChoiceSymbol"):
            self.labelChoiceSymbol.setText(symbol)

        if hasattr(self, "labelChoiceInfo"):
            self.labelChoiceInfo.setText(desc)

        if hasattr(self, "labelChoiceUnit"):
            self.labelChoiceUnit.setText(unit)

        # for your typo version, if it still exists
        if hasattr(self, "labelChocieUnit"):
            self.labelChocieUnit.setText(unit)

    def _read_inputs(self):
        vcc = float(self.lineEditVcc.text())
        beta = float(self.lineEditBeta.text())

        # GUI inputs are in kΩ, core expects Ω
        r1 = float(self.lineEditR1.text()) * 1e3
        r2 = float(self.lineEditR2.text()) * 1e3
        rc = float(self.lineEditRc.text()) * 1e3
        re = float(self.lineEditRe.text()) * 1e3
        rs = float(self.lineEditRs.text() or 0) * 1e3
        rl = float(self.lineEditRl.text() or 0) * 1e3

        if rl == 0:
            rl = None

        choice_text = self.lineEditChoice.text().strip()

        if choice_text == "":
            choice = 0.0
        else:
            choice = float(choice_text)

        # Rx and Ri are entered in kΩ
        if self.mode in ["given_rx", "given_ri"]:
            choice *= 1e3

        return vcc, beta, r1, r2, rc, re, rs, rl, choice

    def calculate(self):
        try:
            vcc, beta, r1, r2, rc, re, rs, rl, choice = self._read_inputs()
        except ValueError:
            self._clear_outputs_only()
            self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
            return

        try:
            result = analyze_ce_general(
                Vcc=vcc,
                beta=beta,
                R1=r1,
                R2=r2,
                Rc=rc,
                Re=re,
                Rs=rs,
                RL=rl,
                mode=self.mode,
                choice_value=choice,
            )
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        self._push_outputs(result)

        if result["possible"]:
            self._set_mode("CE ANALYZED", "#d4edda", "#155724")
        else:
            self._set_mode(result["warning"], "#fff3cd", "#856404")

    def _push_outputs(self, r):

        # Helper to format gain values, which can be None if not applicable in certain modes
        # Button Send to AC wont work unless these exist, we show "—" instead of leaving blank or showing "None"
        def _fmt_gain(value):
            return f"{value:.4f}" if value is not None else "—"

        def _fmt_val(value, unit):
            return fmt(value, unit) if value is not None else "—"
        

        # DC outputs
        self._set_label("labelOutputIb", fmt(r["Ib"], "A", scale="µA"))
        self._set_label("labelOutputRb", fmt(r["Rb"], "Ω"))
        self._set_label("labelOutputRpi", fmt(r["rpi"], "Ω"))
        self._set_label("labelOutputVbb", fmt(r["Vbb"], "V"))
        self._set_label("labelOutputVc", fmt(r["Vc"], "V"))
        self._set_label("labelOutputVb", fmt(r["Vb"], "V"))

        # AC outputs
        self._set_label("labelOutputRx", _fmt_val(r["Rx"], "Ω"))
        self._set_label("labelOutputRxx", _fmt_val(r["Rxx"], "Ω"))
        self._set_label("labelOutputRi", _fmt_val(r["Ri"], "Ω"))
        self._set_label("labelOutputRo", _fmt_val(r["Ro"], "Ω"))
        self._set_label("labelOutputKo", _fmt_gain(r['Ko']))
        self._set_label("labelOutputAvo", _fmt_gain(r['Av0']))
        self._set_label("labelOutputAvt", _fmt_gain(r['AvT']))

        # Optional extra label from your UI
        self._set_label("labelOutputAvot", _fmt_gain(r['AvT_signed']))

        # Limits
        self._set_label("labelAvoMin", f"{r['av0_min']:.4f}")
        self._set_label("labelAvoMax", f"{r['av0_max']:.4f}")
        self._set_label("labelRiMin", fmt(r["ri_min"], "Ω"))
        self._set_label("labelRiMax", fmt(r["ri_max"], "Ω"))
        self._set_label("labelRxMin", fmt(r["rx_min"], "Ω"))
        self._set_label("labelRxMax", fmt(r["rx_max"], "Ω"))
        self._set_label("labelVsMax", _fmt_val(r.get("Vs_max"), "V"))
        self._set_label("labelVsMin", _fmt_val(r.get("Vs_min"), "V"))


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
    window = CEAnalysisWidget()
    window.setWindowTitle("CE Amplifier Analysis")
    window.show()
    sys.exit(app.exec())