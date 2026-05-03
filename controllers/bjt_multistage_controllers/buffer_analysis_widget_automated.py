import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton
from PyQt6.uic import loadUi

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
        CC-CE    : CC added BEFORE CE  -> raises input resistance
        CE-CC    : CC added AFTER CE   -> lowers output resistance
        CC-CE-CC : CC on both sides of CE stage

    All resistances entered and stored in kΩ. Av0 and beta are unitless.

    Formulas (Lecture 08, KAU EE311):

        CC Ri  (Slide 5/31) : REL = RE // RL_cc
                               RXX = rpi + (beta+1)*REL
                               Ri  = RB // RXX

        CC ro  (Slide 7/32) : RSB = RB // Rs_driving
                               ro  = RE // ((rpi + RSB) / (beta+1))

        CC Av               : Av_CC = (beta+1)*REL / RXX

        3-stage Av0 (Slide 18 extended):
            k12  = Ri_CE  / (Ri_CE  + ro_CC1)
            k23  = Ri_CC3 / (Ri_CC3 + ro_CE)
            Av0  = Av_CC1 * k12 * Av_CE * k23 * Av_CC3
            AvT  = Av0 * (Ri / (Ri + Rs)) * (RL / (RL + ro))
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

    # -- setup ----------------------------------------------------------

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
        if hasattr(self, "pushButton_CCCECC"):
            return
        btn = QPushButton("CC-CE-CC", self)
        btn.setObjectName("pushButton_CCCECC")
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

    # -- controls -------------------------------------------------------

    def set_mode(self, mode):
        mode = str(mode).upper().replace(" ", "").replace("-", "")
        if mode == "CECC":
            self.mode = "CE-CC"
        elif mode == "CCCECC":
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

    # -- dispatcher -----------------------------------------------------

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

    # -- CC-CE : input buffer -------------------------------------------

    def _calculate_input_buffer(self):
        Ri_CE = self._read_k("lineEditRi")
        RE    = self._read_k("lineEditRe")
        RB    = self._read_k("lineEditRb")
        rpi   = self._read_k("lineEditRpi")
        beta  = self._read_f("lineEditBeta")

        if None in (Ri_CE, RE, RB, rpi, beta):
            self._clear_outputs_only()
            self._set_mode("Enter: Ri, RE, RB, rpi, beta", "#e8eaf6", "#3d3d9e")
            return

        Rs    = self._read_k("lineEditRs") or 0.0
        Av_CE = self._read_f("lineEditAv0")

        REL    = parallel(RE, Ri_CE)
        RXX    = rpi + (beta + 1) * REL
        Ri_new = parallel(RB, RXX)
        Av_CC  = (beta + 1) * REL / RXX

        RSB    = parallel(RB, Rs) if Rs > 0 else RB
        ro_CC  = parallel(RE, (rpi + RSB) / (beta + 1))
        k12    = Ri_CE / (Ri_CE + ro_CC)

        if Av_CE is not None:
            Av0 = Av_CC * k12 * Av_CE
            k1  = Ri_new / (Ri_new + Rs) if Rs > 0 else 1.0
            AvT = Av0 * k1
        else:
            Av0 = AvT = None

        self._set_res("labelOutputRiNew",   Ri_new)
        self._set_label("labelOutputRoNew", "unchanged")
        self._set_num("labelOutputK",      k12)
        self._set_num("labelOutputAv0",    Av0)
        self._set_num("labelOutputAvt", AvT)

        self._set_mode("CC-CE INPUT BUFFER", "#d4edda", "#155724")

    # -- CE-CC : output buffer ------------------------------------------

    def _calculate_output_buffer(self):
        ro_CE = self._read_k("lineEditRo")
        RE    = self._read_k("lineEditRe")
        RB    = self._read_k("lineEditRb")
        rpi   = self._read_k("lineEditRpi")
        beta  = self._read_f("lineEditBeta")

        if None in (ro_CE, RE, RB, rpi, beta):
            self._clear_outputs_only()
            self._set_mode("Enter: ro, RE, RB, rpi, beta", "#e8eaf6", "#3d3d9e")
            return

        RL    = self._read_k("lineEditRl")
        Ri_CE = self._read_k("lineEditRi")
        Rs    = self._read_k("lineEditRs") or 0.0
        Av_CE = self._read_f("lineEditAv0")

        RSB    = parallel(RB, ro_CE)
        REL    = parallel(RE, RL) if RL is not None else RE
        RXX    = rpi + (beta + 1) * REL
        Ri_CC  = parallel(RB, RXX)
        ro_new = parallel(RE, (rpi + RSB) / (beta + 1))
        Av_CC  = (beta + 1) * REL / RXX
        k23    = Ri_CC / (Ri_CC + ro_CE)

        if Av_CE is not None:
            Av0 = Av_CE * k23 * Av_CC
            k1  = Ri_CE / (Ri_CE + Rs) if (Ri_CE is not None and Rs > 0) else 1.0
            k3  = RL / (RL + ro_new) if RL is not None else 1.0
            AvT = Av0 * k1 * k3
        else:
            Av0 = AvT = None

        self._set_label("labelOutputRiNew", "unchanged")
        self._set_res("labelOutputRoNew",   ro_new)
        self._set_num("labelOutputK",      k23)
        self._set_num("labelOutputAv0",    Av0)
        self._set_num("labelOutputAvt", AvT)

        self._set_mode("CE-CC OUTPUT BUFFER", "#d4edda", "#155724")

    # -- CC-CE-CC : combined buffer -------------------------------------

    def _calculate_combined_buffer(self):
        Ri_CE = self._read_k("lineEditRi")
        ro_CE = self._read_k("lineEditRo")
        Av_CE = self._read_f("lineEditAv0")
        RL    = self._read_k("lineEditRl")
        RE    = self._read_k("lineEditRe")
        RB    = self._read_k("lineEditRb")
        rpi   = self._read_k("lineEditRpi")
        beta  = self._read_f("lineEditBeta")
        Rs    = self._read_k("lineEditRs")

        if any(v is None for v in (Ri_CE, ro_CE, Av_CE, RL, RE, RB, rpi, beta, Rs)):
            self._clear_outputs_only()
            self._set_mode("Enter: Ri, ro, Av0, RL, RE, RB, rpi, beta, Rs", "#e8eaf6", "#3d3d9e")
            return

        # Stage 1 CC: input buffer
        REL1   = parallel(RE, Ri_CE)
        RXX1   = rpi + (beta + 1) * REL1
        Ri_new = parallel(RB, RXX1)
        Av_CC1 = (beta + 1) * REL1 / RXX1
        RSB1   = parallel(RB, Rs)
        ro_CC1 = parallel(RE, (rpi + RSB1) / (beta + 1))

        # Stage 3 CC: output buffer
        REL3   = parallel(RE, RL)
        RXX3   = rpi + (beta + 1) * REL3
        Ri_CC3 = parallel(RB, RXX3)
        Av_CC3 = (beta + 1) * REL3 / RXX3
        RSB3   = parallel(RB, ro_CE)
        ro_new = parallel(RE, (rpi + RSB3) / (beta + 1))

        # Interstage factors (Slide 18)
        k12 = Ri_CE  / (Ri_CE  + ro_CC1)
        k23 = Ri_CC3 / (Ri_CC3 + ro_CE)

        # Overall gain
        Av0 = Av_CC1 * k12 * Av_CE * k23 * Av_CC3
        k1  = Ri_new / (Ri_new + Rs)
        k3  = RL / (RL + ro_new)
        AvT = Av0 * k1 * k3

        self._set_res("labelOutputRiNew",   Ri_new)
        self._set_res("labelOutputRoNew",   ro_new)
        self._set_label("labelOutputK",    f"{k12:.4g} / {k23:.4g}")
        self._set_num("labelOutputAv0",    Av0)
        self._set_num("labelOutputAvt", AvT)

        self._set_mode("CC-CE-CC BUFFER", "#d4edda", "#155724")

    # -- UI labels ------------------------------------------------------

    def _sync_buttons(self):
        if hasattr(self, "pushButton_CCCE"):
            self.pushButton_CCCE.setChecked(self.mode == "CC-CE")
        if hasattr(self, "pushButton_CECC"):
            self.pushButton_CECC.setChecked(self.mode == "CE-CC")
        if hasattr(self, "pushButton_CCCECC"):
            self.pushButton_CCCECC.setChecked(self.mode == "CC-CE-CC")

    def _update_mode_text(self):
        # self._set_label("labelRi",              "Ri")
        # self._set_label("labelInputResistor",   "Input Resistance of CE Stage")
        # self._set_label("labelRo",              "Ro")
        # self._set_label("labelInputResistor_2", "Output Resistance of CE Stage")
        # self._set_label("labelBeta_3",          "Av0")
        # # self._set_label("labelInternalGain",          "CE Stage Internal Gain")
        # self._set_label("labelBeta_4",          "RE")
        # self._set_label("labelGain_4",          "CC Emitter Resistor")
        # self._set_label("labelBeta_2",          "RB")
        # self._set_label("labelGain_2",          "CC Base Resistor")
        # self._set_label("labelRpi",             "rpi")
        # self._set_label("labelRlInfo_2",        "CC rpi")
        # self._set_label("labelRsInfo",          "Source Resistance")

        if self.mode == "CC-CE":
            self._set_label("labelOutput",    "Input Buffer  (CC to CE)")
            self._set_label("labelIconRiNew", "Ri new")
            self._set_label("labelIconRoNew", "ro")
            self._set_label("labelIconK",    "k12")
            self._set_label("labelIconAv0",    "Av0")
            self._set_label("labelIconAvt",  "AvT")
        elif self.mode == "CE-CC":
            self._set_label("labelOutput",    "Output Buffer  (CE to CC)")
            self._set_label("labelIconRiNew", "Ri")
            self._set_label("labelIconRoNew", "ro new")
            self._set_label("labelIconK",    "k23")
            self._set_label("labelIconAv0",    "Av0")
            self._set_label("labelIconAvt",  "AvT")
        else:
            self._set_label("labelOutput",    "Combined Buffer  (CC to CE to CC)")
            self._set_label("labelIconRiNew", "Ri new")
            self._set_label("labelIconRoNew", "ro new")
            self._set_label("labelIconK",    "k12 / k23")
            self._set_label("labelIconAv0",    "Av0")
            self._set_label("labelIconAvt",  "AvT")

    def _set_mode(self, text, bg, fg):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)
            self.labelMode.setStyleSheet(
                f"border-radius:6px; font: 700 11pt 'Rockwell'; "
                f"padding: 4px 14px; background-color:{bg}; color:{fg};"
            )

    # -- read / write helpers -------------------------------------------

    def _read_f(self, name) -> float | None:
        w = getattr(self, name, None)
        if w is None:
            return None
        text = w.text().strip().replace(",", "")
        if not text or text.lower() == "optional":
            return None
        try:
            return float(text)
        except ValueError:
            return None

    def _read_k(self, name) -> float | None:
        return self._read_f(name)

    def _set_label(self, name, text):
        if hasattr(self, name):
            getattr(self, name).setText(str(text))

    def _set_num(self, name, value):
        self._set_label(name, "—" if value is None else f"{value:.4g}")

    def _set_res(self, name, value_k):
        self._set_label(name, fmt(value_k, "kΩ") if value_k is not None else "—")

    def _clear_outputs_only(self):
        for name in [
            "labelOutputRiNew",
            "labelOutputRoNew",
            "labelOutputK",
            "labelOutputAv0",
            "labelOutputAvt",
        ]:
            self._set_label(name, "—")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BufferAnalysisWidget()
    window.setWindowTitle("Multistage Buffer Analysis")
    window.show()
    sys.exit(app.exec())