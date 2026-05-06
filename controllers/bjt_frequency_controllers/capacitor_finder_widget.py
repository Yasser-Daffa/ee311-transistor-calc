import os
import sys
from math import pi

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
    "capacitor_finder.ui",
)


class CapacitorFinderWidget(QWidget):
    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        if hasattr(self, "labelFormulaText"):
            self.labelFormulaText.hide()

        self.clear_outputs()
        self.set_status("— awaiting calculation —")

    def connect_signals(self):
        for line in self.all_input_lines():
            line.textChanged.connect(self.calculate)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

    def all_input_lines(self):
        return [
            self.lineFLTarget,
            self.lineR11,
            self.lineR22,
            self.lineR33,
            self.lineREE,
            self.lineREE1,
            self.lineREE2,
        ]

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def set_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def set_label(self, label_name, text):
        if hasattr(self, label_name):
            getattr(self, label_name).setText(text)

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

    def read_hz(self, line):
        """
        fL input is always in Hz.

        Example:
            10 means 10 Hz
            80 means 80 Hz
        """
        value = self.read_float(line)
        return value if value is not None and value > 0 else None

    def read_kohm(self, line):
        """
        Resistance inputs are always in kΩ.

        Examples:
            R11 = 11.4 kΩ  -> enter 11.4
            R22 = 200 Ω    -> enter 0.2
            REE = 56 Ω     -> enter 0.056
        """
        value = self.read_float(line)
        return value * 1000 if value is not None and value > 0 else None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            fL = self.read_hz(self.lineFLTarget)

            resistances = {
                "C1": self.read_kohm(self.lineR11),
                "C2": self.read_kohm(self.lineR22),
                "C3": self.read_kohm(self.lineR33),
                "CE": self.read_kohm(self.lineREE),
                "CE1": self.read_kohm(self.lineREE1),
                "CE2": self.read_kohm(self.lineREE2),
            }

            result = self.calculate_caps(fL, resistances)

            self.show_result(result)
            self.update_status(result)

        except Exception as e:
            self.clear_outputs()
            self.set_status(f"Error: {e}")

    def calculate_caps(self, fL, resistances):
        result = {
            "fL": fL,
            "caps": {},
            "common_cap": None,
            "dominant_name": None,
            "dominant_resistance": None,
            "common_f_points": {},
            "common_fl_min": None,
            "common_fl_max": None,
        }

        if fL is None:
            return result

        # --------------------------------------------------------
        # Individual capacitor values
        #
        # Each capacitor value makes its own cutoff point equal fL:
        #     C_i = 1 / (2π R_i fL)
        #
        # This is useful when the question asks for C1 and C2 separately.
        # --------------------------------------------------------
        for cap_name, resistance in resistances.items():
            if resistance is not None:
                result["caps"][cap_name] = 1 / (2 * pi * resistance * fL)
            else:
                result["caps"][cap_name] = None

        # --------------------------------------------------------
        # Common capacitor value
        #
        # If the question says:
        #     C1 = C2 = CE = C
        #
        # then:
        #     fL ≈ f1 + f2 + fE
        #
        # and:
        #     f_i = 1 / (2π R_i C)
        #
        # so:
        #     fL = (1 / 2πC) * Σ(1/R_i)
        #
        # therefore:
        #     Ccommon = Σ(1/R_i) / (2π fL)
        # --------------------------------------------------------
        valid_resistances = [
            (cap_name, resistance)
            for cap_name, resistance in resistances.items()
            if resistance is not None
        ]

        if valid_resistances:
            conductance_sum = sum(
                1 / resistance
                for _, resistance in valid_resistances
            )

            common_cap = conductance_sum / (2 * pi * fL)

            result["common_cap"] = common_cap

            # Dominant point = smallest resistance.
            # It contributes the largest individual cutoff point.
            dominant_name, dominant_resistance = min(
                valid_resistances,
                key=lambda item: item[1],
            )

            result["dominant_name"] = dominant_name
            result["dominant_resistance"] = dominant_resistance

            # Check the resulting low-frequency points if Ccommon is used.
            f_points = {}

            for cap_name, resistance in valid_resistances:
                f_points[cap_name] = 1 / (2 * pi * resistance * common_cap)

            result["common_f_points"] = f_points

            if f_points:
                result["common_fl_min"] = max(f_points.values())
                result["common_fl_max"] = sum(f_points.values())

        return result

    # ------------------------------------------------------------
    # Status
    # ------------------------------------------------------------

    def update_status(self, result):
        if result["fL"] is None:
            self.set_status("— enter target fL —")
            return

        calculated = [
            name
            for name, cap in result["caps"].items()
            if cap is not None
        ]

        if calculated:
            self.set_status(f"Calculated: {', '.join(calculated)}")
        else:
            self.set_status("— enter at least one resistance value —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        caps = r["caps"]

        self.set_label("labelC1", self.fmt_cap_micro(caps.get("C1")))
        self.set_label("labelC2", self.fmt_cap_micro(caps.get("C2")))
        self.set_label("labelC3", self.fmt_cap_micro(caps.get("C3")))
        self.set_label("labelCE", self.fmt_cap_micro(caps.get("CE")))
        self.set_label("labelCE1", self.fmt_cap_micro(caps.get("CE1")))
        self.set_label("labelCE2", self.fmt_cap_micro(caps.get("CE2")))

        self.set_label("labelCCommon", self.fmt_cap_micro(r.get("common_cap")))

        if r.get("dominant_resistance") is None:
            self.set_label("labelControllingR", "—")
        else:
            self.set_label(
                "labelControllingR",
                f"{r['dominant_name']} point, {self.fmt_res(r['dominant_resistance'])}",
            )

        if r.get("common_fl_max") is None:
            self.set_label("labelFLCheck", "—")
        else:
            self.set_label(
                "labelFLCheck",
                f"Common-cap conservative fL ≈ {self.fmt_freq(r['common_fl_max'])}",
            )

        # Optional output label if your UI has it.
        if hasattr(self, "labelFLRange"):
            if r.get("common_fl_min") is None or r.get("common_fl_max") is None:
                self.labelFLRange.setText("Range: —")
            else:
                self.labelFLRange.setText(
                    f"Range: {self.fmt_freq(r['common_fl_min'])} ≤ fL ≤ {self.fmt_freq(r['common_fl_max'])}"
                )

    def clear_outputs(self):
        labels = [
            "labelC1",
            "labelC2",
            "labelC3",
            "labelCE",
            "labelCE1",
            "labelCE2",
            "labelCCommon",
            "labelControllingR",
            "labelFLCheck",
        ]

        for label_name in labels:
            self.set_label(label_name, "—")

        if hasattr(self, "labelFLRange"):
            self.labelFLRange.setText("Range: —")

    def clear_inputs(self):
        for line in self.all_input_lines():
            line.clear()

        self.clear_outputs()
        self.set_status("— awaiting calculation —")

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

    def fmt_res(self, value):
        if value is None:
            return "—"

        if abs(value) >= 1e6:
            return f"{value / 1e6:.5g} MΩ"

        if abs(value) >= 1000:
            return f"{value / 1000:.5g} kΩ"

        return f"{value:.5g} Ω"

    def fmt_freq(self, value):
        if value is None:
            return "—"

        if abs(value) >= 1e6:
            return f"{value / 1e6:.5g} MHz"

        if abs(value) >= 1000:
            return f"{value / 1000:.5g} kHz"

        return f"{value:.5g} Hz"

    def fmt_cap_micro(self, value):
        """
        Output labels are in µF, so always display capacitance in µF.
        """
        if value is None:
            return "—"

        return f"{value / 1e-6:.5g} µF"


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = CapacitorFinderWidget()
    w.show()
    sys.exit(app.exec())