import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton
from PyQt6.uic import loadUi

# controllers/bjt_multistage_controllers/buffer_analysis_widget.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from core.core_helpers import fmt, positive_validator
from core.bjt_amplifiers import parallel

UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design_buffer_solver2.ui")


class BufferAnalysisWidget(QWidget):
    """
    Multistage buffer-analysis controller.

    Modes:
        CC-CE     -> input buffer only
        CE-CC     -> output buffer only
        CC-CE-CC  -> input + output buffer around an existing CE stage

    UI units:
        Ri, Ro, RL, RE, RB, rpi, Rs are entered in kΩ.
        Av0 and beta are unitless.

    Core units:
        all resistances are converted to Ω.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self.mode = "CC-CE"
        self._clearing = False

        self._setup_ui()
        self._setup_validators()
        self._setup_connections()
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- setup ----------------

    def _setup_ui(self):
        self._ensure_combined_button()

        for name in ["pushButton_CCCE", "pushButton_CECC", "pushButton_CCCECC"]:
            btn = getattr(self, name, None)
            if isinstance(btn, QPushButton):
                btn.setCheckable(True)
                btn.setAutoExclusive(False)

        self._sync_buttons()
        self._update_mode_text()

    def _ensure_combined_button(self):
        """Add the CC-CE-CC button in code if it is not in the .ui yet."""
        if hasattr(self, "pushButton_CCCECC"):
            return

        btn = QPushButton("CC-CE-CC", self)
        btn.setObjectName("pushButton_CCCECC")

        # Reuse the same style as your existing mode buttons.
        ref = getattr(self, "pushButton_CCCE", None)
        if ref is not None:
            btn.setStyleSheet(ref.styleSheet())
            btn.setMinimumHeight(ref.minimumHeight())
            btn.setSizePolicy(ref.sizePolicy())

        layout = getattr(self, "topoLayout", None)
        if layout is not None:
            layout.addWidget(btn)

        self.pushButton_CCCECC = btn

    def _setup_validators(self):
        for name in [
            "lineEditRl", "lineEditRi", "lineEditRo", "lineEditAv0",
            "lineEditRe", "lineEditRb", "lineEditRpi", "lineEditBeta", "lineEditRs",
        ]:
            if hasattr(self, name):
                getattr(self, name).setValidator(positive_validator(self))

    def _setup_connections(self):
        for edit in self.findChildren(QLineEdit):
            edit.textChanged.connect(self.calculate)

        if hasattr(self, "pushButton_CCCE"):
            self.pushButton_CCCE.clicked.connect(lambda: self.set_mode("CC-CE"))
        if hasattr(self, "pushButton_CECC"):
            self.pushButton_CECC.clicked.connect(lambda: self.set_mode("CE-CC"))
        if hasattr(self, "pushButton_CCCECC"):
            self.pushButton_CCCECC.clicked.connect(lambda: self.set_mode("CC-CE-CC"))

        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

    # ---------------- controls ----------------

    def set_mode(self, mode):
        mode = str(mode).upper().replace(" ", "")
        if mode in ["CE-CC", "CECC"]:
            self.mode = "CE-CC"
        elif mode in ["CC-CE-CC", "CCCECC"]:
            self.mode = "CC-CE-CC"
        else:
            self.mode = "CC-CE"

        self._sync_buttons()
        self._update_mode_text()
        self.calculate()

    def clear_fields(self):
        self._clearing = True
        for edit in self.findChildren(QLineEdit):
            edit.clear()
        self._clearing = False

        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- calculation ----------------

    def calculate(self):
        if self._clearing:
            return

        try:
            if self.mode == "CC-CE":
                self._calculate_input_buffer()
            elif self.mode == "CE-CC":
                self._calculate_output_buffer()
            else:
                self._calculate_combined_buffer()
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(str(e), "#f8d7da", "#721c24")
        except Exception as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")

    def _calculate_input_buffer(self):
        """
        CC -> CE input buffer.

        Required:
            Ri_CE, RE_CC, RB_CC, rpi_CC, beta

        Formula:
            RE_ac = RE_CC || Ri_CE
            Rxx_CC = rpi + (beta + 1)RE_ac
            Ri_new = RB_CC || Rxx_CC
        """
        Ri_CE = self._read_kohm("lineEditRi")
        RE = self._read_kohm("lineEditRe")
        RB = self._read_kohm("lineEditRb")
        rpi = self._read_kohm("lineEditRpi")
        beta = self._read_float("lineEditBeta")

        if None in (Ri_CE, RE, RB, rpi, beta):
            self._clear_outputs_only()
            self._set_mode("Enter Ri, RE, RB, rπ, β", "#e8eaf6", "#3d3d9e")
            return

        RE_ac = parallel(RE, Ri_CE)
        Rxx = rpi + (beta + 1) * RE_ac
        Ri_new = parallel(RB, Rxx)
        Av_CC = ((beta + 1) * RE_ac) / Rxx

        Av_CE = self._read_float("lineEditAv0")
        Rs = self._read_kohm("lineEditRs") or 0.0
        input_factor = Ri_new / (Rs + Ri_new) if Rs > 0 else 1.0
        Av_total = Av_CC * Av_CE * input_factor if Av_CE is not None else None

        self._set_res("labelOutputRiNew", Ri_new)
        self._set_label("labelOutputRoNew", "—")
        self._set_res("labelOutputIb", Rxx)          # your UI's Rxx output row
        self._set_res("labelOutputReAc", RE_ac)
        self._set_num("labelOutputAvCC", Av_CC)
        self._set_num("labelOutputAvTotal", Av_total)  # optional, if later added

        self._set_mode("CC-CE INPUT BUFFER ANALYZED", "#d4edda", "#155724")

    def _calculate_output_buffer(self):
        """
        CE -> CC output buffer.

        Required:
            ro_CE, RE_CC, RB_CC, rpi_CC, beta

        Formula:
            ro_new = RE_CC || ((rpi + (RB_CC || ro_CE)) / (beta + 1))
        """
        ro_CE = self._read_kohm("lineEditRo")
        RE = self._read_kohm("lineEditRe")
        RB = self._read_kohm("lineEditRb")
        rpi = self._read_kohm("lineEditRpi")
        beta = self._read_float("lineEditBeta")

        if None in (ro_CE, RE, RB, rpi, beta):
            self._clear_outputs_only()
            self._set_mode("Enter ro, RE, RB, rπ, β", "#e8eaf6", "#3d3d9e")
            return

        RL = self._read_kohm("lineEditRl")
        Ri_CE = self._read_kohm("lineEditRi")
        Rs = self._read_kohm("lineEditRs") or 0.0
        Av_CE = self._read_float("lineEditAv0")

        ro_new = self._cc_output_resistance(RE=RE, RB=RB, rpi=rpi, beta=beta, Rs_back=ro_CE)
        RE_ac = parallel(RE, RL) if RL is not None else RE
        Rxx = rpi + (beta + 1) * RE_ac
        Av_CC = ((beta + 1) * RE_ac) / Rxx

        if Av_CE is not None:
            input_factor = Ri_CE / (Rs + Ri_CE) if (Ri_CE is not None and Rs > 0) else 1.0
            Av_total = Av_CE * Av_CC * input_factor
        else:
            Av_total = None

        self._set_label("labelOutputRiNew", "—")
        self._set_res("labelOutputRoNew", ro_new)
        self._set_res("labelOutputIb", Rxx)          # your UI's Rxx output row
        self._set_res("labelOutputReAc", RE_ac)
        self._set_num("labelOutputAvCC", Av_CC)
        self._set_num("labelOutputAvTotal", Av_total)  # optional, if later added

        self._set_mode("CE-CC OUTPUT BUFFER ANALYZED", "#d4edda", "#155724")

    def _calculate_combined_buffer(self):
        """
        CC -> CE -> CC combined buffer analysis.

        Required:
            Ri_CE, ro_CE, Av0_CE, RE_CC, RB_CC, rpi_CC, beta, Rs, RL

        This solves questions like:
            existing CE stage has Ri, ro, Av0, then both input and output are buffered by CC stages.
        """
        Ri_CE = self._read_kohm("lineEditRi")
        ro_CE = self._read_kohm("lineEditRo")
        Av_CE = self._read_float("lineEditAv0")
        RL = self._read_kohm("lineEditRl")

        RE = self._read_kohm("lineEditRe")
        RB = self._read_kohm("lineEditRb")
        rpi = self._read_kohm("lineEditRpi")
        beta = self._read_float("lineEditBeta")
        Rs = self._read_kohm("lineEditRs")

        required = (Ri_CE, ro_CE, Av_CE, RL, RE, RB, rpi, beta, Rs)
        if any(v is None for v in required):
            self._clear_outputs_only()
            self._set_mode("Enter Ri, ro, Av0, RL, RE, RB, rπ, β, Rs", "#e8eaf6", "#3d3d9e")
            return

        # Input CC stage, loaded by the CE input resistance.
        RE_ac1 = parallel(RE, Ri_CE)
        Rxx1 = rpi + (beta + 1) * RE_ac1
        Ri_new = parallel(RB, Rxx1)
        Av_CC1 = ((beta + 1) * RE_ac1) / Rxx1

        # Output CC stage, driven by the CE output resistance and loaded by RL.
        ro_new = self._cc_output_resistance(RE=RE, RB=RB, rpi=rpi, beta=beta, Rs_back=ro_CE)
        RE_ac2 = parallel(RE, RL)
        Rxx2 = rpi + (beta + 1) * RE_ac2
        Ri_CC2 = parallel(RB, Rxx2)
        Av_CC2 = ((beta + 1) * RE_ac2) / Rxx2

        input_factor = Ri_new / (Rs + Ri_new) if Rs > 0 else 1.0
        ce_to_cc_factor = Ri_CC2 / (Ri_CC2 + ro_CE)

        AvT = input_factor * Av_CC1 * Av_CE * ce_to_cc_factor * Av_CC2

        self._set_res("labelOutputRiNew", Ri_new)
        self._set_res("labelOutputRoNew", ro_new)
        self._set_label("labelOutputIb", f"{fmt(Rxx1, 'Ω')} / {fmt(Rxx2, 'Ω')}")
        self._set_label("labelOutputReAc", f"{fmt(RE_ac1, 'Ω')} / {fmt(RE_ac2, 'Ω')}")
        self._set_num("labelOutputAvCC", AvT)
        self._set_num("labelOutputAvTotal", AvT)  # optional, if later added

        self._set_mode("CC-CE-CC BUFFER ANALYZED", "#d4edda", "#155724")

    # ---------------- formulas ----------------

    @staticmethod
    def _cc_output_resistance(*, RE, RB, rpi, beta, Rs_back):
        rs_parallel_rb = parallel(RB, Rs_back)
        return parallel(RE, (rpi + rs_parallel_rb) / (beta + 1))

    # ---------------- UI text ----------------

    def _sync_buttons(self):
        if hasattr(self, "pushButton_CCCE"):
            self.pushButton_CCCE.setChecked(self.mode == "CC-CE")
        if hasattr(self, "pushButton_CECC"):
            self.pushButton_CECC.setChecked(self.mode == "CE-CC")
        if hasattr(self, "pushButton_CCCECC"):
            self.pushButton_CCCECC.setChecked(self.mode == "CC-CE-CC")

    def _update_mode_text(self):
        self._set_label("labelRi", "Ri")
        self._set_label("labelInputResistor", "Input Resistance of CE Stage")
        self._set_label("labelRo", "Ro")
        self._set_label("labelInputResistor_2", "Output Resistance of CE Stage")
        self._set_label("labelBeta_3", "Av0")
        self._set_label("labelGain_3", "CE Stage Internal Gain")
        self._set_label("labelBeta_4", "RE")
        self._set_label("labelGain_4", "CC Emitter Resistor")
        self._set_label("labelBeta_2", "RB")
        self._set_label("labelGain_2", "CC Base Resistor")
        self._set_label("labelRpi", "rπ")
        self._set_label("labelRlInfo_2", "CC rπ")
        self._set_label("labelRsInfo", "Source Resistance")

        if self.mode == "CC-CE":
            self._set_label("labelOutput", "Input Buffer Solution (CC → CE)")
            self._set_label("labelIconRiNew", "Ri new")
            self._set_label("labelIconRoNew", "Ro new")
            self._set_label("labelIconIb", "Rxx CC")
            self._set_label("labelIconReAc", "RE AC")
            self._set_label("labelIconVc", "Av CC")
        elif self.mode == "CE-CC":
            self._set_label("labelOutput", "Output Buffer Solution (CE → CC)")
            self._set_label("labelIconRiNew", "Ri new")
            self._set_label("labelIconRoNew", "Ro new")
            self._set_label("labelIconIb", "Rxx CC")
            self._set_label("labelIconReAc", "RE AC")
            self._set_label("labelIconVc", "Av CC")
        else:
            self._set_label("labelOutput", "Combined Buffer Solution (CC → CE → CC)")
            self._set_label("labelIconRiNew", "Ri total")
            self._set_label("labelIconRoNew", "Ro total")
            self._set_label("labelIconIb", "Rxx1 / Rxx2")
            self._set_label("labelIconReAc", "REac1 / REac2")
            self._set_label("labelIconVc", "AvT total (maybe wrong)")

    def _set_mode(self, text, bg, fg):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)
            self.labelMode.setStyleSheet(
                f"border-radius:6px; font: 700 11pt 'Rockwell'; "
                f"padding: 4px 14px; background-color:{bg}; color:{fg};"
            )

    # ---------------- helpers ----------------

    def _read_float(self, name):
        w = getattr(self, name, None)
        if w is None:
            return None
        text = w.text().strip().replace(",", "")
        if text == "" or text.lower() == "optional":
            return None
        return float(text)

    def _read_kohm(self, name):
        value = self._read_float(name)
        return value * 1e3 if value is not None else None

    def _set_label(self, name, text):
        if hasattr(self, name):
            getattr(self, name).setText(str(text))

    def _set_num(self, name, value):
        self._set_label(name, "—" if value is None else f"{value:.4g}")

    def _set_res(self, name, value):
        self._set_label(name, fmt(value, "Ω") if value is not None else "—")

    def _clear_outputs_only(self):
        for name in [
            "labelOutputRiNew",
            "labelOutputRoNew",
            "labelOutputIb",      # Rxx row in your UI
            "labelOutputReAc",
            "labelOutputAvCC",
            "labelOutputAvTotal", # optional if you add it later
        ]:
            self._set_label(name, "—")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BufferAnalysisWidget()
    window.setWindowTitle("Multistage Buffer Analysis")
    window.show()
    sys.exit(app.exec())
