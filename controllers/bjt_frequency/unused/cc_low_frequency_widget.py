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

from controllers.bjt_amplifiers_controllers.cc_design_analysis_menu_widget import CCDesignAnalysisMenuWidget


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "cc_low_frequency.ui")


class CCLowFrequencyWidget(QWidget):
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
        # Make the three mode buttons behave like radio buttons:
        # only one can be checked at a time.
        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)

        self.mode_group.addButton(self.buttonFullAnalysis)
        self.mode_group.addButton(self.buttonGivenC1)
        self.mode_group.addButton(self.buttonGivenC2)

        self.buttonFullAnalysis.setChecked(True)
        self.set_required_highlights()

        self.labelFormulaText.hide()
        self.clear_outputs()
        self.set_calc_status("— awaiting calculation —")
        self.set_choice_text(self.get_mode_hint())

    def connect_signals(self):
        inputs = [
            self.lineRs,
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
        ]

        for line in inputs:
            line.textChanged.connect(self.calculate)

        self.mode_group.buttonClicked.connect(self.on_mode_button_clicked)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

        if hasattr(self, "buttonOpen"):
            self.buttonOpen.clicked.connect(self.open_cc_design_window)

    # ------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------

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
        Highlight the inputs needed for the selected calculation mode.
        This does NOT disable fields. It only visually guides the user.
        """

        all_lines = [
            self.lineRs,
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
        ]

        # Clear old highlights
        for line in all_lines:
            line.setProperty("requiredInput", False)

        mode = self.get_mode_key()

        if mode == "c1_only":
            required = [
                self.lineRs,
                self.lineRB,
                self.lineRE,
                self.lineRL,
                self.lineBeta,
                self.lineRpi,
                self.lineC1,
            ]

        elif mode == "c2_only":
            required = [
                self.lineRs,
                self.lineRB,
                self.lineRE,
                self.lineRL,
                self.lineBeta,
                self.lineRpi,
                self.lineC2,
            ]

        else:
            # Full analysis: highlight all useful inputs.
            # C1 and C2 are highlighted because they define f1/f2.
            required = [
                self.lineRs,
                self.lineRB,
                self.lineRE,
                self.lineRL,
                self.lineBeta,
                self.lineRpi,
                self.lineC1,
                self.lineC2,
            ]

        for line in required:
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

    def get_mode_key(self):
        if self.buttonGivenC1.isChecked():
            return "c1_only"

        if self.buttonGivenC2.isChecked():
            return "c2_only"

        return "full"

    def get_mode_text(self):
        if self.buttonGivenC1.isChecked():
            return "Due to C1 only"

        if self.buttonGivenC2.isChecked():
            return "Due to C2 only"

        return "Full Analysis"

    def get_mode_hint(self):
        mode = self.get_mode_key()

        if mode == "c1_only":
            return "Choice picked: C1 only — needs Rs, RB, RE, RL, β, rπ, and C1"

        if mode == "c2_only":
            return "Choice picked: C2 only — needs Rs, RB, RE, RL, β, rπ, and C2"

        return "Choice picked: Full Analysis — calculates any available f1 and f2"

    def on_mode_button_clicked(self):
        self.set_required_highlights()
        self.set_choice_text(self.get_mode_hint())
        self.calculate()
        self.animate_choice_label()

    def set_calc_status(self, text):
        """
        labelMode = calculation status only.
        Example: awaiting calculation, partial result, calculated, error.
        """
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def set_choice_text(self, text):
        """
        labelChoicePicked = selected mode / required inputs.
        """
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

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            mode = self.get_mode_key()

            rs = self.read_kohm(self.lineRs)
            rb = self.read_kohm(self.lineRB)
            re = self.read_kohm(self.lineRE)
            rl = self.read_kohm(self.lineRL)

            beta = self.read_float(self.lineBeta)
            rpi = self.read_kohm(self.lineRpi)

            c1 = self.read_uf(self.lineC1)
            c2 = self.read_uf(self.lineC2)

            result = {
                "REL": None,
                "RSB": None,
                "RXX": None,
                "R11": None,
                "R22": None,
                "f1": None,
                "f2": None,
                "fL_min": None,
                "fL_max": None,
                "fL_conservative": None,
            }

            # ----------------------------------------------------
            # REL = RE || RL
            # ----------------------------------------------------
            if re is not None and rl is not None:
                result["REL"] = parallel(re, rl)

            # ----------------------------------------------------
            # RSB = RS || RB
            # ----------------------------------------------------
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # ----------------------------------------------------
            # RXX = rπ + (β + 1)REL
            #
            # Helper value for:
            # R11 = RS + (RB || RXX)
            # ----------------------------------------------------
            if (
                rpi is not None
                and beta is not None
                and result["REL"] is not None
            ):
                result["RXX"] = rpi + (beta + 1) * result["REL"]

            # ----------------------------------------------------
            # R11 and f1
            #
            # R11 = RS + (RB || RXX)
            # f1 = 1 / (2π R11 C1)
            # ----------------------------------------------------
            if (
                rs is not None
                and rb is not None
                and result["RXX"] is not None
            ):
                result["R11"] = rs + parallel(rb, result["RXX"])

                if c1 is not None:
                    result["f1"] = cutoff_frequency(result["R11"], c1)

            # ----------------------------------------------------
            # R22 and f2
            #
            # R22 = RL + { RE || [(rπ + RSB)/(β + 1)] }
            # f2 = 1 / (2π R22 C2)
            # ----------------------------------------------------
            if (
                rl is not None
                and re is not None
                and rpi is not None
                and beta is not None
                and result["RSB"] is not None
            ):
                result["R22"] = rl + parallel(
                    re,
                    (rpi + result["RSB"]) / (beta + 1),
                )

                if c2 is not None:
                    result["f2"] = cutoff_frequency(result["R22"], c2)

            # ----------------------------------------------------
            # Mode filtering
            # ----------------------------------------------------
            if mode == "c1_only":
                active_freqs = [result["f1"]]

            elif mode == "c2_only":
                active_freqs = [result["f2"]]

            else:
                active_freqs = [result["f1"], result["f2"]]

            low = conservative_low_range(active_freqs)
            result.update(low)

            self.show_result(result)

            if result["fL_conservative"] is None:
                available = []

                if result["f1"] is not None:
                    available.append("f1")
                if result["f2"] is not None:
                    available.append("f2")

                if available:
                    self.set_calc_status(f"Partial: calculated {', '.join(available)}")
                else:
                    self.set_calc_status("— awaiting required inputs —")
            else:
                self.set_calc_status("Calculated")

        except Exception as e:
            self.clear_outputs()
            self.set_calc_status(f"Error: {e}")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        self.labelREL.setText(self.fmt_res(r.get("REL")))
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))

        if hasattr(self, "labelRXX"):
            self.labelRXX.setText(self.fmt_res(r.get("RXX")))

        self.labelR11.setText(self.fmt_res(r.get("R11")))
        self.labelR22.setText(self.fmt_res(r.get("R22")))

        self.labelF1.setText(self.fmt_freq(r.get("f1")))
        self.labelF2.setText(self.fmt_freq(r.get("f2")))

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
            self.labelREL,
            self.labelRSB,
            self.labelR11,
            self.labelR22,
            self.labelF1,
            self.labelF2,
        ]

        if hasattr(self, "labelRXX"):
            labels.insert(2, self.labelRXX)

        for label in labels:
            label.setText("—")

        self.labelFLConservative.setText("fL conservative: —")
        self.labelFLRange.setText("Range: —")

    def clear_inputs(self):
        lines = [
            self.lineRs,
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
        ]

        for line in lines:
            line.clear()

        # Keep the currently selected mode.
        # Do NOT force buttonFullAnalysis here.

        self.set_required_highlights()

        self.clear_outputs()
        self.set_calc_status("— awaiting calculation —")
        self.set_choice_text(self.get_mode_hint())
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
    w = CCLowFrequencyWidget()
    w.show()
    sys.exit(app.exec())