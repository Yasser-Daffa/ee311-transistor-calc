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

from controllers.bjt_amplifiers_controllers.cc_design_analysis_menu_widget import (
    CCDesignAnalysisMenuWidget,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "frequency", "cc_low_high_frequency.ui")


class CCLowHighFrequencyWidget(QWidget):
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

        self.buttonFullAnalysis.setChecked(True)

        self.labelFormulaText.hide()
        self.labelHighFormulaText.hide()

        self.clear_low_outputs()
        self.clear_high_outputs()

        self.set_required_highlights()

        self.set_low_calc_status("— awaiting calculation —")
        self.set_high_calc_status("— awaiting calculation —")
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
            self.buttonOpen.clicked.connect(self.open_cc_design_window)

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def open_cc_design_window(self):
        self.cc_design_window = CCDesignAnalysisMenuWidget()
        self.cc_design_window.buttonAnalysis.clicked.emit()
        self.cc_design_window.buttonAnalysis.setChecked(True)
        self.cc_design_window.setWindowTitle("CC Design/Analysis Calculator")
        self.cc_design_window.resize(1100, 750)
        self.cc_design_window.show()

    def set_low_calc_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def set_high_calc_status(self, text):
        # Supports either renamed labelHighMode or Qt auto-name labelMode_2.
        if hasattr(self, "labelHighMode"):
            self.labelHighMode.setText(text)
        elif hasattr(self, "labelMode_2"):
            self.labelMode_2.setText(text)

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

        High-frequency inputs are only highlighted in Full Analysis mode.
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
            self.lineCpi,
            self.lineCmu,
        ]

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
            # Full Analysis = full low-frequency + high-frequency guidance.
            required = [
                self.lineRs,
                self.lineRB,
                self.lineRE,
                self.lineRL,
                self.lineBeta,
                self.lineRpi,
                self.lineC1,
                self.lineC2,
                # self.lineCpi, cause its high-frequency only, but we won't require it for low-freq analysis.
                # self.lineCmu, cause its high-frequency only, but we won't require it for low-freq analysis.
            ]

        for line in required:
            line.setProperty("requiredInput", True)

        self.refresh_line_styles(*all_lines)

    # ------------------------------------------------------------
    # Reading helpers
    # ------------------------------------------------------------
    
    def cc_single_low_formula_html_alt_2(self):
        return """
        <div style="font-family:'Segoe UI'; font-size:13px; color:#1e293b; line-height:1.5;">

        <h2 style="color:#185FA5; margin:0 0 12px 0;">
            CC Low-Frequency Response
        </h2>

        <table width="100%" cellspacing="0" cellpadding="8" style="border-collapse:collapse;">
            <tr>
                <td style="background:#f8fafc; border:1px solid #dbe4f0;">
                    <b style="color:#185FA5;">Helper values</b><br>
                    REL = RE ∥ RL<br>
                    RSB = RS ∥ RB<br>
                    RXX = r<sub style="font-size:85%;">π</sub> + (β + 1)REL
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#eef2ff; border:1px solid #c7d2fe;">
                    <b>Input capacitor C1</b><br>
                    R11 = RS + (RB ∥ RXX)<br>
                    f1 = 1 / (2πR11C1)
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#eef2ff; border:1px solid #c7d2fe;">
                    <b>Output capacitor C2</b><br>
                    R22 = RL + { RE ∥ [(r<sub style="font-size:85%;">π</sub> + RSB) / (β + 1)] }<br>
                    f2 = 1 / (2πR22C2)
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#ecfdf5; border:1px solid #bbf7d0;">
                    <b>Low cutoff range</b><br>
                    max(f1, f2) ≤ fL ≤ f1 + f2<br><br>
                    <b>Conservative:</b><br>
                    fL = max(f1, f2)
                </td>
            </tr>
        </table>

        </div>
        """

    def cc_single_high_formula_html_alt_2(self):
        return """
        <div style="font-family:'Segoe UI'; font-size:13px; color:#1e293b; line-height:1.5;">

        <h2 style="color:#185FA5; margin:0 0 12px 0;">
            CC High-Frequency Response
        </h2>

        <table width="100%" cellspacing="0" cellpadding="8" style="border-collapse:collapse;">
            <tr>
                <td style="background:#f8fafc; border:1px solid #dbe4f0;">
                    <b style="color:#185FA5;">Helper values</b><br>
                    RSB = RS ∥ RB<br>
                    REL = RE ∥ RL<br>
                    RXX = r<sub style="font-size:85%;">π</sub> + (β + 1)REL
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#eef2ff; border:1px solid #c7d2fe;">
                    <b>Equivalent resistance for Cπ</b><br>
                    Rπ = r<sub style="font-size:85%;">π</sub> ∥ [RSB + (β + 1)REL]<br>
                    fπ = 1 / (2πRπCπ)
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#eef2ff; border:1px solid #c7d2fe;">
                    <b>Equivalent resistance for Cµ</b><br>
                    Rµ = RSB ∥ RXX<br>
                    fµ = 1 / (2πRµCµ)
                </td>
            </tr>

            <tr><td height="6"></td></tr>

            <tr>
                <td style="background:#ecfdf5; border:1px solid #bbf7d0;">
                    <b>High cutoff range</b><br>
                    fπ ∥ fµ ≤ fH ≤ min(fπ, fµ)<br><br>
                    <b>Conservative:</b><br>
                    fH = fπ ∥ fµ
                </td>
            </tr>
        </table>

        </div>
        """

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

    # ------------------------------------------------------------
    # Low-frequency mode helpers
    # ------------------------------------------------------------

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

            # REL = RE || RL
            if re is not None and rl is not None:
                result["REL"] = parallel(re, rl)

            # RSB = RS || RB
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # RXX = rπ + (β + 1)REL
            if (
                rpi is not None
                and beta is not None
                and result["REL"] is not None
            ):
                result["RXX"] = rpi + (beta + 1) * result["REL"]

            # R11 = RS + (RB || RXX)
            if (
                rs is not None
                and rb is not None
                and result["RXX"] is not None
            ):
                result["R11"] = rs + parallel(rb, result["RXX"])

                if c1 is not None:
                    result["f1"] = cutoff_frequency(result["R11"], c1)

            # R22 = RL + { RE || [(rπ + RSB)/(β + 1)] }
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

            if mode == "c1_only":
                active_freqs = [result["f1"]]
            elif mode == "c2_only":
                active_freqs = [result["f2"]]
            else:
                active_freqs = [result["f1"], result["f2"]]

            result.update(conservative_low_range(active_freqs))

            self.show_low_result(result)
            self.update_low_calc_status(result)

        except Exception as e:
            self.clear_low_outputs()
            self.set_low_calc_status(f"Error: {e}")

    def calculate_high(self):
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

            # RSB = RS || RB
            if rs is not None and rb is not None:
                result["RSB"] = parallel(rs, rb)

            # REL = RE || RL
            if re is not None and rl is not None:
                result["REL"] = parallel(re, rl)

            # RXX = rπ + (β + 1)REL
            if (
                rpi is not None
                and beta is not None
                and result["REL"] is not None
            ):
                result["RXX"] = rpi + (beta + 1) * result["REL"]

            # Rµ_eq = RSB || RXX
            if result["RSB"] is not None and result["RXX"] is not None:
                result["Rmu_eq"] = parallel(result["RSB"], result["RXX"])

            # Rπ_eq = rπ || [ RSB + (β + 1)REL ]
            if (
                rpi is not None
                and beta is not None
                and result["RSB"] is not None
                and result["REL"] is not None
            ):
                right_side = result["RSB"] + (beta + 1) * result["REL"]
                result["Rpi_eq"] = parallel(rpi, right_side)

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

        if available:
            self.set_low_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_low_calc_status("— awaiting required inputs —")

    def update_high_calc_status(self, result):
        if result["fH_conservative"] is not None:
            self.set_high_calc_status("Calculated")
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
            self.set_high_calc_status(f"Partial: calculated {', '.join(available)}")
        else:
            self.set_high_calc_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_low_result(self, r):
        self.labelREL.setText(self.fmt_res(r.get("REL")))
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))
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

    def show_high_result(self, r):
        self.labelHighRSB.setText(self.fmt_res(r.get("RSB")))
        self.labelHighREL.setText(self.fmt_res(r.get("REL")))
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
            self.labelREL,
            self.labelRSB,
            self.labelRXX,
            self.labelR11,
            self.labelR22,
            self.labelF1,
            self.labelF2,
        ]

        for label in labels:
            label.setText("—")

        self.labelFLConservative.setText("fL conservative: —")
        self.labelFLRange.setText("Range: —")

    def clear_high_outputs(self):
        labels = [
            self.labelHighRSB,
            self.labelHighREL,
            self.labelHighRXX,
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
            self.lineRB,
            self.lineRE,
            self.lineRL,
            self.lineBeta,
            self.lineRpi,
            self.lineC1,
            self.lineC2,
            self.lineCpi,
            self.lineCmu,
        ]

        for line in lines:
            line.clear()

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
    w = CCLowHighFrequencyWidget()
    w.show()
    sys.exit(app.exec())