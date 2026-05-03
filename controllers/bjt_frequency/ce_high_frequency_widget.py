import os
import sys

from PyQt6.QtCore import QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import (
    QWidget,
    QButtonGroup,
    QGraphicsOpacityEffect,
)
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.bjt_frequency import (
    ce_high_resistances,
    CEHighResistanceInputs,
    high_frequency,
    HighFreqInputs,
    conservative_high_range,
    cutoff_frequency,
)

from controllers.bjt_amplifiers_controllers.ce_design_analysis_menu_widget import CEDesignAnalysisMenuWidget

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "ce_high_frequency.ui")


class CEHighFrequencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.choice_anim = None
        self.mode_group = None

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_group.addButton(self.buttonFullAnalysis)
        self.mode_group.addButton(self.buttonGivenCpi)
        self.mode_group.addButton(self.buttonGivenCmu)

        self.buttonFullAnalysis.setChecked(True)

        self.labelFormulaText.hide()
        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates fπ and fµ")

    def connect_signals(self):
        inputs = [
            self.lineRs,
            self.lineRB,
            self.lineRpi,
            self.lineRX,
            self.lineRC,
            self.lineRL,
            self.lineBeta,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.mode_group.buttonClicked.connect(self.on_mode_button_clicked)
        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)
        self.buttonOpen.clicked.connect(self.open_ce_design_window)

    # ------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------

    def open_ce_design_window(self):
        self.ce_design_window = CEDesignAnalysisMenuWidget()
        self.ce_design_window.buttonAnalysis.clicked.emit()
        self.ce_design_window.buttonAnalysis.setChecked(True)
        self.ce_design_window.setWindowTitle("CE Design/Analysis Calculator")
        self.ce_design_window.resize(1100, 750)
        self.ce_design_window.show()

    def get_mode_key(self):
        if self.buttonGivenCpi.isChecked():
            return "cpi_only"
        if self.buttonGivenCmu.isChecked():
            return "cmu_only"
        return "full"

    def get_mode_text(self):
        mode = self.get_mode_key()
        if mode == "cpi_only":
            return "Due to Cπ only"
        if mode == "cmu_only":
            return "Due to Cµ only"
        return "Full Analysis"

    def get_mode_hint(self):
        mode = self.get_mode_key()
        if mode == "cpi_only":
            return "Choice picked: Cπ only — needs RS, RB, rπ, RX, RC, RL, β, and Cπ"
        if mode == "cmu_only":
            return "Choice picked: Cµ only — needs RS, RB, rπ, RX, RC, RL, β, and Cµ"
        return "Choice picked: Full Analysis — calculates fπ and fµ"

    def on_mode_button_clicked(self):
        self.calculate()
        self.animate_choice_label()

    def set_status(self, text):
        if hasattr(self, "labelChoicePicked"):
            self.labelChoicePicked.setText(text)

    def animate_choice_label(self):
        if not hasattr(self, "labelChoicePicked"):
            return

        effect = QGraphicsOpacityEffect(self.labelChoicePicked)
        self.labelChoicePicked.setGraphicsEffect(effect)

        self.choice_anim = QPropertyAnimation(effect, b"opacity", self)
        self.choice_anim.setDuration(220)
        self.choice_anim.setStartValue(0.25)
        self.choice_anim.setEndValue(1.0)
        self.choice_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.choice_anim.start()

    # ------------------------------------------------------------
    # Reading helpers
    # ------------------------------------------------------------

    def read_float(self, line):
        text = line.text().strip()
        if text == "":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def read_kohm(self, line):
        value = self.read_float(line)
        return value * 1000 if value is not None else None

    def read_pf(self, line):
        """Read value in pF, return in Farads."""
        value = self.read_float(line)
        return value * 1e-12 if value is not None else None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            mode = self.get_mode_key()

            rs = self.read_kohm(self.lineRs)
            rb = self.read_kohm(self.lineRB)
            rpi = self.read_kohm(self.lineRpi)
            rx = self.read_kohm(self.lineRX)
            rc = self.read_kohm(self.lineRC)
            rl = self.read_kohm(self.lineRL)
            beta = self.read_float(self.lineBeta)

            cpi = self.read_pf(self.lineCpi)
            cmu = self.read_pf(self.lineCmu)

            result = {
                "RSB": None,
                "RCL": None,
                "RXX": None,
                "Rpi_eq": None,
                "Rmu_eq": None,
                "fpi": None,
                "fmu": None,
                "fH_min": None,
                "fH_max": None,
                "fH_conservative": None,
            }

            # -------------------------------------------------------
            # Equivalent resistances — need all circuit resistors + β
            # -------------------------------------------------------
            resist_ready = all(
                v is not None for v in [rs, rb, rpi, rx, rc, rl, beta]
            )

            if resist_ready:
                res = ce_high_resistances(
                    CEHighResistanceInputs(
                        rs_ohm=rs,
                        rb_ohm=rb,
                        rpi_ohm=rpi,
                        rx_ohm=rx,
                        rc_ohm=rc,
                        rl_ohm=rl,
                        beta=beta,
                    )
                )
                result["RSB"] = res["RSB"]
                result["RCL"] = res["RCL"]
                result["RXX"] = res["RXX"]
                result["Rpi_eq"] = res["Rpi_eq"]
                result["Rmu_eq"] = res["Rmu_eq"]

            # -------------------------------------------------------
            # fπ — needs Rπ_eq and Cπ
            # -------------------------------------------------------
            if result["Rpi_eq"] is not None and cpi is not None:
                result["fpi"] = cutoff_frequency(result["Rpi_eq"], cpi)

            # -------------------------------------------------------
            # fµ — needs Rµ_eq and Cµ
            # -------------------------------------------------------
            if result["Rmu_eq"] is not None and cmu is not None:
                result["fmu"] = cutoff_frequency(result["Rmu_eq"], cmu)

            # -------------------------------------------------------
            # Mode filtering
            # -------------------------------------------------------
            if mode == "cpi_only":
                active_freqs = [result["fpi"]]
            elif mode == "cmu_only":
                active_freqs = [result["fmu"]]
            else:
                active_freqs = [result["fpi"], result["fmu"]]

            high = conservative_high_range(active_freqs)
            result.update(high)

            self.show_result(result)

            if result["fH_conservative"] is None:
                self.set_status(self.get_mode_hint())
            else:
                self.set_status(f"Choice picked: {self.get_mode_text()}")

        except Exception as e:
            self.clear_outputs()
            self.set_status(f"Error: {e}")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))
        self.labelRCL.setText(self.fmt_res(r.get("RCL")))
        self.labelRXX.setText(self.fmt_res(r.get("RXX")))
        self.labelRpiEq.setText(self.fmt_res(r.get("Rpi_eq")))
        self.labelRmuEq.setText(self.fmt_res(r.get("Rmu_eq")))

        self.labelFpi.setText(self.fmt_freq(r.get("fpi")))
        self.labelFmu.setText(self.fmt_freq(r.get("fmu")))

        self.labelFHConservative.setText(
            f"fH conservative: {self.fmt_freq(r.get('fH_conservative'))}"
        )

        if r.get("fH_min") is None or r.get("fH_max") is None:
            self.labelFHRange.setText("Range: —")
        else:
            self.labelFHRange.setText(
                f"Range: {self.fmt_freq(r.get('fH_min'))} ≤ fH ≤ {self.fmt_freq(r.get('fH_max'))}"
            )

    def clear_outputs(self):
        for label in [
            self.labelRSB,
            self.labelRCL,
            self.labelRXX,
            self.labelRpiEq,
            self.labelRmuEq,
            self.labelFpi,
            self.labelFmu,
        ]:
            label.setText("—")

        self.labelFHConservative.setText("fH conservative: —")
        self.labelFHRange.setText("Range: —")

    def clear_inputs(self):
        for line in [
            self.lineRs,
            self.lineRB,
            self.lineRpi,
            self.lineRX,
            self.lineRC,
            self.lineRL,
            self.lineBeta,
            self.lineCpi,
            self.lineCmu,
        ]:
            line.clear()

        self.buttonFullAnalysis.setChecked(True)
        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates fπ and fµ")
        self.animate_choice_label()

    def toggle_formulas(self):
        visible = self.labelFormulaText.isVisible()
        self.labelFormulaText.setVisible(not visible)
        if visible:
            self.pushButtonShowFormulas.setText(" Show Formulas")
        else:
            self.pushButtonShowFormulas.setText(" Hide Formulas")

    # ------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------

    def fmt_res(self, value):
        if value is None:
            return "—"
        if abs(value) >= 1000:
            return f"{value / 1000:.3g} kΩ"
        return f"{value:.3g} Ω"

    def fmt_freq(self, value):
        if value is None:
            return "—"
        if abs(value) >= 1e6:
            return f"{value / 1e6:.3g} MHz"
        if abs(value) >= 1e3:
            return f"{value / 1e3:.3g} kHz"
        return f"{value:.3g} Hz"


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = CEHighFrequencyWidget()
    w.show()
    sys.exit(app.exec())
