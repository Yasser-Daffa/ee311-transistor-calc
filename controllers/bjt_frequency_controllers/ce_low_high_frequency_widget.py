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
    conservative_high_range,
)

from controllers.bjt_amplifiers_controllers.ce_design_analysis_menu_widget import (
    CEDesignAnalysisMenuWidget,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "ce_low_high_frequency.ui")


class CELowHighFrequencyWidget(QWidget):
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
        # Low-frequency mode buttons only.
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_group.addButton(self.buttonFullAnalysis)
        self.mode_group.addButton(self.buttonGivenC1)
        self.mode_group.addButton(self.buttonGivenC2)
        self.mode_group.addButton(self.buttonGivenCE)

        self.buttonFullAnalysis.setChecked(True)

        self.labelFormulaText.hide()
        self.labelHighFormulaText.hide()

        self.clear_low_outputs()
        self.clear_high_outputs()

        self.update_rb_input_lock()
        self.set_required_highlights()

        self.set_low_calc_status("— awaiting calculation —")
        self.set_high_calc_status("— awaiting calculation —")
        self.set_choice_text(self.get_mode_hint())

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
            self.lineCpi,
            self.lineCmu,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.mode_group.buttonClicked.connect(self.on_mode_button_clicked)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_low_formulas)
        self.pushButtonShowHighFormulas.clicked.connect(self.toggle_high_formulas)

        if hasattr(self, "buttonOpen"):
            self.buttonOpen.clicked.connect(self.open_ce_design_window)

        self.lineR1.textChanged.connect(self.update_rb_input_lock)
        self.lineR2.textChanged.connect(self.update_rb_input_lock)
        self.lineRB.textChanged.connect(self.update_rb_input_lock)

    # ------------------------------------------------------------
    # Shared UI helpers
    # ------------------------------------------------------------

    def open_ce_design_window(self):
        self.ce_design_window = CEDesignAnalysisMenuWidget()
        self.ce_design_window.buttonAnalysis.clicked.emit()
        self.ce_design_window.buttonAnalysis.setChecked(True)
        self.ce_design_window.setWindowTitle("CE Design/Analysis Calculator")
        self.ce_design_window.resize(1100, 750)
        self.ce_design_window.show()

    def set_low_calc_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def set_high_calc_status(self, text):
        if hasattr(self, "labelHighMode"):
            self.labelHighMode.setText(text)

    def set_choice_text(self, text):
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

    def refresh_line_styles(self, *widgets):
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def set_required_highlights(self):
        """
        Highlight only the inputs needed for the selected LOW-frequency mode.

        Important:
        High-frequency inputs are only highlighted in Full Analysis mode.
        This prevents Cπ/Cµ and high-only fields from being highlighted when
        the user chooses Due to C1, Due to C2, or Due to CE.
        """

        all_lines = [
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
            self.lineCpi,
            self.lineCmu,
        ]

        for line in all_lines:
            line.setProperty("requiredInput", False)

        mode = self.get_mode_key()

        if mode == "c1_only":
            required = [
                self.lineRs,
                self.lineR1,
                self.lineR2,
                self.lineRB,
                self.lineBeta,
                self.lineRpi,
                self.lineRX,
                self.lineC1,
            ]

        elif mode == "c2_only":
            required = [
                self.lineRC,
                self.lineRL,
                self.lineC2,
            ]

        elif mode == "ce_only":
            required = [
                self.lineRE,
                self.lineRX,
                self.lineBeta,
                self.lineRpi,
                self.lineRs,
                self.lineR1,
                self.lineR2,
                self.lineRB,
                self.lineCE,
            ]

        else:
            # Full Analysis = full low-frequency + high-frequency guidance.
            required = [
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
                self.lineCpi,
                self.lineCmu,
            ]

        for line in required:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

    def update_rb_input_lock(self):
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

    def get_rb(self, r1, r2, rb_direct):
        if rb_direct is not None:
            return rb_direct

        if r1 is not None and r2 is not None:
            return parallel(r1, r2)

        return None

    # ------------------------------------------------------------
    # Low-frequency mode helpers
    # ------------------------------------------------------------

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
        self.set_required_highlights()
        self.set_choice_text(self.get_mode_hint())
        self.calculate()
        self.animate_choice_label()

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        self.calculate_low()
        self.calculate_high()

    def calculate_low(self):
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

            if rpi is not None and beta is not None and rx is not None:
                result["RXX"] = rpi + (beta + 1) * rx

            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            if rs is not None and rb is not None and result["RXX"] is not None:
                result["R11"] = rs + parallel(rb, result["RXX"])

                if c1 is not None:
                    result["f1"] = cutoff_frequency(result["R11"], c1)

            if rc is not None and rl is not None:
                result["R22"] = rc + rl

                if c2 is not None:
                    result["f2"] = cutoff_frequency(result["R22"], c2)

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

            if mode == "c1_only":
                active_freqs = [result["f1"]]
            elif mode == "c2_only":
                active_freqs = [result["f2"]]
            elif mode == "ce_only":
                active_freqs = [result["fE"]]
            else:
                active_freqs = [result["f1"], result["f2"], result["fE"]]

            result.update(conservative_low_range(active_freqs))

            self.show_low_result(result)
            self.update_low_calc_status(result)

        except Exception as e:
            self.clear_low_outputs()
            self.set_low_calc_status(f"Error: {e}")

    def calculate_high(self):
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

            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            if rc is not None and rl is not None:
                result["RCL"] = parallel(rc, rl)

            if rpi is not None and beta is not None and rx is not None:
                result["RXX"] = rpi + (beta + 1) * rx

            if (
                rpi is not None
                and rx is not None
                and result["RSB"] is not None
                and result["RXX"] is not None
            ):
                denominator = result["RSB"] + result["RXX"]

                if denominator > 0:
                    result["Rpi_eq"] = rpi * (result["RSB"] + rx) / denominator

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

            if result["Rpi_eq"] is not None and cpi is not None:
                result["fpi"] = cutoff_frequency(result["Rpi_eq"], cpi)

            if result["Rmu_eq"] is not None and cmu is not None:
                result["fmu"] = cutoff_frequency(result["Rmu_eq"], cmu)

            if result["fpi"] is not None and result["fmu"] is not None:
                result.update(conservative_high_range([result["fpi"], result["fmu"]]))

            self.show_high_result(result)
            self.update_high_calc_status(result)

        except Exception as e:
            self.clear_high_outputs()
            self.set_high_calc_status(f"Error: {e}")

    # ------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------

    def update_low_calc_status(self, result):
        if result["fL_conservative"] is not None:
            self.set_low_calc_status("Calculated")
            return

        available = []

        if result["f1"] is not None:
            available.append("f1")
        if result["f2"] is not None:
            available.append("f2")
        if result["fE"] is not None:
            available.append("fE")

        if available:
            self.set_low_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_low_calc_status("— awaiting required inputs —")

    def update_high_calc_status(self, result):
        if result["fH_conservative"] is not None:
            self.set_high_calc_status("Calculated")
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
            self.set_high_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_high_calc_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_low_result(self, r):
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

    def show_high_result(self, r):
        self.labelHighRBOut.setText(self.fmt_res(r.get("RB")))
        self.labelHighRSB.setText(self.fmt_res(r.get("RSB")))
        self.labelHighRCL.setText(self.fmt_res(r.get("RCL")))
        self.labelHighRXX.setText(self.fmt_res(r.get("RXX")))

        self.labelHighRpi.setText(self.fmt_res(r.get("Rpi_eq")))
        self.labelHighRmu.setText(self.fmt_res(r.get("Rmu_eq")))

        self.labelHighFpi.setText(self.fmt_freq(r.get("fpi")))
        self.labelHighFmu.setText(self.fmt_freq(r.get("fmu")))

        self.labelFHConservative.setText(
            f"fH conservative: {self.fmt_freq(r.get('fH_conservative'))}"
        )

        if r.get("fH_min") is None or r.get("fH_max") is None:
            self.labelFHRange.setText("Range: —")
        else:
            self.labelFHRange.setText(
                f"Range: {self.fmt_freq(r.get('fH_min'))} ≤ fH ≤ {self.fmt_freq(r.get('fH_max'))}"
            )

    def clear_low_outputs(self):
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

    def clear_high_outputs(self):
        labels = [
            self.labelHighRBOut,
            self.labelHighRXX,
            self.labelHighRSB,
            self.labelHighRCL,
            self.labelHighRpi,
            self.labelHighRmu,
            self.labelHighFpi,
            self.labelHighFmu,
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
            self.lineRE,
            self.lineRX,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
            self.lineCE,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in lines:
            line.clear()

        self.update_rb_input_lock()
        self.set_required_highlights()

        self.clear_low_outputs()
        self.clear_high_outputs()

        self.set_low_calc_status("— awaiting calculation —")
        self.set_high_calc_status("— awaiting calculation —")
        self.set_choice_text(self.get_mode_hint())
        self.animate_choice_label()

    def toggle_low_formulas(self):
        visible = self.labelFormulaText.isVisible()
        self.labelFormulaText.setVisible(not visible)

        if visible:
            self.pushButtonShowFormulas.setText(" Show Formulas")
        else:
            self.pushButtonShowFormulas.setText(" Hide Formulas")

    def toggle_high_formulas(self):
        visible = self.labelHighFormulaText.isVisible()
        self.labelHighFormulaText.setVisible(not visible)

        if visible:
            self.pushButtonShowHighFormulas.setText(" Show High Formulas")
        else:
            self.pushButtonShowHighFormulas.setText(" Hide High Formulas")

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
    w = CELowHighFrequencyWidget()
    w.show()
    sys.exit(app.exec())