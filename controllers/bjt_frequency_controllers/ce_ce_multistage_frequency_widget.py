import os
import sys

from PyQt6.QtWidgets import QWidget
from PyQt6.uic import loadUi

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.bjt_frequency import (
    parallel,
    cutoff_frequency,
    conservative_low_range,
    conservative_high_range,
)

from controllers.bjt_multistage_controllers.multistage_choices_widget import MultistageChoicesWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(
    BASE_DIR,
    "..",
    "..",
    "ui",
    "frequency",
    "ce_ce_multistage_frequency.ui",
)


class CECEMultistageFrequencyWidget(QWidget):
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

        self.update_rb1_input_lock()
        self.update_rb2_input_lock()
        self.set_required_highlights()

        self.set_low_status("— awaiting calculation —")
        self.set_high_status("— awaiting calculation —")

    def connect_signals(self):
        for line in self.all_input_lines():
            line.textChanged.connect(self.calculate)

        # Stage 1 RB selector: R1/R2 OR RB1 direct
        self.lineR1.textChanged.connect(self.update_rb1_input_lock)
        self.lineR2.textChanged.connect(self.update_rb1_input_lock)
        self.lineRB1.textChanged.connect(self.update_rb1_input_lock)

        # Stage 2 RB selector: R3/R4 OR RB2 direct
        self.lineR3.textChanged.connect(self.update_rb2_input_lock)
        self.lineR4.textChanged.connect(self.update_rb2_input_lock)
        self.lineRB2.textChanged.connect(self.update_rb2_input_lock)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

        if hasattr(self, "buttonOpen"):
            self.buttonOpen.clicked.connect(self.open_ce_ce_design_window)

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def open_ce_ce_design_window(self):
        self.design_window = MultistageChoicesWidget()
        self.design_window.buttonCECE.clicked.emit()
        self.design_window.buttonCECE.setChecked(True)
        self.design_window.setWindowTitle("Multistage Design/Analysis Calculator")
        self.design_window.resize(1100, 750)
        self.design_window.show()

    def set_low_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def set_high_status(self, text):
        if hasattr(self, "labelHighMode"):
            self.labelHighMode.setText(text)
        elif hasattr(self, "labelMode_2"):
            self.labelMode_2.setText(text)

    def refresh_line_styles(self, *widgets):
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def set_required_highlights(self):
        all_lines = self.all_input_lines()

        for line in all_lines:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

    def update_rb1_input_lock(self):
        """
        Prevent invalid RB1 input combinations for CE stage 1.

        Use either:
        - R1 and R2
        - RB1 direct
        """

        has_r1_or_r2 = bool(self.lineR1.text().strip()) or bool(self.lineR2.text().strip())
        has_rb1 = bool(self.lineRB1.text().strip())

        if has_r1_or_r2 and not has_rb1:
            self.lineRB1.setEnabled(False)
            self.lineRB1.setToolTip(
                "Disabled because R1 or R2 is entered. Clear R1/R2 to use RB1 direct."
            )

            self.lineR1.setEnabled(True)
            self.lineR2.setEnabled(True)
            self.lineR1.setToolTip("")
            self.lineR2.setToolTip("")
            return

        if has_rb1 and not has_r1_or_r2:
            self.lineR1.setEnabled(False)
            self.lineR2.setEnabled(False)
            self.lineR1.setToolTip(
                "Disabled because RB1 direct is entered. Clear RB1 to use R1/R2."
            )
            self.lineR2.setToolTip(
                "Disabled because RB1 direct is entered. Clear RB1 to use R1/R2."
            )

            self.lineRB1.setEnabled(True)
            self.lineRB1.setToolTip("")
            return

        if not has_r1_or_r2 and not has_rb1:
            self.lineR1.setEnabled(True)
            self.lineR2.setEnabled(True)
            self.lineRB1.setEnabled(True)

            self.lineR1.setToolTip("")
            self.lineR2.setToolTip("")
            self.lineRB1.setToolTip("")

    def update_rb2_input_lock(self):
        """
        Prevent invalid RB2 input combinations for CE stage 2.

        Use either:
        - R3 and R4
        - RB2 direct
        """

        has_r3_or_r4 = bool(self.lineR3.text().strip()) or bool(self.lineR4.text().strip())
        has_rb2 = bool(self.lineRB2.text().strip())

        if has_r3_or_r4 and not has_rb2:
            self.lineRB2.setEnabled(False)
            self.lineRB2.setToolTip(
                "Disabled because R3 or R4 is entered. Clear R3/R4 to use RB2 direct."
            )

            self.lineR3.setEnabled(True)
            self.lineR4.setEnabled(True)
            self.lineR3.setToolTip("")
            self.lineR4.setToolTip("")
            return

        if has_rb2 and not has_r3_or_r4:
            self.lineR3.setEnabled(False)
            self.lineR4.setEnabled(False)
            self.lineR3.setToolTip(
                "Disabled because RB2 direct is entered. Clear RB2 to use R3/R4."
            )
            self.lineR4.setToolTip(
                "Disabled because RB2 direct is entered. Clear RB2 to use R3/R4."
            )

            self.lineRB2.setEnabled(True)
            self.lineRB2.setToolTip("")
            return

        if not has_r3_or_r4 and not has_rb2:
            self.lineR3.setEnabled(True)
            self.lineR4.setEnabled(True)
            self.lineRB2.setEnabled(True)

            self.lineR3.setToolTip("")
            self.lineR4.setToolTip("")
            self.lineRB2.setToolTip("")

    def all_input_lines(self):
        return [
            # General
            self.lineRs,
            self.lineRL,
            self.lineBeta,

            # CE stage 1
            self.lineR1,
            self.lineR2,
            self.lineRB1,
            self.lineRC1,
            self.lineRE1,
            self.lineRX1,
            self.lineRpi1,
            self.lineCpi1,
            self.lineCmu1,

            # CE stage 2
            self.lineR3,
            self.lineR4,
            self.lineRB2,
            self.lineRC2,
            self.lineRE2,
            self.lineRX2,
            self.lineRpi2,
            self.lineCpi2,
            self.lineCmu2,

            # Low-frequency capacitors
            self.lineC1,
            self.lineC2,
            self.lineC3,
            self.lineCE1,
            self.lineCE2,
        ]

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

    def read_pf(self, line):
        value = self.read_float(line)
        return value * 1e-12 if value is not None else None

    def get_rb1(self, r1, r2, rb1_direct):
        if rb1_direct is not None:
            return rb1_direct

        if r1 is not None and r2 is not None:
            return parallel(r1, r2)

        return None

    def get_rb2(self, r3, r4, rb2_direct):
        if rb2_direct is not None:
            return rb2_direct

        if r3 is not None and r4 is not None:
            return parallel(r3, r4)

        return None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            values = self.read_inputs()
            low = self.calculate_low(values)
            high = self.calculate_high(values, low)

            self.show_low_result(low)
            self.show_high_result(high)

            self.update_low_status(low)
            self.update_high_status(high)

        except Exception as e:
            self.clear_outputs()
            self.set_low_status(f"Error: {e}")
            self.set_high_status(f"Error: {e}")

    def read_inputs(self):
        r1 = self.read_kohm(self.lineR1)
        r2 = self.read_kohm(self.lineR2)
        rb1_direct = self.read_kohm(self.lineRB1)

        r3 = self.read_kohm(self.lineR3)
        r4 = self.read_kohm(self.lineR4)
        rb2_direct = self.read_kohm(self.lineRB2)

        return {
            # General
            "rs": self.read_kohm(self.lineRs),
            "rl": self.read_kohm(self.lineRL),
            "beta": self.read_float(self.lineBeta),

            # CE stage 1
            "r1": r1,
            "r2": r2,
            "rb1": self.get_rb1(r1, r2, rb1_direct),
            "rc1": self.read_kohm(self.lineRC1),
            "re1": self.read_kohm(self.lineRE1),
            "rx1": self.read_kohm(self.lineRX1),
            "rpi1": self.read_kohm(self.lineRpi1),
            "cpi1": self.read_pf(self.lineCpi1),
            "cmu1": self.read_pf(self.lineCmu1),

            # CE stage 2
            "r3": r3,
            "r4": r4,
            "rb2": self.get_rb2(r3, r4, rb2_direct),
            "rc2": self.read_kohm(self.lineRC2),
            "re2": self.read_kohm(self.lineRE2),
            "rx2": self.read_kohm(self.lineRX2),
            "rpi2": self.read_kohm(self.lineRpi2),
            "cpi2": self.read_pf(self.lineCpi2),
            "cmu2": self.read_pf(self.lineCmu2),

            # Low-frequency capacitors
            "c1": self.read_uf(self.lineC1),
            "c2": self.read_uf(self.lineC2),
            "c3": self.read_uf(self.lineC3),
            "ce1": self.read_uf(self.lineCE1),
            "ce2": self.read_uf(self.lineCE2),
        }

    # ------------------------------------------------------------
    # Low-frequency calculation
    # ------------------------------------------------------------

    def calculate_low(self, v):
        rs = v["rs"]
        rl = v["rl"]
        beta = v["beta"]

        # CE stage 1
        rb1 = v["rb1"]
        rc1 = v["rc1"]
        re1 = v["re1"]
        rx1 = v["rx1"]
        rpi1 = v["rpi1"]

        # CE stage 2
        rb2 = v["rb2"]
        rc2 = v["rc2"]
        re2 = v["re2"]
        rx2 = v["rx2"]
        rpi2 = v["rpi2"]

        # Capacitors
        c1 = v["c1"]
        c2 = v["c2"]
        c3 = v["c3"]
        ce1 = v["ce1"]
        ce2 = v["ce2"]

        result = {
            "RB1": rb1,
            "RB2": rb2,
            "RSB1": None,
            "RSB2": None,
            "RXX1": None,
            "RXX2": None,
            "Ri2": None,
            "R11": None,
            "R22": None,
            "R33": None,
            "REE1": None,
            "REE2": None,
            "f1": None,
            "f2": None,
            "f3": None,
            "fE1": None,
            "fE2": None,
            "fL_min": None,
            "fL_max": None,
            "fL_conservative": None,
        }

        # Stage 1 CE helper values
        if rs is not None and rb1 is not None:
            result["RSB1"] = parallel(rs, rb1)

        if rpi1 is not None and beta is not None and rx1 is not None:
            result["RXX1"] = rpi1 + (beta + 1) * rx1

        # Stage 2 CE helper values
        if rpi2 is not None and beta is not None and rx2 is not None:
            result["RXX2"] = rpi2 + (beta + 1) * rx2

        if rb2 is not None and result["RXX2"] is not None:
            result["Ri2"] = parallel(rb2, result["RXX2"])

        # C1 input coupling:
        # R11 = RS + (RB1 || RXX1)
        if rs is not None and rb1 is not None and result["RXX1"] is not None:
            result["R11"] = rs + parallel(rb1, result["RXX1"])

            if c1 is not None:
                result["f1"] = cutoff_frequency(result["R11"], c1)

        # C2 interstage coupling:
        # R22 = RC1 + Ri2
        if rc1 is not None and result["Ri2"] is not None:
            result["R22"] = rc1 + result["Ri2"]

            if c2 is not None:
                result["f2"] = cutoff_frequency(result["R22"], c2)

        # C3 output coupling:
        # R33 = RC2 + RL
        if rc2 is not None and rl is not None:
            result["R33"] = rc2 + rl

            if c3 is not None:
                result["f3"] = cutoff_frequency(result["R33"], c3)

        # CE1 emitter bypass:
        # REE1 = RE1 || [RX1 + (rπ1 + RSB1)/(β + 1)]
        if (
            re1 is not None
            and rx1 is not None
            and rpi1 is not None
            and beta is not None
            and result["RSB1"] is not None
        ):
            result["REE1"] = parallel(
                re1,
                rx1 + (rpi1 + result["RSB1"]) / (beta + 1),
            )

            if ce1 is not None:
                result["fE1"] = cutoff_frequency(result["REE1"], ce1)

        # RSB2 for CE stage 2:
        # RSB2 = RC1 || RB2
        if rc1 is not None and rb2 is not None:
            result["RSB2"] = parallel(rc1, rb2)

        # CE2 emitter bypass:
        # REE2 = RE2 || [RX2 + (rπ2 + RSB2)/(β + 1)]
        if (
            re2 is not None
            and rx2 is not None
            and rpi2 is not None
            and beta is not None
            and result["RSB2"] is not None
        ):
            result["REE2"] = parallel(
                re2,
                rx2 + (rpi2 + result["RSB2"]) / (beta + 1),
            )

            if ce2 is not None:
                result["fE2"] = cutoff_frequency(result["REE2"], ce2)

        result.update(
            conservative_low_range([
                result["f1"],
                result["f2"],
                result["f3"],
                result["fE1"],
                result["fE2"],
            ])
        )

        return result

    # ------------------------------------------------------------
    # High-frequency calculation
    # ------------------------------------------------------------

    def calculate_high(self, v, low):
        beta = v["beta"]

        # CE stage 1
        rc1 = v["rc1"]
        rx1 = v["rx1"]
        rpi1 = v["rpi1"]

        # CE stage 2
        rc2 = v["rc2"]
        rx2 = v["rx2"]
        rpi2 = v["rpi2"]

        # Capacitors
        cpi1 = v["cpi1"]
        cmu1 = v["cmu1"]
        cpi2 = v["cpi2"]
        cmu2 = v["cmu2"]

        result = {
            "RCL1": None,
            "Rpi1": None,
            "Rmu1": None,
            "fpi1": None,
            "fmu1": None,
            "RCL2": None,
            "Rpi2": None,
            "Rmu2": None,
            "fpi2": None,
            "fmu2": None,
            "fH_min": None,
            "fH_max": None,
            "fH_conservative": None,
        }

        # Stage 1 collector load:
        # RCL1 = RC1 || Ri2
        if rc1 is not None and low.get("Ri2") is not None:
            result["RCL1"] = parallel(rc1, low["Ri2"])

        # Stage 1 Rπ:
        # Rπ1 = rπ1(RSB1 + RX1)/(RSB1 + RXX1)
        if (
            rpi1 is not None
            and rx1 is not None
            and low.get("RSB1") is not None
            and low.get("RXX1") is not None
        ):
            denominator = low["RSB1"] + low["RXX1"]

            if denominator > 0:
                result["Rpi1"] = rpi1 * (low["RSB1"] + rx1) / denominator

        # Stage 1 Rµ:
        # Rµ1 = [RXX1(RSB1 + RCL1) + (β + 1)RSB1RCL1] / (RSB1 + RXX1)
        if (
            beta is not None
            and low.get("RXX1") is not None
            and low.get("RSB1") is not None
            and result["RCL1"] is not None
        ):
            denominator = low["RSB1"] + low["RXX1"]

            if denominator > 0:
                numerator = (
                    low["RXX1"] * (low["RSB1"] + result["RCL1"])
                    + (beta + 1) * low["RSB1"] * result["RCL1"]
                )

                result["Rmu1"] = numerator / denominator

        # Stage 2 collector load:
        # RCL2 = RC2 || RL
        if rc2 is not None and v["rl"] is not None:
            result["RCL2"] = parallel(rc2, v["rl"])

        # Stage 2 Rπ:
        # Rπ2 = rπ2(RSB2 + RX2)/(RSB2 + RXX2)
        if (
            rpi2 is not None
            and rx2 is not None
            and low.get("RSB2") is not None
            and low.get("RXX2") is not None
        ):
            denominator = low["RSB2"] + low["RXX2"]

            if denominator > 0:
                result["Rpi2"] = rpi2 * (low["RSB2"] + rx2) / denominator

        # Stage 2 Rµ:
        # Rµ2 = [RXX2(RSB2 + RCL2) + (β + 1)RSB2RCL2] / (RSB2 + RXX2)
        if (
            beta is not None
            and low.get("RXX2") is not None
            and low.get("RSB2") is not None
            and result["RCL2"] is not None
        ):
            denominator = low["RSB2"] + low["RXX2"]

            if denominator > 0:
                numerator = (
                    low["RXX2"] * (low["RSB2"] + result["RCL2"])
                    + (beta + 1) * low["RSB2"] * result["RCL2"]
                )

                result["Rmu2"] = numerator / denominator

        if result["Rpi1"] is not None and cpi1 is not None:
            result["fpi1"] = cutoff_frequency(result["Rpi1"], cpi1)

        if result["Rmu1"] is not None and cmu1 is not None:
            result["fmu1"] = cutoff_frequency(result["Rmu1"], cmu1)

        if result["Rpi2"] is not None and cpi2 is not None:
            result["fpi2"] = cutoff_frequency(result["Rpi2"], cpi2)

        if result["Rmu2"] is not None and cmu2 is not None:
            result["fmu2"] = cutoff_frequency(result["Rmu2"], cmu2)

        result.update(
            conservative_high_range([
                result["fpi1"],
                result["fmu1"],
                result["fpi2"],
                result["fmu2"],
            ])
        )

        return result

    # ------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------

    def update_low_status(self, result):
        if result["fL_conservative"] is not None:
            self.set_low_status("Calculated")
            return

        checks = [
            ("f1", "f1"),
            ("f2", "f2"),
            ("f3", "f3"),
            ("fE1", "fE1"),
            ("fE2", "fE2"),
        ]

        available = []

        for label, key in checks:
            if result.get(key) is not None:
                available.append(label)

        if available:
            self.set_low_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_low_status("— awaiting required inputs —")

    def update_high_status(self, result):
        if result["fH_conservative"] is not None:
            self.set_high_status("Calculated")
            return

        checks = [
            ("fπ1", "fpi1"),
            ("fµ1", "fmu1"),
            ("fπ2", "fpi2"),
            ("fµ2", "fmu2"),
        ]

        available = []

        for label, key in checks:
            if result.get(key) is not None:
                available.append(label)

        if available:
            self.set_high_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_high_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_low_result(self, r):
        self.labelR11.setText(self.fmt_res(r.get("R11")))
        self.labelR22.setText(self.fmt_res(r.get("R22")))
        self.labelR33.setText(self.fmt_res(r.get("R33")))

        self.labelREE1.setText(self.fmt_res(r.get("REE1")))
        self.labelREE2.setText(self.fmt_res(r.get("REE2")))

        self.labelF1.setText(self.fmt_freq(r.get("f1")))
        self.labelF2.setText(self.fmt_freq(r.get("f2")))
        self.labelF3.setText(self.fmt_freq(r.get("f3")))

        self.labelFE.setText(self.fmt_freq(r.get("fE1")))
        self.labelFE2.setText(self.fmt_freq(r.get("fE2")))

        self.labelFLConservative.setText(
            f"fL conservative: {self.fmt_freq(r.get('fL_conservative'))}"
        )

        if r.get("fL_min") is None or r.get("fL_max") is None:
            self.labelFLRange.setText("Range: —")
        else:
            self.labelFLRange.setText(
                f"Range: {self.fmt_freq(r.get('fL_min'))} ≤ fL ≤ {self.fmt_freq(r.get('fL_max'))}"
            )

    def show_high_result(self, r):
        self.labelRpi1_2.setText(self.fmt_res(r.get("Rpi1")))
        self.labelRmu1.setText(self.fmt_res(r.get("Rmu1")))
        self.labelFpi1.setText(self.fmt_freq(r.get("fpi1")))
        self.labelFmu1.setText(self.fmt_freq(r.get("fmu1")))

        self.labelRpi2_2.setText(self.fmt_res(r.get("Rpi2")))
        self.labelRmu2.setText(self.fmt_res(r.get("Rmu2")))
        self.labelFpi2.setText(self.fmt_freq(r.get("fpi2")))
        self.labelFmu2.setText(self.fmt_freq(r.get("fmu2")))

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
            self.labelR11,
            self.labelR22,
            self.labelR33,
            self.labelREE1,
            self.labelREE2,
            self.labelF1,
            self.labelF2,
            self.labelF3,
            self.labelFE,
            self.labelFE2,
            self.labelRpi1_2,
            self.labelRmu1,
            self.labelFpi1,
            self.labelFmu1,
            self.labelRpi2_2,
            self.labelRmu2,
            self.labelFpi2,
            self.labelFmu2,
        ]

        for label in labels:
            label.setText("—")

        self.labelFLConservative.setText("fL conservative: —")
        self.labelFLRange.setText("Range: —")
        self.labelFHConservative.setText("fH conservative: —")
        self.labelFHRange.setText("Range: —")

    def clear_inputs(self):
        for line in self.all_input_lines():
            line.clear()

        self.update_rb1_input_lock()
        self.update_rb2_input_lock()
        self.set_required_highlights()

        self.clear_outputs()
        self.set_low_status("— awaiting calculation —")
        self.set_high_status("— awaiting calculation —")

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
    w = CECEMultistageFrequencyWidget()
    w.show()
    sys.exit(app.exec())
