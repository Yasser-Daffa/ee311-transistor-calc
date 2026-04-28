import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# controllers/bjt_multistage_controllers/ce_ce_design_widget.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from core.core_helpers import fmt, positive_validator, signed_validator
from core.bjt_amplifiers import design_ce_from_specs, parallel

UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design.ui")
IMAGE_PATH = os.path.join(PROJECT_ROOT, "assets", "images", "ce_ce_amp.png")


class CECEDesignWidget(QWidget):
    """
    CE-CE multistage design controller only.

    UI units:
        Vcc      V
        Icmax    mA
        beta     unitless
        Ri       kΩ
        Av0/AvT  unitless
        Rs, RL   kΩ
        Vs       V

    Core units:
        resistances in Ω, current in A except Icmax_mA.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        self.target_mode = "Av0"
        self._clearing = False

        self._setup_ui()
        self._setup_validators()
        self._setup_connections()
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- setup ----------------

    def _setup_ui(self):
        self._set_label("labelCircuitTitle", "CE-CE Multistage Amplifier")
        self._set_label("labelOutput", "DC OUTPUT")
        self._set_label("labelOutput_2", "Total Output (CE-CE)")
        self._set_label("labelInput_2", "STAGE 1 OUTPUT: CE")
        self._set_label("labelInput_3", "STAGE 2 OUTPUT: CE")
        self._set_label("labelRlInfo_2", "Source Signal Voltage")
        self._set_label("labelRlUnit_2", "V")
        self._set_label("labelIconRx1", "R<sub>X1</sub>")
        self._set_label("labelIconRx_2", "R<sub>X2</sub>")
        self._sync_target_buttons()
        self._update_target_labels()
        self._set_image()

    def _setup_validators(self):
        if hasattr(self, "lineEditVcc"):
            self.lineEditVcc.setValidator(signed_validator(self))

        for name in [
            "lineEditIcmax", "lineEditBeta", "lineEditRi", "lineEditAv0",
            "lineEditRs", "lineEditRl", "lineEditRl_2",
        ]:
            if hasattr(self, name):
                getattr(self, name).setValidator(positive_validator(self))

    def _setup_connections(self):
        for edit in self.findChildren(QLineEdit):
            edit.textChanged.connect(self.calculate)

        if hasattr(self, "pushButtonModeAv0"):
            self.pushButtonModeAv0.setCheckable(True)
            self.pushButtonModeAv0.setAutoExclusive(False)
            self.pushButtonModeAv0.clicked.connect(lambda: self.set_target_mode("Av0"))

        if hasattr(self, "pushButtonModeAvt"):
            self.pushButtonModeAvt.setCheckable(True)
            self.pushButtonModeAvt.setAutoExclusive(False)
            self.pushButtonModeAvt.clicked.connect(lambda: self.set_target_mode("AvT"))

        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

    # ---------------- controls ----------------

    def set_target_mode(self, mode):
        self.target_mode = "AvT" if str(mode).lower() == "avt" else "Av0"
        self._sync_target_buttons()
        self._update_target_labels()
        self.calculate()

    def clear_fields(self):
        self._clearing = True
        for edit in self.findChildren(QLineEdit):
            edit.clear()
        self._clearing = False

        self.target_mode = "Av0"
        self._sync_target_buttons()
        self._update_target_labels()
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- calculation ----------------

    def calculate(self):
        if self._clearing:
            return

        vcc = self._read_float("lineEditVcc")
        icmax = self._read_float("lineEditIcmax")
        beta = self._read_float("lineEditBeta")

        if None in (vcc, icmax, beta):
            self._clear_outputs_only()
            self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
            return

        try:
            bias = design_ce_from_specs(Vcc=vcc, Icmax_mA=icmax, beta=beta)
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        # Bias and limits should appear as soon as Vcc, Icmax, beta are entered.
        self._push_bias_outputs(bias, vcc, icmax, beta)
        self._push_ce_limits(bias, beta, stage=1)
        self._push_ce_limits(bias, beta, stage=2)

        target_ri_k = self._read_float("lineEditRi")
        target_gain = self._read_float("lineEditAv0")

        if target_ri_k is None or target_gain is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("Enter target Ri and gain", "#e8eaf6", "#3d3d9e")
            return

        rs = (self._read_float("lineEditRs") or 0.0) * 1e3
        rl_k = self._read_float("lineEditRl")
        vs = self._read_float("lineEditRl_2")
        rl = rl_k * 1e3 if rl_k is not None else None

        if self.target_mode == "AvT" and rl is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("RL is required for AvT", "#fff3cd", "#856404")
            return

        result, possible, warning = self._solve_ce_ce(
            bias=bias,
            beta=beta,
            target_ri=target_ri_k * 1e3,
            target_gain=abs(target_gain),
            mode=self.target_mode,
            Rs=rs,
            RL=rl,
            Vs=vs,
        )

        self._push_ce_ce_outputs(result)

        if possible:
            self._set_mode("Possible", "#d4edda", "#155724")
        else:
            self._set_mode(warning or "Impossible", "#fff3cd", "#856404")

    def _solve_ce_ce(self, *, bias, beta, target_ri, target_gain, mode, Rs, RL, Vs):
        """CE-CE design. Keeps showing nearest usable values even when target is impossible."""
        Rc = bias["Rc"]
        Re = bias["Re"]
        Rb = bias["Rb"]
        rpi = bias["rpi"]

        warnings = []
        possible = True

        # Stage 1: design from Ri target.
        try:
            Rx1_raw = self._rx_from_ri(target_ri, Rb, rpi, beta)
        except ValueError as e:
            possible = False
            warnings.append(str(e))
            Rx1_raw = Re if target_ri >= Rb else 0.0

        if Rx1_raw < 0 or Rx1_raw > Re:
            possible = False
            warnings.append("Rx1 is outside 0 ≤ Rx1 ≤ Re.")

        Rx1 = self._clip(Rx1_raw, 0.0, Re)
        st1 = self._ce_stage(Rx1, Rc, Rb, rpi, beta)

        input_factor = st1["Ri"] / (Rs + st1["Ri"]) if Rs > 0 else 1.0
        output_factor = RL / (RL + Rc) if RL is not None else None

        if mode == "AvT":
            target_av0 = target_gain / (input_factor * output_factor)
        else:
            target_av0 = target_gain

        def av0_total_for_rx2(rx2):
            st2_local = self._ce_stage(rx2, Rc, Rb, rpi, beta)
            interstage_local = st2_local["Ri"] / (st2_local["Ri"] + st1["ro"])
            return st1["Av"] * interstage_local * st2_local["Av"]

        av_at_min = av0_total_for_rx2(0.0)
        av_at_max = av0_total_for_rx2(Re)
        lo_gain = min(av_at_min, av_at_max)
        hi_gain = max(av_at_min, av_at_max)

        if target_av0 > hi_gain:
            possible = False
            warnings.append(f"Gain too high. Max Av0 is {hi_gain:.4g}.")
            Rx2 = 0.0
        elif target_av0 < lo_gain:
            possible = False
            warnings.append(f"Gain too low. Min Av0 is {lo_gain:.4g}.")
            Rx2 = Re
        else:
            Rx2 = self._bisect_decreasing(av0_total_for_rx2, 0.0, Re, target_av0)

        st2 = self._ce_stage(Rx2, Rc, Rb, rpi, beta)
        interstage = st2["Ri"] / (st2["Ri"] + st1["ro"])
        av0_total = st1["Av"] * interstage * st2["Av"]
        avt_total = av0_total * input_factor * output_factor if RL is not None else None
        vo_total = avt_total * Vs if (Vs is not None and avt_total is not None) else None

        return {
            "st1": st1,
            "st2": st2,
            "Rx1_raw": Rx1_raw,
            "Rx2_raw": Rx2,
            "Ri_total": st1["Ri"],
            "Av0_total": av0_total,
            "AvT_total": avt_total,
            "ro_total": st2["ro"],
            "Vo_total": vo_total,
            "interstage": interstage,
            "input_factor": input_factor,
            "output_factor": output_factor,
        }, possible, " | ".join(dict.fromkeys(warnings))

    # ---------------- output push ----------------

    def _push_bias_outputs(self, b, vcc, icmax_mA, beta):
        Ic = icmax_mA * 1e-3
        Ib = Ic / beta
        Vc = vcc - Ic * b["Rc"]

        self._set_volt("labelOutputVbb", b.get("Vbb"))
        self._set_res("labelOutputRb", b.get("Rb"))
        self._set_current("labelOutputIb", Ib)
        self._set_res("labelOutputRpi", b.get("rpi"))
        self._set_volt("labelOutputVc", Vc)
        self._set_volt("labelOutputVb", b.get("Vb"))

        # Optional extra labels if you add them in Designer later.
        self._set_res("labelOutputRc", b.get("Rc"))
        self._set_res("labelOutputRe", b.get("Re"))
        self._set_res("labelOutputR1", b.get("R1"))
        self._set_res("labelOutputR2", b.get("R2"))

    def _push_ce_ce_outputs(self, r):
        st1 = r["st1"]
        st2 = r["st2"]

        self._set_res("labelOutputRx1", r["Rx1_raw"])
        self._set_res("labelOutputRxx1", st1.get("Rxx"))
        self._set_res("labelOutputRi1", st1["Ri"])
        self._set_res("labelOutputRo1", st1["ro"])
        self._set_num("labelOutputAvo", st1["Av"])
        self._set_label("labelOutputAvt", "—")

        self._set_res("labelOutputRx_2", r["Rx2_raw"])
        self._set_res("labelOutputRxx2", st2.get("Rxx"))
        self._set_res("labelOutputRi_2", st2["Ri"])
        self._set_res("labelOutputRo_2", st2["ro"])
        self._set_num("labelOutputAvo_2", st2["Av"])
        self._set_label("labelOutputAvt_2", "—")

        self._set_res("labelOutputRiTotal", r["Ri_total"])
        self._set_num("labelOutputAv0Total", r["Av0_total"])
        self._set_num("labelOutputAvtTotal", r["AvT_total"])
        self._set_res("labelOutputRoTotal", r["ro_total"])
        self._set_volt("labelOutputVoTotal", r["Vo_total"])

    def _push_ce_limits(self, b, beta, stage):
        Rc, Re, Rb, rpi = b["Rc"], b["Re"], b["Rb"], b["rpi"]
        av_min = beta * Rc / (rpi + (beta + 1) * Re)
        av_max = beta * Rc / rpi
        ri_min = parallel(Rb, rpi)
        ri_max = parallel(Rb, rpi + (beta + 1) * Re)

        suffix = "" if stage == 1 else "_2"
        self._set_num(f"labelAvoMin{suffix}", max(1.0, av_min))
        self._set_num(f"labelAvoMax{suffix}", av_max)
        self._set_res(f"labelRiMin{suffix}", ri_min)
        self._set_res(f"labelRiMax{suffix}", ri_max)
        self._set_res(f"labelRxMin{suffix}", 0.0)
        self._set_res(f"labelRxMax{suffix}", Re)

    def _clear_outputs_only(self):
        for name in [
            "labelOutputVbb", "labelOutputRb", "labelOutputIb", "labelOutputRpi", "labelOutputVc", "labelOutputVb",
            "labelOutputRc", "labelOutputRe", "labelOutputR1", "labelOutputR2",
            "labelOutputRx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo", "labelOutputAvt",
            "labelOutputRx_2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2", "labelOutputAvt_2",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal", "labelOutputRoTotal", "labelOutputVoTotal",
            "labelAvoMin", "labelAvoMax", "labelRiMin", "labelRiMax", "labelRxMin", "labelRxMax",
            "labelAvoMin_2", "labelAvoMax_2", "labelRiMin_2", "labelRiMax_2", "labelRxMin_2", "labelRxMax_2",
        ]:
            self._set_label(name, "—")

    def _clear_stage_and_total_outputs(self):
        for name in [
            "labelOutputRx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo", "labelOutputAvt",
            "labelOutputRx_2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2", "labelOutputAvt_2",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal", "labelOutputRoTotal", "labelOutputVoTotal",
        ]:
            self._set_label(name, "—")

    # ---------------- math helpers ----------------

    @staticmethod
    def _rx_from_ri(target_ri, Rb, rpi, beta):
        if target_ri >= Rb:
            raise ValueError(f"Impossible Ri: target Ri must be less than Rb ({Rb:.4g} Ω).")
        Rxx = (target_ri * Rb) / (Rb - target_ri)
        return (Rxx - rpi) / (beta + 1)

    @staticmethod
    def _ce_stage(Rx, Rc, Rb, rpi, beta):
        Rxx = rpi + (beta + 1) * Rx
        Ri = parallel(Rb, Rxx)
        Av = beta * Rc / Rxx
        return {"Rx": Rx, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": Rc}

    @staticmethod
    def _bisect_decreasing(func, low, high, target):
        lo, hi = low, high
        for _ in range(100):
            mid = (lo + hi) / 2.0
            if func(mid) > target:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2.0

    @staticmethod
    def _clip(value, low, high):
        return max(low, min(value, high))

    # ---------------- UI helpers ----------------

    def _update_target_labels(self):
        if self.target_mode == "AvT":
            self._set_label("labelBeta_3", "AvT")
            self._set_label("labelGain_3", "Total Gain")
        else:
            self._set_label("labelBeta_3", "Av0")
            self._set_label("labelGain_3", "Internal Gain")

    def _sync_target_buttons(self):
        if hasattr(self, "pushButtonModeAv0"):
            self.pushButtonModeAv0.setChecked(self.target_mode == "Av0")
        if hasattr(self, "pushButtonModeAvt"):
            self.pushButtonModeAvt.setChecked(self.target_mode == "AvT")

    def _set_image(self):
        if hasattr(self, "labelCircuitImage") and os.path.exists(IMAGE_PATH):
            pix = QPixmap(IMAGE_PATH)
            self.labelCircuitImage.setPixmap(
                pix.scaled(self.labelCircuitImage.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            )

    def _set_mode(self, text, bg, fg):
        if hasattr(self, "labelMode"):
            self.labelMode.setText(text)
            self.labelMode.setStyleSheet(
                f"border-radius:6px; font: 700 11pt 'Rockwell'; "
                f"padding: 4px 14px; background-color:{bg}; color:{fg};"
            )

    def _read_float(self, name):
        w = getattr(self, name, None)
        if w is None:
            return None
        text = w.text().strip().replace(",", "")
        if text == "" or text.lower() == "optional":
            return None
        return float(text)

    def _set_label(self, name, text):
        if hasattr(self, name):
            getattr(self, name).setText(str(text))

    def _set_num(self, name, value):
        self._set_label(name, "—" if value is None else f"{value:.4g}")

    def _set_res(self, name, value):
        self._set_label(name, fmt(value, "Ω") if value is not None else "—")

    def _set_volt(self, name, value):
        self._set_label(name, fmt(value, "V") if value is not None else "—")

    def _set_current(self, name, value):
        self._set_label(name, fmt(value, "A", scale="µA") if value is not None else "—")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CECEDesignWidget()
    window.setWindowTitle("CE-CE Multistage Design")
    window.show()
    sys.exit(app.exec())
