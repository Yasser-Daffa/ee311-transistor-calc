import os
import sys
import re

from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(
    BASE_DIR,
    "..",
    "..",
    "ui",
    "frequency",
    "cutoff_frequency.ui",
)


class CutoffFrequencyWidget(QWidget):
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
        self.set_low_status("— awaiting calculation —")
        self.set_high_status("— awaiting calculation —")
        self.set_required_highlights()

    def connect_signals(self):
        self.lineLowPoints.textChanged.connect(self.calculate)
        self.lineHighPoints.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def set_low_status(self, text):
        if hasattr(self, "labelLowMode"):
            self.labelLowMode.setText(text)

    def set_high_status(self, text):
        if hasattr(self, "labelHighMode"):
            self.labelHighMode.setText(text)

    def refresh_line_styles(self, *widgets):
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def set_required_highlights(self):
        lines = [
            self.lineLowPoints,
            self.lineHighPoints,
        ]

        for line in lines:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*lines)

    # ------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------

    def parse_frequency_list(self, text, default_unit_multiplier):
        """
        Accepts inputs like:
            10, 12, 15, 50
            10Hz, 12Hz, 15Hz
            10MHz, 12MHz, 14MHz

        default_unit_multiplier:
            Low input default = 1       because low values are usually Hz
            High input default = 1e6    because high values are usually MHz
        """

        text = text.strip()

        if not text:
            return []

        pattern = r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*(mhz|khz|hz)?"
        matches = re.findall(pattern, text.lower())

        values = []

        for number_text, unit_text in matches:
            try:
                value = float(number_text)
            except ValueError:
                continue

            if value <= 0:
                continue

            if unit_text == "mhz":
                value *= 1e6
            elif unit_text == "khz":
                value *= 1e3
            elif unit_text == "hz":
                value *= 1
            else:
                value *= default_unit_multiplier

            values.append(value)

        return values

    def parallel_values(self, values):
        valid = [v for v in values if v is not None and v > 0]

        if not valid:
            return None

        return 1 / sum(1 / v for v in valid)

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        low_points = self.parse_frequency_list(
            self.lineLowPoints.text(),
            default_unit_multiplier=1,      # Hz
        )

        high_points = self.parse_frequency_list(
            self.lineHighPoints.text(),
            default_unit_multiplier=1e6,    # MHz
        )

        low_result = self.calculate_low_range(low_points)
        high_result = self.calculate_high_range(high_points)

        self.show_low_result(low_result)
        self.show_high_result(high_result)

        self.update_low_status(low_result)
        self.update_high_status(high_result)

    def calculate_low_range(self, points):
        result = {
            "count": len(points),
            "max": None,
            "sum": None,
            "fL_conservative": None,
            "fL_min": None,
            "fL_max": None,
        }

        if not points:
            return result

        max_point = max(points)
        sum_points = sum(points)

        result["max"] = max_point
        result["sum"] = sum_points
        result["fL_conservative"] = max_point
        result["fL_min"] = max_point
        result["fL_max"] = sum_points

        return result

    def calculate_high_range(self, points):
        result = {
            "count": len(points),
            "parallel": None,
            "min": None,
            "fH_conservative": None,
            "fH_min": None,
            "fH_max": None,
        }

        if not points:
            return result

        parallel_point = self.parallel_values(points)
        min_point = min(points)

        result["parallel"] = parallel_point
        result["min"] = min_point
        result["fH_conservative"] = parallel_point
        result["fH_min"] = parallel_point
        result["fH_max"] = min_point

        return result

    # ------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------

    def update_low_status(self, result):
        if result["count"] == 0:
            self.set_low_status("— awaiting low-frequency points —")
        else:
            self.set_low_status("Calculated")

    def update_high_status(self, result):
        if result["count"] == 0:
            self.set_high_status("— awaiting high-frequency points —")
        else:
            self.set_high_status("Calculated")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_low_result(self, r):
        self.labelLowCount.setText(str(r["count"]) if r["count"] else "—")
        self.labelLowMax.setText(self.fmt_freq(r["max"]))
        self.labelLowSum.setText(self.fmt_freq(r["sum"]))

        self.labelFLConservative.setText(
            f"fL conservative: {self.fmt_freq(r['fL_conservative'])}"
        )

        if r["fL_min"] is None or r["fL_max"] is None:
            self.labelFLRange.setText("Range: —")
        else:
            self.labelFLRange.setText(
                f"Range: {self.fmt_freq(r['fL_min'])} ≤ fL ≤ {self.fmt_freq(r['fL_max'])}"
            )

    def show_high_result(self, r):
        self.labelHighCount.setText(str(r["count"]) if r["count"] else "—")
        self.labelHighParallel.setText(self.fmt_freq(r["parallel"]))
        self.labelHighMin.setText(self.fmt_freq(r["min"]))

        self.labelFHConservative.setText(
            f"fH conservative: {self.fmt_freq(r['fH_conservative'])}"
        )

        if r["fH_min"] is None or r["fH_max"] is None:
            self.labelFHRange.setText("Range: —")
        else:
            self.labelFHRange.setText(
                f"Range: {self.fmt_freq(r['fH_min'])} ≤ fH ≤ {self.fmt_freq(r['fH_max'])}"
            )

    def clear_outputs(self):
        labels = [
            self.labelLowCount,
            self.labelLowMax,
            self.labelLowSum,
            self.labelHighCount,
            self.labelHighParallel,
            self.labelHighMin,
        ]

        for label in labels:
            label.setText("—")

        self.labelFLConservative.setText("fL conservative: —")
        self.labelFLRange.setText("Range: —")

        self.labelFHConservative.setText("fH conservative: —")
        self.labelFHRange.setText("Range: —")

    def clear_inputs(self):
        self.lineLowPoints.clear()
        self.lineHighPoints.clear()

        self.clear_outputs()
        self.set_low_status("— awaiting calculation —")
        self.set_high_status("— awaiting calculation —")
        self.set_required_highlights()

    def toggle_formulas(self):
        visible = self.labelFormulaText.isVisible()
        self.labelFormulaText.setVisible(not visible)

        if visible:
            self.pushButtonShowFormulas.setText("Show Formulas")
        else:
            self.pushButtonShowFormulas.setText("Hide Formulas")

    # ------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------

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
    w = CutoffFrequencyWidget()
    w.show()
    sys.exit(app.exec())