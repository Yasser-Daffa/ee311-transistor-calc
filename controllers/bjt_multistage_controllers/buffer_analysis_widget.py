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
    Buffer analysis controller for multistage questions.

    Modes:
        CC-CE: input buffer problem
        CE-CC: output buffer problem

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
        # Start on CC-CE because that is usually the first buffer question.
        if hasattr(self, "pushButton_CCCE"):
            self.pushButton_CCCE.setCheckable(True)
            self.pushButton_CCCE.setChecked(True)
        if hasattr(self, "pushButton_CECC"):
            self.pushButton_CECC.setCheckable(True)
            self.pushButton_CECC.setChecked(False)

        self._update_mode_text()

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

        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

    # ---------------- controls ----------------

    def set_mode(self, mode):
        self.mode = "CE-CC" if str(mode).upper().replace(" ", "") == "CE-CC" else "CC-CE"

        if hasattr(self, "pushButton_CCCE"):
            self.pushButton_CCCE.setChecked(self.mode == "CC-CE")
        if hasattr(self, "pushButton_CECC"):
            self.pushButton_CECC.setChecked(self.mode == "CE-CC")

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
            else:
                self._calculate_output_buffer()
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

        Main formula:
            RE_ac = RE_CC || Ri_CE
            Rxx_CC = rpi + (beta + 1) RE_ac
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

        # Optional total gain estimate if Av0_CE and Rs are given.
        Av0_CE = self._read_float("lineEditAv0")
        Rs = self._read_kohm("lineEditRs") or 0.0
        input_factor = Ri_new / (Rs + Ri_new) if Rs > 0 else 1.0
        Av_total = Av_CC * Av0_CE * input_factor if Av0_CE is not None else None

        self._set_res("labelOutputRiNew", Ri_new)
        self._set_label("labelOutputRoNew", "—")
        self._set_res("labelOutputRxx", Rxx)
        self._set_res("labelOutputReAc", RE_ac)
        self._set_num("labelOutputAvCC", Av_CC)

        # If you later add this label in Designer, this line will fill it automatically.
        self._set_res("labelOutputRxx", Rxx)
        self._set_num("labelOutputAvTotal", Av_total)

        self._set_mode("CC-CE INPUT BUFFER ANALYZED", "#d4edda", "#155724")

    def _calculate_output_buffer(self):
        """
        CE -> CC output buffer.

        Required:
            ro_CE, RE_CC, RB_CC, rpi_CC, beta

        Optional:
            RL is used for RE_ac and Av_CC.
            Av0_CE and Rs are used for total gain estimate.

        Main formula:
            Rs_CC = ro_CE
            ro_new = RE_CC || ((rpi + (RB_CC || Rs_CC)) / (beta + 1))
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
        Av0_CE = self._read_float("lineEditAv0")

        Rs_CC = ro_CE
        Rs_parallel_RB = parallel(RB, Rs_CC)
        ro_new = parallel(RE, (rpi + Rs_parallel_RB) / (beta + 1))

        RE_ac = parallel(RE, RL) if RL is not None else RE
        Rxx = rpi + (beta + 1) * RE_ac
        Av_CC = ((beta + 1) * RE_ac) / Rxx

        # Optional total gain estimate.
        if Av0_CE is not None:
            input_factor = Ri_CE / (Rs + Ri_CE) if (Ri_CE is not None and Rs > 0) else 1.0
            output_factor = RL / (RL + ro_new) if RL is not None else 1.0
            Av_total = Av0_CE * Av_CC * input_factor * output_factor
        else:
            Av_total = None

        self._set_label("labelOutputRiNew", "—")
        self._set_res("labelOutputRoNew", ro_new)
        self._set_res("labelOutputRxx", Rxx)
        self._set_res("labelOutputReAc", RE_ac)
        self._set_num("labelOutputAvCC", Av_CC)

        # If you later add this label in Designer, this line will fill it automatically.
        self._set_res("labelOutputRxx", Rxx)
        self._set_num("labelOutputAvTotal", Av_total)

        self._set_mode("CE-CC OUTPUT BUFFER ANALYZED", "#d4edda", "#155724")

    # ---------------- UI text ----------------

    def _update_mode_text(self):
        if self.mode == "CC-CE":
            self._set_label("labelOutput", "Input Buffer Solution (CC → CE)")
            # self._set_label("labelRi", "Input Resistance of CE Stage")
            self._set_label("labelRo", "Output Resistance of CE Stage")
            self._set_label("labelAv0", "CE Stage Internal Gain")
        else:
            self._set_label("labelOutput", "Output Buffer Solution (CE → CC)")
            self._set_label("labelRi", "Input Resistance of CE Stage")
            self._set_label("labelRo", "Output Resistance of CE Stage")
            self._set_label("labelAv0", "CE Stage Internal Gain")

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
        if text == "":
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
            "labelOutputRxx",
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
