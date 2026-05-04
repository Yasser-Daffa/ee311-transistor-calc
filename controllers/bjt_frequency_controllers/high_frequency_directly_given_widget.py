import os
import sys
from math import pi

from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.bjt_frequency import (
    cutoff_frequency,
    conservative_high_range,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "high_frequency_directly_given.ui")


class HighFrequencyDirectlyGivenWidget(QWidget):
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
            self.lineRpi,
            self.lineRmu,
            self.lineCpi,
            self.lineCmu,
            self.lineFH,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def set_calc_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def refresh_line_styles(self, *widgets):
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def set_required_highlights(self):
        """
        Required for normal fH analysis:
        Rπ, Rµ, Cπ, Cµ

        Optional:
        fH target, only needed for Cx design.
        """
        all_lines = [
            self.lineRpi,
            self.lineRmu,
            self.lineCpi,
            self.lineCmu,
            self.lineFH,
        ]

        for line in all_lines:
            line.setProperty("requiredInput", False)

        required = [
            self.lineRpi,
            self.lineRmu,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in required:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

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

    def read_mhz(self, line):
        value = self.read_float(line)
        return value * 1e6 if value is not None else None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            rpi = self.read_kohm(self.lineRpi)
            rmu = self.read_kohm(self.lineRmu)

            cpi = self.read_pf(self.lineCpi)
            cmu = self.read_pf(self.lineCmu)

            target_fh = self.read_mhz(self.lineFH)

            result = {
                "Rpi": rpi,
                "Rmu": rmu,
                "fpi": None,
                "fmu": None,
                "fH_min": None,
                "fH_max": None,
                "fH_conservative": None,
                "Cx": None,
                "Cmu_total": None,
                "cx_possible": None,
            }

            # ----------------------------------------------------
            # fπ = 1 / (2π Rπ Cπ)
            # ----------------------------------------------------
            if rpi is not None and cpi is not None:
                result["fpi"] = cutoff_frequency(rpi, cpi)

            # ----------------------------------------------------
            # fµ = 1 / (2π Rµ Cµ)
            # ----------------------------------------------------
            if rmu is not None and cmu is not None:
                result["fmu"] = cutoff_frequency(rmu, cmu)

            # ----------------------------------------------------
            # High cutoff range:
            #
            # fπ || fµ ≤ fH ≤ min(fπ, fµ)
            # ----------------------------------------------------
            if result["fpi"] is not None and result["fmu"] is not None:
                high = conservative_high_range([result["fpi"], result["fmu"]])
                result.update(high)

            # ----------------------------------------------------
            # Cx design:
            #
            # target fH = 1 / [2π(RπCπ + Rµ(Cµ + Cx))]
            #
            # Cx = (1/Rµ)[1/(2πfH) - RπCπ] - Cµ
            # ----------------------------------------------------
            if (
                target_fh is not None
                and rpi is not None
                and rmu is not None
                and cpi is not None
                and cmu is not None
            ):
                cx = (1 / rmu) * (
                    (1 / (2 * pi * target_fh)) - (rpi * cpi)
                ) - cmu

                if cx > 0:
                    result["Cx"] = cx
                    result["Cmu_total"] = cmu + cx
                    result["cx_possible"] = True
                else:
                    result["Cx"] = None
                    result["Cmu_total"] = cmu
                    result["cx_possible"] = False

            self.show_result(result)
            self.update_calc_status(result, target_fh)

        except Exception as e:
            self.clear_outputs()
            self.set_calc_status(f"Error: {e}")

    def update_calc_status(self, result, target_fh):
        if result["cx_possible"] is False:
            self.set_calc_status("Cx design not possible")
            return

        if result["cx_possible"] is True and result["fH_conservative"] is not None:
            self.set_calc_status("Calculated fH and Cx")
            return

        if result["fH_conservative"] is not None:
            self.set_calc_status("Calculated")
            return

        available = []

        if result["fpi"] is not None:
            available.append("fπ")
        if result["fmu"] is not None:
            available.append("fµ")
        if result["Cx"] is not None:
            available.append("Cx")

        if available:
            self.set_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            if target_fh is not None:
                self.set_calc_status("— enter Rπ, Rµ, Cπ, and Cµ to design Cx —")
            else:
                self.set_calc_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        self.labelRpi.setText(self.fmt_res(r.get("Rpi")))
        self.labelRmu.setText(self.fmt_res(r.get("Rmu")))

        self.labelFpi.setText(self.fmt_freq(r.get("fpi")))
        self.labelFmu.setText(self.fmt_freq(r.get("fmu")))

        if r.get("cx_possible") is False:
            self.labelCx.setText("Not possible")
        else:
            self.labelCx.setText(self.fmt_cap(r.get("Cx")))

        self.labelCmuTotal.setText(self.fmt_cap(r.get("Cmu_total")))

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
            self.labelRpi,
            self.labelRmu,
            self.labelFpi,
            self.labelFmu,
            self.labelCx,
            self.labelCmuTotal,
        ]

        for label in labels:
            label.setText("—")

        self.labelFHConservative.setText("fH conservative: —")
        self.labelFHRange.setText("Range: —")

    def clear_inputs(self):
        lines = [
            self.lineRpi,
            self.lineRmu,
            self.lineCpi,
            self.lineCmu,
            self.lineFH,
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

    def fmt_cap(self, value):
        if value is None:
            return "—"

        if abs(value) >= 1e-6:
            return f"{value / 1e-6:.3g} µF"

        if abs(value) >= 1e-9:
            return f"{value / 1e-9:.3g} nF"

        if abs(value) >= 1e-12:
            return f"{value / 1e-12:.3g} pF"

        return f"{value:.3g} F"


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = HighFrequencyDirectlyGivenWidget()
    w.show()
    sys.exit(app.exec())