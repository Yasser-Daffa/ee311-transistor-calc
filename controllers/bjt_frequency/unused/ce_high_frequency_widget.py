import os
import sys

from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.bjt_frequency import (
    parallel,
    cutoff_frequency,
    conservative_high_range,
)

from controllers.bjt_amplifiers_controllers.ce_design_analysis_menu_widget import CEDesignAnalysisMenuWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "ce_high_frequency.ui")


class CEHighFrequencyWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        self.labelFormulaText.hide()
        self.clear_outputs()
        self.set_required_highlights()
        self.set_calc_status("— awaiting calculation —")

    def connect_signals(self):
        inputs = [
            self.lineRs,
            self.lineR1,
            self.lineR2,
            self.lineRB,
            self.lineRC,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.lineR1.textChanged.connect(self.update_rb_input_lock)
        self.lineR2.textChanged.connect(self.update_rb_input_lock)
        self.lineRB.textChanged.connect(self.update_rb_input_lock)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

        if hasattr(self, "buttonOpen"):
            self.buttonOpen.clicked.connect(self.open_ce_design_window)

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def set_calc_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def refresh_line_styles(self, *widgets):
        """
        Forces Qt to re-apply stylesheet rules after changing dynamic properties.
        """
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def set_required_highlights(self):
        """
        CE high frequency uses all these inputs, but the app still calculates
        partial results whenever enough values are entered.
        """

        all_lines = [
            self.lineRs,
            self.lineR1,
            self.lineR2,
            self.lineRB,
            self.lineRC,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in all_lines:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

    def update_rb_input_lock(self):
        """
        Prevent invalid RB input combinations.

        If user types in R1 or R2:
            disable RB direct.

        If user types in RB direct:
            disable R1 and R2.

        If all are empty:
            enable all three.
        """

        has_r1_or_r2 = bool(self.lineR1.text().strip()) or bool(self.lineR2.text().strip())
        has_rb = bool(self.lineRB.text().strip())

        if has_r1_or_r2 and not has_rb:
            self.lineRB.setEnabled(False)
            self.lineRB.setToolTip(
                "Disabled because R1 or R2 is entered. Clear R1/R2 to use RB direct."
            )

            self.lineR1.setEnabled(True)
            self.lineR2.setEnabled(True)
            self.lineR1.setToolTip("")
            self.lineR2.setToolTip("")
            return

        if has_rb and not has_r1_or_r2:
            self.lineR1.setEnabled(False)
            self.lineR2.setEnabled(False)
            self.lineR1.setToolTip(
                "Disabled because RB direct is entered. Clear RB to use R1/R2."
            )
            self.lineR2.setToolTip(
                "Disabled because RB direct is entered. Clear RB to use R1/R2."
            )

            self.lineRB.setEnabled(True)
            self.lineRB.setToolTip("")
            return

        if not has_r1_or_r2 and not has_rb:
            self.lineR1.setEnabled(True)
            self.lineR2.setEnabled(True)
            self.lineRB.setEnabled(True)

            self.lineR1.setToolTip("")
            self.lineR2.setToolTip("")
            self.lineRB.setToolTip("")
            return

    def open_ce_design_window(self):
        """
        Opens the CE Design/Analysis calculator externally so the user can
        calculate missing resistor values, then return to the frequency page.
        """

        self.ce_design_window = CEDesignAnalysisMenuWidget()
        self.ce_design_window.buttonAnalysis.clicked.emit()
        self.ce_design_window.buttonAnalysis.setChecked(True)
        self.ce_design_window.setWindowTitle("CE Design/Analysis Calculator")
        self.ce_design_window.resize(1100, 750)
        self.ce_design_window.show()

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
        value = self.read_float(line)
        return value * 1e-12 if value is not None else None

    def get_rb(self, r1, r2, rb_direct):
        """
        Return the base resistance RB.

        The UI lock prevents using both methods at the same time:
        - RB direct
        - R1 and R2

        If R1 and R2 are used:
            RB = R1 || R2
        """

        if rb_direct is not None:
            return rb_direct

        if r1 is not None and r2 is not None:
            return parallel(r1, r2)

        return None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            rs = self.read_kohm(self.lineRs)
            r1 = self.read_kohm(self.lineR1)
            r2 = self.read_kohm(self.lineR2)
            rb_direct = self.read_kohm(self.lineRB)

            rc = self.read_kohm(self.lineRC)
            rx = self.read_kohm(self.lineRX)
            rl = self.read_kohm(self.lineRL)

            beta = self.read_float(self.lineBeta)
            rpi = self.read_kohm(self.lineRpi)

            cpi = self.read_pf(self.lineCpi)
            cmu = self.read_pf(self.lineCmu)

            rb = self.get_rb(r1, r2, rb_direct)

            result = {
                "RB": rb,
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

            # ----------------------------------------------------
            # RB = R1 || R2, or RB direct
            # ----------------------------------------------------
            if rb is not None:
                result["RB"] = rb

            # ----------------------------------------------------
            # RSB = RS || RB
            # ----------------------------------------------------
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # ----------------------------------------------------
            # RCL = RC || RL
            # ----------------------------------------------------
            if rc is not None and rl is not None:
                result["RCL"] = parallel(rc, rl)

            # ----------------------------------------------------
            # RXX = rπ + (β + 1)RX
            # ----------------------------------------------------
            if rpi is not None and beta is not None and rx is not None:
                result["RXX"] = rpi + (beta + 1) * rx

            # ----------------------------------------------------
            # Rπ_eq = rπ(RSB + RX) / (RSB + RXX)
            # ----------------------------------------------------
            if (
                rpi is not None
                and rx is not None
                and result["RSB"] is not None
                and result["RXX"] is not None
            ):
                denominator = result["RSB"] + result["RXX"]

                if denominator > 0:
                    result["Rpi_eq"] = (
                        rpi * (result["RSB"] + rx) / denominator
                    )

            # ----------------------------------------------------
            # Rµ_eq =
            # [RXX(RSB + RCL) + (β + 1)RSB RCL] / (RSB + RXX)
            # ----------------------------------------------------
            if (
                beta is not None
                and result["RXX"] is not None
                and result["RSB"] is not None
                and result["RCL"] is not None
            ):
                denominator = result["RSB"] + result["RXX"]

                if denominator > 0:
                    numerator = (
                        result["RXX"] * (result["RSB"] + result["RCL"])
                        + (beta + 1) * result["RSB"] * result["RCL"]
                    )

                    result["Rmu_eq"] = numerator / denominator

            # ----------------------------------------------------
            # fπ = 1 / (2π Rπ_eq Cπ)
            # ----------------------------------------------------
            if result["Rpi_eq"] is not None and cpi is not None:
                result["fpi"] = cutoff_frequency(result["Rpi_eq"], cpi)

            # ----------------------------------------------------
            # fµ = 1 / (2π Rµ_eq Cµ)
            # ----------------------------------------------------
            if result["Rmu_eq"] is not None and cmu is not None:
                result["fmu"] = cutoff_frequency(result["Rmu_eq"], cmu)

            # ----------------------------------------------------
            # High cutoff range only when both fπ and fµ exist:
            #
            # fπ || fµ ≤ fH ≤ min(fπ, fµ)
            # ----------------------------------------------------
            if result["fpi"] is not None and result["fmu"] is not None:
                high = conservative_high_range([result["fpi"], result["fmu"]])
                result.update(high)

            self.show_result(result)
            self.update_calc_status(result)

        except Exception as e:
            self.clear_outputs()
            self.set_calc_status(f"Error: {e}")

    def update_calc_status(self, result):
        if result["fH_conservative"] is not None:
            self.set_calc_status("Calculated")
            return

        available = []

        if result["RB"] is not None:
            available.append("RB")
        if result["RSB"] is not None:
            available.append("RSB")
        if result["RCL"] is not None:
            available.append("RCL")
        if result["RXX"] is not None:
            available.append("RXX")
        if result["Rpi_eq"] is not None:
            available.append("Rπ")
        if result["Rmu_eq"] is not None:
            available.append("Rµ")
        if result["fpi"] is not None:
            available.append("fπ")
        if result["fmu"] is not None:
            available.append("fµ")

        if available:
            self.set_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_calc_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        self.labelRBOut.setText(self.fmt_res(r.get("RB")))
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))
        self.labelRCL.setText(self.fmt_res(r.get("RCL")))
        self.labelRXX.setText(self.fmt_res(r.get("RXX")))

        self.labelRpi.setText(self.fmt_res(r.get("Rpi_eq")))
        self.labelRmu.setText(self.fmt_res(r.get("Rmu_eq")))

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
        labels = [
            self.labelRBOut,
            self.labelRSB,
            self.labelRCL,
            self.labelRXX,
            self.labelRpi,
            self.labelRmu,
            self.labelFpi,
            self.labelFmu,
        ]

        for label in labels:
            label.setText("—")

        self.labelFHConservative.setText("fH conservative: —")
        self.labelFHRange.setText("Range: —")

    def clear_inputs(self):
        lines = [
            self.lineRs,
            self.lineR1,
            self.lineR2,
            self.lineRB,
            self.lineRC,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in lines:
            line.clear()

        self.update_rb_input_lock()
        self.set_required_highlights()

        self.clear_outputs()
        self.set_calc_status("— awaiting calculation —")

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