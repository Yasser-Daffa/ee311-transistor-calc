import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit, QPushButton
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# controllers/bjt_multistage_controllers/cc_ce_design_widget.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from core.core_helpers import fmt, positive_validator, signed_validator
from core.bjt_amplifiers import design_ce_from_specs, design_cc_from_specs, parallel

UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design_cc_ce.ui")
IMAGE_PATH = os.path.join(PROJECT_ROOT, "assets", "images", "cc_ce_amp.png")


class CCCEDesignWidget(QWidget):
    """
    CC-CE multistage design controller.

    Stage 1 = CC input buffer
    Stage 2 = CE gain stage

    UI units:
        Vcc      V
        Icmax    mA
        beta     unitless
        Ri       kΩ  (minimum required total input resistance)
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
        self._set_label("labelCircuitTitle", "CC-CE Multistage Amplifier")
        self._set_label("labelOutput", "Stage 2 Bias: CE")
        self._set_label("labelOutput_2", "Total Output (CC-CE)")
        self._set_label("labelStage1Output", "STAGE 1 OUTPUT: CC")
        self._set_label("labelStage2Output", "STAGE 2 OUTPUT: CE")

        # Input row names.
        self._set_label("labelVsInfo", "Source Signal Voltage")
        self._set_label("labelVsUnit", "V")

        # AC output symbols.
        self._set_label("labelIconRx1", "R<sub>E(ac)1</sub>")
        self._set_label("labelIconRxx1", "R<sub>XX1</sub>")
        self._set_label("labelIconRx_2", "R<sub>X2</sub>")
        self._set_label("labelIconRxx_2", "R<sub>XX2</sub>")

        # DC output symbols. These names exist in your CC-CE UI.
        self._set_label("labelIconRb1", "R<sub>B1</sub>")
        self._set_label("labelIconRe2_2", "R<sub>E1</sub>")
        self._set_label("labelIconVc1", "V<sub>C1</sub>")
        self._set_label("labelIconVb1", "V<sub>B1</sub>")

        self._set_label("labelIconVbb_2", "V<sub>BB2</sub>")
        self._set_label("labelIconRb_2", "R<sub>B2</sub>")
        self._set_label("labelIconIb", "I<sub>B2</sub>")
        self._set_label("labelIconRpi", "rπ<sub>2</sub>")
        self._set_label("labelIconVc2", "V<sub>C2</sub>")
        self._set_label("labelIconVb2", "V<sub>B2</sub>")
        self._set_label("labelIconRc", "R<sub>C2</sub>")
        self._set_label("labelIconRe2", "R<sub>E2</sub>")
        self._set_label("labelIconVc_2", "R<sub>1</sub>")
        self._set_label("labelIconVb", "R<sub>2</sub>")

        self._sync_target_buttons()
        self._update_target_labels()
        self._set_image()

    def _setup_validators(self):
        if hasattr(self, "lineEditVcc"):
            self.lineEditVcc.setValidator(signed_validator(self))

        for name in [
            "lineEditIcmax", "lineEditBeta", "lineEditRi", "lineEditAv0",
            "lineEditRs", "lineEditRl", "lineEditVs",
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
            cc_bias = design_cc_from_specs(Vcc=vcc, Icmax_mA=icmax, beta=beta)
            ce_bias = design_ce_from_specs(Vcc=vcc, Icmax_mA=icmax, beta=beta)
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        # Bias should appear immediately after only Vcc, Icmax, beta.
        self._push_bias_outputs(cc_bias, ce_bias, vcc, icmax, beta)
        self._push_ce_limits(ce_bias, beta)

        target_ri_k = self._read_float("lineEditRi")
        target_gain = self._read_float("lineEditAv0")

        if target_ri_k is None or target_gain is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("Enter target Ri and gain", "#e8eaf6", "#3d3d9e")
            return

        rs = (self._read_float("lineEditRs") or 0.0) * 1e3
        rl_k = self._read_float("lineEditRl")
        vs = self._read_float("lineEditVs")
        rl = rl_k * 1e3 if rl_k is not None else None

        if self.target_mode == "AvT" and rl is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("RL is required for AvT", "#fff3cd", "#856404")
            return

        result, possible, warning = self._solve_cc_ce(
            cc_bias=cc_bias,
            ce_bias=ce_bias,
            beta=beta,
            target_ri=target_ri_k * 1e3,
            target_gain=abs(target_gain),
            mode=self.target_mode,
            Rs=rs,
            RL=rl,
            Vs=vs,
        )

        self._push_cc_ce_outputs(result)

        if possible:
            self._set_mode("Possible", "#d4edda", "#155724")
        else:
            self._set_mode(warning or "Impossible", "#fff3cd", "#856404")

    def _solve_cc_ce(self, *, cc_bias, ce_bias, beta, target_ri, target_gain, mode, Rs, RL, Vs):
        """CC-CE design. Keeps showing nearest usable values even when target is impossible."""
        Rc = ce_bias["Rc"]
        Re = ce_bias["Re"]
        Rb = ce_bias["Rb"]
        rpi = ce_bias["rpi"]

        warnings = []
        possible = True

        if mode == "Av0":
            # Worksheet/slides style: Av0 target is assigned to the CE gain stage.
            try:
                Rx2_raw = self._rx_from_av(target_gain, Rc, rpi, beta)
            except ValueError as e:
                possible = False
                warnings.append(str(e))
                Rx2_raw = 0.0
        else:
            # AvT is a true total gain target, so solve numerically.
            def avt_for_rx2(rx2):
                st2_local = self._ce_stage(rx2, Rc, Rb, rpi, beta)
                st1_local = self._cc_stage(cc_bias, st2_local["Ri"], Rs, beta)
                f12 = st2_local["Ri"] / (st2_local["Ri"] + (st1_local["ro"] or 0.0))
                av0_total_local = st1_local["Av"] * f12 * st2_local["Av"]
                input_factor_local = st1_local["Ri"] / (Rs + st1_local["Ri"]) if Rs > 0 else 1.0
                output_factor_local = RL / (RL + st2_local["ro"])
                return av0_total_local * input_factor_local * output_factor_local

            av_at_min = avt_for_rx2(0.0)
            av_at_max = avt_for_rx2(Re)
            lo_gain = min(av_at_min, av_at_max)
            hi_gain = max(av_at_min, av_at_max)

            if target_gain > hi_gain:
                possible = False
                warnings.append(f"Gain too high. Max AvT is {hi_gain:.4g}.")
                Rx2_raw = 0.0
            elif target_gain < lo_gain:
                possible = False
                warnings.append(f"Gain too low. Min AvT is {lo_gain:.4g}.")
                Rx2_raw = Re
            else:
                Rx2_raw = self._bisect_decreasing(avt_for_rx2, 0.0, Re, target_gain)

        if Rx2_raw < 0 or Rx2_raw > Re:
            possible = False
            warnings.append("Rx2 is outside 0 ≤ Rx2 ≤ Re.")

        Rx2 = self._clip(Rx2_raw, 0.0, Re)
        st2 = self._ce_stage(Rx2, Rc, Rb, rpi, beta)
        st1 = self._cc_stage(cc_bias, st2["Ri"], Rs, beta)

        f12 = st2["Ri"] / (st2["Ri"] + (st1["ro"] or 0.0))
        av0_total = st1["Av"] * f12 * st2["Av"]
        input_factor = st1["Ri"] / (Rs + st1["Ri"]) if Rs > 0 else 1.0
        output_factor = RL / (RL + st2["ro"]) if RL is not None else None
        avt_total = av0_total * input_factor * output_factor if output_factor is not None else None
        vo_total = avt_total * Vs if (Vs is not None and avt_total is not None) else None

        if st1["Ri"] < target_ri:
            possible = False
            warnings.append(f"Ri_total is {fmt(st1['Ri'], 'Ω')}, below target {fmt(target_ri, 'Ω')}.")

        return {
            "st1": st1,
            "st2": st2,
            "Rx2_raw": Rx2_raw,
            "Ri_total": st1["Ri"],
            "Av0_total": av0_total,
            "AvT_total": avt_total,
            "ro_total": st2["ro"],
            "Vo_total": vo_total,
            "interstage": f12,
            "input_factor": input_factor,
            "output_factor": output_factor,
        }, possible, " | ".join(dict.fromkeys(warnings))

    # ---------------- output push ----------------

    def _push_bias_outputs(self, cc, ce, vcc, icmax_mA, beta):
        Ic = icmax_mA * 1e-3
        Ib = Ic / beta
        Vc2 = vcc - Ic * ce["Rc"]

        # Stage 1 Bias: CC
        self._set_res("labelOutputRb1", cc.get("Rb"))
        self._set_res("labelOutputRe1", cc.get("Re"))
        self._set_volt("labelOutputVc1", vcc)
        self._set_volt("labelOutputVb1", cc.get("Vb"))

        # Stage 2 Bias: CE
        self._set_volt("labelOutputVbb", ce.get("Vbb"))
        self._set_res("labelOutputRb", ce.get("Rb"))
        self._set_current("labelOutputIb", Ib)
        self._set_res("labelOutputRpi", ce.get("rpi"))
        self._set_volt("labelOutputVc2", Vc2)
        self._set_volt("labelOutputVb2", ce.get("Vb"))
        self._set_res("labelOutputRc", ce.get("Rc"))
        self._set_res("labelOutputRe2", ce.get("Re"))
        self._set_res("labelOutputR1", ce.get("R1"))
        self._set_res("labelOutputR2", ce.get("R2"))

    def _push_cc_ce_outputs(self, r):
        st1 = r["st1"]
        st2 = r["st2"]

        # Stage 1: CC
        self._set_res("labelOutputRx1", st1["Re_ac"])
        self._set_res("labelOutputRxx1", st1["Rxx"])
        self._set_res("labelOutputRi1", st1["Ri"])
        self._set_res("labelOutputRo1", st1["ro"])
        self._set_num("labelOutputAvo", st1["Av"])

        # Stage 2: CE
        self._set_res("labelOutputRx_2", r["Rx2_raw"])
        self._set_res("labelOutputRxx2", st2["Rxx"])
        self._set_res("labelOutputRi_2", st2["Ri"])
        self._set_res("labelOutputRo_2", st2["ro"])
        self._set_num("labelOutputAvo_2", st2["Av"])

        # Totals
        self._set_res("labelOutputRiTotal", r["Ri_total"])
        self._set_num("labelOutputAv0Total", r["Av0_total"])
        self._set_num("labelOutputAvtTotal", r["AvT_total"])
        self._set_res("labelOutputRoTotal", r["ro_total"])
        self._set_volt("labelOutputVoTotal", r["Vo_total"])

    def _push_ce_limits(self, ce, beta):
        Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]
        av_min = beta * Rc / (rpi + (beta + 1) * Re)
        av_max = beta * Rc / rpi
        ri_min = parallel(Rb, rpi)
        ri_max = parallel(Rb, rpi + (beta + 1) * Re)

        # Stage 1 CC limits are load-dependent, so show actual values later.
        self._set_label("labelAvoMin", "—")
        self._set_label("labelAvoMax", "—")
        self._set_label("labelRiMin", "—")
        self._set_label("labelRiMax", "—")

        # Stage 2 CE limits.
        self._set_num("labelAvoMin_2", max(1.0, av_min))
        self._set_num("labelAvoMax_2", av_max)
        self._set_res("labelRiMin_2", ri_min)
        self._set_res("labelRiMax_2", ri_max)

    def _clear_outputs_only(self):
        for name in [
            # Stage 1 bias
            "labelOutputRb1", "labelOutputRe1", "labelOutputVc1", "labelOutputVb1",
            # Stage 2 bias
            "labelOutputVbb", "labelOutputRb", "labelOutputIb", "labelOutputRpi",
            "labelOutputVc2", "labelOutputVb2", "labelOutputRc", "labelOutputRe2",
            "labelOutputR1", "labelOutputR2",
            # Stage 1 AC
            "labelOutputRx1", "labelOutputRxx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo",
            # Stage 2 AC
            "labelOutputRx_2", "labelOutputRxx2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2",
            # Totals
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal", "labelOutputRoTotal", "labelOutputVoTotal",
            # Limits
            "labelAvoMin", "labelAvoMax", "labelRiMin", "labelRiMax",
            "labelAvoMin_2", "labelAvoMax_2", "labelRiMin_2", "labelRiMax_2",
        ]:
            self._set_label(name, "—")

    def _clear_stage_and_total_outputs(self):
        for name in [
            "labelOutputRx1", "labelOutputRxx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo",
            "labelOutputRx_2", "labelOutputRxx2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal", "labelOutputRoTotal", "labelOutputVoTotal",
        ]:
            self._set_label(name, "—")

    # ---------------- math helpers ----------------

    @staticmethod
    def _rx_from_av(target_av, Rc, rpi, beta):
        if target_av <= 0:
            raise ValueError("Gain target must be positive.")
        Rxx = beta * Rc / target_av
        return (Rxx - rpi) / (beta + 1)

    @staticmethod
    def _ce_stage(Rx, Rc, Rb, rpi, beta):
        Rxx = rpi + (beta + 1) * Rx
        Ri = parallel(Rb, Rxx)
        Av = beta * Rc / Rxx
        return {"Rx": Rx, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": Rc}

    @staticmethod
    def _cc_stage(cc_bias, RL, Rs, beta):
        Re = cc_bias["Re"]
        Rb = cc_bias["Rb"]
        rpi = cc_bias["rpi"]
        Re_ac = parallel(Re, RL) if RL is not None else Re
        Rxx = rpi + (beta + 1) * Re_ac
        Ri = parallel(Rb, Rxx)
        Av = ((beta + 1) * Re_ac) / Rxx

        Rs_parallel_Rb = 0.0 if Rs == 0 else parallel(Rs, Rb)
        ro = parallel(Re, (rpi + Rs_parallel_Rb) / (beta + 1))

        return {"Re_ac": Re_ac, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": ro}

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
    window = CCCEDesignWidget()
    window.setWindowTitle("CC-CE Multistage Design")
    window.show()
    sys.exit(app.exec())
