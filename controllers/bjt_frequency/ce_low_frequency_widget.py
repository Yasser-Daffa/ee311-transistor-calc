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
    parallel,
    cutoff_frequency,
    conservative_low_range,
)

from controllers.bjt_amplifiers_controllers.ce_design_analysis_menu_widget import CEDesignAnalysisMenuWidget
# from PyQt6 import QtStackedWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "ce_low_frequency.ui")


class CELowFrequencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.choice_anim = None

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        # Make the four mode buttons behave like radio buttons:
        # only one can be checked at a time.
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_group.addButton(self.buttonFullAnalysis)
        self.mode_group.addButton(self.buttonGivenC1)
        self.mode_group.addButton(self.buttonGivenC2)
        self.mode_group.addButton(self.buttonGivenCE)

        self.buttonFullAnalysis.setChecked(True)

        self.labelFormulaText.hide()
        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates any available f1, f2, and fE")

    def connect_signals(self):
        inputs = [
            self.lineRs,
            self.lineR1,
            self.lineR2,
            self.lineRB,
            self.lineRC,
            self.lineRE,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
            self.lineCE,
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
        """
        Opens the CE Design calculator externally so the user can calculate
        missing resistor values, then return to the frequency page.
        """

        self.ce_design_window = CEDesignAnalysisMenuWidget()
        self.ce_design_window.buttonAnalysis.clicked.emit()  # trigger analysis page setup
        self.ce_design_window.buttonAnalysis.setChecked(True)  # set analysis page button as checked
        self.ce_design_window.setWindowTitle("CE Design/Analysis Calculator")
        self.ce_design_window.resize(1100, 750)
        self.ce_design_window.show()

    def get_mode_key(self):
        if self.buttonGivenC1.isChecked():
            return "c1_only"

        if self.buttonGivenC2.isChecked():
            return "c2_only"

        if self.buttonGivenCE.isChecked():
            return "ce_only"

        return "full"

    def get_mode_text(self):
        if self.buttonGivenC1.isChecked():
            return "Due to C1 only"

        if self.buttonGivenC2.isChecked():
            return "Due to C2 only"

        if self.buttonGivenCE.isChecked():
            return "Due to CE only"

        return "Full Analysis"

    def get_mode_hint(self):
        mode = self.get_mode_key()

        if mode == "c1_only":
            return "Choice picked: C1 only — needs Rs, RB/R1/R2, β, rπ, RX, and C1"

        if mode == "c2_only":
            return "Choice picked: C2 only — needs RC, RL, and C2"

        if mode == "ce_only":
            return "Choice picked: CE only — needs RE, RX, β, rπ, Rs, RB/R1/R2, and CE"

        return "Choice picked: Full Analysis — calculates any available f1, f2, and fE"

    def on_mode_button_clicked(self):
        self.calculate()
        self.animate_choice_label()

    def set_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

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

    def read_uf(self, line):
        value = self.read_float(line)
        return value * 1e-6 if value is not None else None

    def get_rb(self, r1, r2, rb_direct):
        """
        RB rule:

        Use one method only:
        1. Enter RB direct.
        2. OR enter R1 and R2.

        Do not enter both RB and R1/R2 together.
        """
        has_r1r2 = r1 is not None and r2 is not None
        has_rb = rb_direct is not None

        if has_rb and has_r1r2:
            raise ValueError("Enter either RB directly OR R1 and R2, not both.")

        if has_rb:
            return rb_direct

        if has_r1r2:
            return parallel(r1, r2)

        return None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            mode = self.get_mode_key()

            rs = self.read_kohm(self.lineRs)
            r1 = self.read_kohm(self.lineR1)
            r2 = self.read_kohm(self.lineR2)
            rb_direct = self.read_kohm(self.lineRB)

            rc = self.read_kohm(self.lineRC)
            re = self.read_kohm(self.lineRE)
            rx = self.read_kohm(self.lineRX)
            rl = self.read_kohm(self.lineRL)

            beta = self.read_float(self.lineBeta)
            rpi = self.read_kohm(self.lineRpi)

            c1 = self.read_uf(self.lineC1)
            c2 = self.read_uf(self.lineC2)
            ce = self.read_uf(self.lineCE)

            rb = self.get_rb(r1, r2, rb_direct)

            result = {
                "RB": rb,
                "RXX": None,
                "RSB": None,
                "R11": None,
                "R22": None,
                "REE": None,
                "f1": None,
                "f2": None,
                "fE": None,
                "fL_min": None,
                "fL_max": None,
                "fL_conservative": None,
            }

            # ----------------------------------------------------
            # RB
            # ----------------------------------------------------
            if rb is not None:
                result["RB"] = rb

            # ----------------------------------------------------
            # RXX = rπ + (β + 1)RX
            # ----------------------------------------------------
            if rpi is not None and beta is not None and rx is not None:
                result["RXX"] = rpi + (beta + 1) * rx

            # ----------------------------------------------------
            # RSB = RS || RB
            # ----------------------------------------------------
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # ----------------------------------------------------
            # R11 and f1
            #
            # R11 = RS + (RB || RXX)
            # f1 = 1 / (2π R11 C1)
            # ----------------------------------------------------
            if rs is not None and rb is not None and result["RXX"] is not None:
                result["R11"] = rs + parallel(rb, result["RXX"])

                if c1 is not None:
                    result["f1"] = cutoff_frequency(result["R11"], c1)

            # ----------------------------------------------------
            # R22 and f2
            #
            # R22 = RC + RL
            # f2 = 1 / (2π R22 C2)
            # ----------------------------------------------------
            if rc is not None and rl is not None:
                result["R22"] = rc + rl

                if c2 is not None:
                    result["f2"] = cutoff_frequency(result["R22"], c2)

            # ----------------------------------------------------
            # REE and fE
            #
            # REE = RE || [ RX + (rπ + RSB)/(β + 1) ]
            # fE = 1 / (2π REE CE)
            # ----------------------------------------------------
            if (
                re is not None
                and rx is not None
                and rpi is not None
                and beta is not None
                and result["RSB"] is not None
            ):
                result["REE"] = parallel(
                    re,
                    rx + (rpi + result["RSB"]) / (beta + 1),
                )

                if ce is not None:
                    result["fE"] = cutoff_frequency(result["REE"], ce)

            # ----------------------------------------------------
            # Mode filtering
            # ----------------------------------------------------
            if mode == "c1_only":
                active_freqs = [result["f1"]]

            elif mode == "c2_only":
                active_freqs = [result["f2"]]

            elif mode == "ce_only":
                active_freqs = [result["fE"]]

            else:
                active_freqs = [result["f1"], result["f2"], result["fE"]]

            low = conservative_low_range(active_freqs)
            result.update(low)

            self.show_result(result)

            if result["fL_conservative"] is None:
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
        self.labelRBOut.setText(self.fmt_res(r.get("RB")))
        self.labelRXX.setText(self.fmt_res(r.get("RXX")))
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))

        self.labelR11.setText(self.fmt_res(r.get("R11")))
        self.labelR22.setText(self.fmt_res(r.get("R22")))
        self.labelREE.setText(self.fmt_res(r.get("REE")))

        self.labelF1.setText(self.fmt_freq(r.get("f1")))
        self.labelF2.setText(self.fmt_freq(r.get("f2")))
        self.labelFE.setText(self.fmt_freq(r.get("fE")))

        self.labelFLConservative.setText(
            f"fL conservative: {self.fmt_freq(r.get('fL_conservative'))}"
        )

        if r.get("fL_min") is None or r.get("fL_max") is None:
            self.labelFLRange.setText("Range: —")
        else:
            self.labelFLRange.setText(
                f"Range: {self.fmt_freq(r.get('fL_min'))} ≤ fL ≤ {self.fmt_freq(r.get('fL_max'))}"
            )

    def clear_outputs(self):
        labels = [
            self.labelRBOut,
            self.labelRXX,
            self.labelRSB,
            self.labelR11,
            self.labelR22,
            self.labelREE,
            self.labelF1,
            self.labelF2,
            self.labelFE,
        ]

        for label in labels:
            label.setText("—")

        self.labelFLConservative.setText("fL conservative: —")
        self.labelFLRange.setText("Range: —")

    def clear_inputs(self):
        lines = [
            self.lineRs,
            self.lineR1,
            self.lineR2,
            self.lineRB,
            self.lineRC,
            self.lineRE,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
            self.lineCE,
        ]

        for line in lines:
            line.clear()

        self.buttonFullAnalysis.setChecked(True)

        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates any available f1, f2, and fE")
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
    w = CELowFrequencyWidget()
    w.show()
    sys.exit(app.exec())