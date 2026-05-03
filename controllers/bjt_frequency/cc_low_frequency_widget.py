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
        self.mode_group = None

        self.setup_ui()
        self.connect_signals()

    # ------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------

    def setup_ui(self):
        """
        Supports either:
        1. New button UI:
           buttonFullAnalysis, buttonGivenC1, buttonGivenC2

        2. Old combo UI:
           comboMode
        """

        if self.has_mode_buttons():
            self.mode_group = QButtonGroup(self)
            self.mode_group.setExclusive(True)

            self.mode_group.addButton(self.buttonFullAnalysis)
            self.mode_group.addButton(self.buttonGivenC1)
            self.mode_group.addButton(self.buttonGivenC2)

            self.buttonFullAnalysis.setChecked(True)

        elif hasattr(self, "comboMode"):
            self.comboMode.clear()
            self.comboMode.addItems([
                "Full Analysis",
                "Due to C1 only",
                "Due to C2 only",
            ])

        self.labelFormulaText.hide()
        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates any available f1 and f2")

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

        if self.mode_group is not None:
            self.mode_group.buttonClicked.connect(self.on_mode_button_clicked)
        elif hasattr(self, "comboMode"):
            self.comboMode.currentIndexChanged.connect(self.on_mode_button_clicked)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)
        self.buttonOpen.clicked.connect(self.open_cc_design_window)
    def has_mode_buttons(self):
        return (
            hasattr(self, "buttonFullAnalysis")
            and hasattr(self, "buttonGivenC1")
            and hasattr(self, "buttonGivenC2")
        )

    # ------------------------------------------------------------
    # Mode helpers
    # ------------------------------------------------------------

    def open_cc_design_window(self):
        """
        Opens the CC Design calculator externally so the user can calculate
        missing resistor values, then return to the frequency page.
        """
        self.cc_design_window = CCDesignAnalysisMenuWidget()
        self.cc_design_window.buttonAnalysis.clicked.emit()  # trigger analysis page setup
        self.cc_design_window.buttonAnalysis.setChecked(True)  # set analysis page button as checked
        self.cc_design_window.setWindowTitle("CC Design/Analysis Calculator")
        self.cc_design_window.resize(1100, 750)
        self.cc_design_window.show()



    def get_mode_key(self):
        if self.has_mode_buttons():
            if self.buttonGivenC1.isChecked():
                return "c1_only"

            if self.buttonGivenC2.isChecked():
                return "c2_only"

            return "full"

        if hasattr(self, "comboMode"):
            text = self.comboMode.currentText()

            if text == "Due to C1 only":
                return "c1_only"

            if text == "Due to C2 only":
                return "c2_only"

        return "full"

    def get_mode_text(self):
        mode = self.get_mode_key()

        if mode == "c1_only":
            return "Due to C1 only"

        if mode == "c2_only":
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
            # This is a helper value for:
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
            # R22 = RL + [ RE || ((rπ + RSB)/(β + 1)) ]
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
        self.labelREL.setText(self.fmt_res(r.get("REL")))
        self.labelRSB.setText(self.fmt_res(r.get("RSB")))

        # If you added labelRXX to the UI, this will fill it.
        # If not, the widget still works.
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

        if self.has_mode_buttons():
            self.buttonFullAnalysis.setChecked(True)
        elif hasattr(self, "comboMode"):
            self.comboMode.setCurrentIndex(0)

        self.clear_outputs()
        self.set_status("Choice picked: Full Analysis — calculates any available f1 and f2")
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