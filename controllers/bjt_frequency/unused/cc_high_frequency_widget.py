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

from controllers.bjt_amplifiers_controllers.cc_design_analysis_menu_widget import CCDesignAnalysisMenuWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "cc_high_frequency.ui")


class CCHighFrequencyWidget(QWidget):
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
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

        if hasattr(self, "buttonOpen"):
            self.buttonOpen.clicked.connect(self.open_cc_design_window)

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
        CC high frequency uses all these inputs, but the app still calculates
        partial results whenever enough values are entered.
        """

        all_lines = [
            self.lineRs,
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in all_lines:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

    def open_cc_design_window(self):
        """
        Opens the CC Design/Analysis calculator externally so the user can
        calculate missing resistor values, then return to the frequency page.
        """

        self.cc_design_window = CCDesignAnalysisMenuWidget()
        self.cc_design_window.buttonAnalysis.clicked.emit()
        self.cc_design_window.buttonAnalysis.setChecked(True)
        self.cc_design_window.setWindowTitle("CC Design/Analysis Calculator")
        self.cc_design_window.resize(1100, 750)
        self.cc_design_window.show()

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

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            rs = self.read_kohm(self.lineRs)
            rb = self.read_kohm(self.lineRB)
            re = self.read_kohm(self.lineRE)
            rl = self.read_kohm(self.lineRL)

            beta = self.read_float(self.lineBeta)
            rpi = self.read_kohm(self.lineRpi)

            cpi = self.read_pf(self.lineCpi)
            cmu = self.read_pf(self.lineCmu)

            result = {
                "RSB": None,
                "REL": None,
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
            # RSB = RS || RB
            # ----------------------------------------------------
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # ----------------------------------------------------
            # REL = RE || RL
            # ----------------------------------------------------
            if re is not None and rl is not None:
                result["REL"] = parallel(re, rl)

            # ----------------------------------------------------
            # RXX = rπ + (β + 1)REL
            # ----------------------------------------------------
            if (
                rpi is not None
                and beta is not None
                and result["REL"] is not None
            ):
                result["RXX"] = rpi + (beta + 1) * result["REL"]

            # ----------------------------------------------------
            # Rµ_eq = RSB || RXX
            # ----------------------------------------------------
            if result["RSB"] is not None and result["RXX"] is not None:
                result["Rmu_eq"] = parallel(result["RSB"], result["RXX"])

            # ----------------------------------------------------
            # Rπ_eq = rπ || [ RSB + (β + 1)REL ]
            # ----------------------------------------------------
            if (
                rpi is not None
                and beta is not None
                and result["RSB"] is not None
                and result["REL"] is not None
            ):
                right_side = result["RSB"] + (beta + 1) * result["REL"]
                result["Rpi_eq"] = parallel(rpi, right_side)

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

        if result["RSB"] is not None:
            available.append("RSB")
        if result["REL"] is not None:
            available.append("REL")
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
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))
        self.labelREL.setText(self.fmt_res(r.get("REL")))
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
            self.labelRSB,
            self.labelREL,
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
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in lines:
            line.clear()

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
    w = CCHighFrequencyWidget()
    w.show()
    sys.exit(app.exec())