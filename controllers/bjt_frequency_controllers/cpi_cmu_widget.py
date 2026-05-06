import os
import sys
from math import pow

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
    "cpi_cmu.ui",
)


class CpiCmuWidget(QWidget):
    # Default active-mode base-emitter voltage assumption
    ASSUMED_VBE = 0.7

    def __init__(self):
        super().__init__()
        loadUi(UI_PATH, self)

        # True when VE was filled automatically from VB - 0.7
        self.ve_auto_filled = False

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

        # Optional helpful placeholder
        if hasattr(self, "lineVE"):
            self.lineVE.setPlaceholderText("auto: VB - 0.7 if left blank")

    def connect_signals(self):
        for line in self.all_input_lines():
            line.textChanged.connect(self.calculate)

        # If user manually types in VE, stop treating it as auto-filled
        self.lineVE.textEdited.connect(self.mark_ve_as_manual)

        self.pushButtonClear.clicked.connect(self.clear_inputs)
        self.pushButtonShowFormulas.clicked.connect(self.toggle_formulas)

        if hasattr(self, "buttonPreset2N2222A"):
            self.buttonPreset2N2222A.clicked.connect(self.apply_2n2222a_preset)

    def all_input_lines(self):
        return [
            # Transistor model inputs
            self.lineCJC,
            self.lineVJC,
            self.lineCJE,
            self.lineVJE,
            self.lineTF,
            self.lineVT,
            self.lineBeta,

            # DC operating point inputs
            self.lineIC,
            self.lineVB,
            self.lineVC,
            self.lineVE,
        ]

    # ------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------

    def set_status(self, text):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)

    def refresh_line_styles(self, *widgets):
        for w in widgets:
            w.style().unpolish(w)
            w.style().polish(w)
            w.update()

    def mark_ve_as_manual(self):
        """
        Called only when the user manually edits VE.
        After that, the app will respect the user's VE value.
        """
        self.ve_auto_filled = False

    def auto_fill_ve_from_vb(self, vb):
        """
        If VE is blank or was previously auto-filled:
            VE = VB - 0.7

        This lets the calculator use default VBE = 0.7 V.
        """
        if vb is None:
            return None

        ve = vb - self.ASSUMED_VBE

        self.lineVE.blockSignals(True)
        self.lineVE.setText(f"{ve:.4g}")
        self.lineVE.blockSignals(False)

        self.ve_auto_filled = True
        return ve

    def apply_2n2222a_preset(self):
        """
        2N2222A constants from your course/Excel.

        UI units:
        CJC, CJE -> pF
        VJC, VJE -> V
        TF       -> ps
        VT       -> mV
        """

        preset = {
            "CJC_pF": "9.12",
            "VJC_V": "0.41",
            "CJE_pF": "27",
            "VJE_V": "0.8",
            "TF_ps": "325",
            "VT_mV": "25",
        }

        self.lineCJC.setText(str(preset["CJC_pF"]))
        self.lineVJC.setText(str(preset["VJC_V"]))
        self.lineCJE.setText(str(preset["CJE_pF"]))
        self.lineVJE.setText(str(preset["VJE_V"]))
        self.lineTF.setText(str(preset["TF_ps"]))
        self.lineVT.setText(str(preset["VT_mV"]))

        self.set_status("2N2222A preset applied")

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

    def read_pf(self, line):
        value = self.read_float(line)
        return value * 1e-12 if value is not None else None

    def read_ps(self, line):
        value = self.read_float(line)
        return value * 1e-12 if value is not None else None

    def read_mv(self, line):
        value = self.read_float(line)
        return value * 1e-3 if value is not None else None

    def read_ma(self, line):
        value = self.read_float(line)
        return value * 1e-3 if value is not None else None

    # ------------------------------------------------------------
    # Main calculation
    # ------------------------------------------------------------

    def calculate(self):
        try:
            values = self.read_inputs()
            result = self.calculate_capacitances(values)

            self.show_result(result)
            self.update_status(result)

        except Exception as e:
            self.clear_outputs()
            self.set_status(f"Error: {e}")

    def read_inputs(self):
        vb = self.read_float(self.lineVB)
        ve = self.read_float(self.lineVE)

        # If VE is empty, estimate it from VB - 0.7.
        # If VE was auto-filled before, update it again when VB changes.
        if vb is not None and (ve is None or self.ve_auto_filled):
            ve = self.auto_fill_ve_from_vb(vb)

        return {
            # Transistor model values
            "cjc": self.read_pf(self.lineCJC),      # pF -> F
            "vjc": self.read_float(self.lineVJC),   # V
            "cje": self.read_pf(self.lineCJE),      # pF -> F
            "vje": self.read_float(self.lineVJE),   # V
            "tf": self.read_ps(self.lineTF),        # ps -> s
            "vt": self.read_mv(self.lineVT),        # mV -> V
            "beta": self.read_float(self.lineBeta),

            # DC operating point
            "ic": self.read_ma(self.lineIC),        # mA -> A
            "vb": vb,
            "vc": self.read_float(self.lineVC),
            "ve": ve,

            # Extra flag
            "ve_auto": self.ve_auto_filled,
        }

    def calculate_capacitances(self, v):
        result = {
            "VCB": None,
            "VBE": None,
            "Cmu": None,
            "Cpi": None,
            "Rpi": None,
            "warnings": [],
            "used_auto_ve": v.get("ve_auto", False),
        }

        # --------------------------------------------------------
        # Voltage differences
        # --------------------------------------------------------

        # VCB = VC - VB
        if v["vc"] is not None and v["vb"] is not None:
            result["VCB"] = v["vc"] - v["vb"]

        # If VE was auto-filled, force VBE to the default 0.7 V.
        # Otherwise calculate it normally from VB - VE.
        if v["ve_auto"]:
            result["VBE"] = self.ASSUMED_VBE
        elif v["vb"] is not None and v["ve"] is not None:
            result["VBE"] = v["vb"] - v["ve"]

        # --------------------------------------------------------
        # Cµ = CJC / (1 + VCB/VJC)^(1/3)
        # --------------------------------------------------------

        if v["cjc"] is not None and v["vjc"] is not None and result["VCB"] is not None:
            if v["vjc"] == 0:
                result["warnings"].append("VJC cannot be zero")
            else:
                denominator = 1 + (result["VCB"] / v["vjc"])

                if denominator > 0:
                    result["Cmu"] = v["cjc"] / pow(denominator, 1 / 3)
                else:
                    result["warnings"].append("Cµ invalid: 1 + VCB/VJC must be positive")

        # --------------------------------------------------------
        # Rπ = βVT / IC
        # --------------------------------------------------------

        if v["beta"] is not None and v["vt"] is not None and v["ic"] is not None:
            if v["ic"] > 0:
                result["Rpi"] = v["beta"] * v["vt"] / v["ic"]
            else:
                result["warnings"].append("IC must be positive for Rπ")

        # --------------------------------------------------------
        # Cπ = τF(IC/VT) + CJE / (1 - VBE/VJE)^(1/3)
        # --------------------------------------------------------

        diffusion_cap = None
        depletion_cap = None

        # Diffusion part: τF(IC / VT)
        if v["tf"] is not None and v["ic"] is not None and v["vt"] is not None:
            if v["vt"] > 0 and v["ic"] >= 0:
                diffusion_cap = v["tf"] * (v["ic"] / v["vt"])
            else:
                result["warnings"].append("VT must be positive for Cπ diffusion term")

        # Depletion part: CJE / (1 - VBE/VJE)^(1/3)
        if v["cje"] is not None and v["vje"] is not None and result["VBE"] is not None:
            if v["vje"] == 0:
                result["warnings"].append("VJE cannot be zero")
            else:
                denominator = 1 - (result["VBE"] / v["vje"])

                if denominator > 0:
                    depletion_cap = v["cje"] / pow(denominator, 1 / 3)
                else:
                    result["warnings"].append("Cπ invalid: 1 - VBE/VJE must be positive")

        # Full Cπ should only be shown when both terms are available.
        if diffusion_cap is not None and depletion_cap is not None:
            result["Cpi"] = diffusion_cap + depletion_cap

        return result

    # ------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------

    def update_status(self, r):
        calculated = []

        if r["VCB"] is not None:
            calculated.append("VCB")
        if r["VBE"] is not None:
            calculated.append("VBE")
        if r["Cmu"] is not None:
            calculated.append("Cµ")
        if r["Cpi"] is not None:
            calculated.append("Cπ")
        if r["Rpi"] is not None:
            calculated.append("Rπ")

        if r["warnings"]:
            self.set_status("Partial: " + "; ".join(r["warnings"][:2]))
            return

        if calculated:
            suffix = ""

            if r.get("used_auto_ve"):
                suffix += " — VE estimated from VB - 0.7"

            if r["Rpi"] is None:
                suffix += " — enter β to calculate Rπ"

            self.set_status(f"Calculated: {', '.join(calculated)}{suffix}")
            return

        self.set_status("— awaiting required inputs —")

    # ------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------

    def show_result(self, r):
        self.labelVCB.setText(self.fmt_voltage(r.get("VCB")))
        self.labelVBE.setText(self.fmt_voltage(r.get("VBE")))
        self.labelCmu.setText(self.fmt_cap(r.get("Cmu")))
        self.labelCpi.setText(self.fmt_cap(r.get("Cpi")))
        self.labelRpi.setText(self.fmt_res(r.get("Rpi")))

    def clear_outputs(self):
        labels = [
            self.labelVCB,
            self.labelVBE,
            self.labelCmu,
            self.labelCpi,
            self.labelRpi,
        ]

        for label in labels:
            label.setText("—")

    def clear_inputs(self):
        self.ve_auto_filled = False

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

    def fmt_voltage(self, value):
        if value is None:
            return "—"

        return f"{value:.4g} V"

    def fmt_res(self, value):
        if value is None:
            return "—"

        if abs(value) >= 1000:
            return f"{value / 1000:.4g} kΩ"

        return f"{value:.4g} Ω"

    def fmt_cap(self, value):
        if value is None:
            return "—"

        if abs(value) >= 1e-9:
            return f"{value / 1e-9:.4g} nF"

        if abs(value) >= 1e-12:
            return f"{value / 1e-12:.4g} pF"

        return f"{value:.4g} F"


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    w = CpiCmuWidget()
    w.show()
    sys.exit(app.exec())