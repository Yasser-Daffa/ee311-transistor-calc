import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QLineEdit
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# controllers/bjt_multistage_controllers/ce_cc_design_widget.py

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from core.core_helpers import fmt, positive_validator, signed_validator
from core.bjt_amplifiers import design_ce_from_specs, design_cc_from_specs, parallel

UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design_ce_cc.ui")
IMAGE_PATH = os.path.join(PROJECT_ROOT, "assets", "images", "ce_cc_amp.png")


class CECCDesignWidget(QWidget):
    """
    CE-CC multistage design controller.

    Stage 1: CE gain stage
    Stage 2: CC output buffer

    UI units:
        Vcc      V
        Icmax    mA
        beta     unitless
        Av0/AvT  unitless
        Rs, RL   kΩ
        Vs       V
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
        self._set_label("labelCircuitTitle", "CE-CC Multistage Amplifier")
        self._set_label("labelOutput", "DC OUTPUT")
        self._set_label("labelOutput_2", "Total Output (CE-CC)")
        self._set_label("labelStage1Output", "STAGE 1 OUTPUT: CE")
        self._set_label("labelStage2Output", "STAGE 2 OUTPUT: CC")

        # Stage 1 CE AC labels
        self._set_label("labelIconRx1", "R<sub>X1</sub>")
        self._set_label("labelIconRxx1", "R<sub>XX1</sub>")

        # Stage 2 CC AC labels: Rx row is reused for Re(ac)
        self._set_label("labelIconRx_2", "R<sub>E(ac)2</sub>")
        self._set_label("labelIconRxx_2", "R<sub>XX2</sub>")

        # Optional input text
        self._set_label("labelVsInfo", "Source Signal Voltage")
        self._set_label("labelVsUnit", "V")

        # Make the copied DC labels stage-specific and less confusing.
        self._set_label("labelBjtHead_3", "Stage 1 Bias: CE")
        self._set_label("labelIconVbb", "V<sub>BB1</sub>")
        self._set_label("labelIconRb1", "R<sub>B1</sub>")
        self._set_label("labelIconIb", "I<sub>B1</sub>")
        self._set_label("labelIconRpi", "r<sub>π1</sub>")
        self._set_label("labelIconVc1_2", "V<sub>C1</sub>")
        self._set_label("labelIconVb1", "V<sub>B1</sub>")
        self._set_label("labelIconRc", "R<sub>C1</sub>")
        self._set_label("labelIconRe1", "R<sub>E1</sub>")
        self._set_label("labelIconVc_2", "R<sub>1</sub>")
        self._set_label("labelIconVb", "R<sub>2</sub>")

        self._set_label("labelIconRb2", "R<sub>B2</sub>")
        self._set_label("labelIconRe2", "R<sub>E2</sub>")
        self._set_label("labelIconVc2", "V<sub>C2</sub>")
        self._set_label("labelIconVb2", "V<sub>B2</sub>")

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
            ce_bias = design_ce_from_specs(Vcc=vcc, Icmax_mA=icmax, beta=beta)
            cc_bias = design_cc_from_specs(Vcc=vcc, Icmax_mA=icmax, beta=beta)
        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        # Bias and useful ranges appear after only Vcc, Icmax, beta.
        self._push_bias_outputs(ce_bias, cc_bias, vcc, icmax, beta)
        self._push_ce_limits(ce_bias, beta)
        self._push_cc_limits_unloaded(cc_bias, beta)

        target_gain = self._read_float("lineEditAv0")
        if target_gain is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("Enter gain target", "#e8eaf6", "#3d3d9e")
            return

        rs = (self._read_float("lineEditRs") or 0.0) * 1e3
        rl_k = self._read_float("lineEditRl")
        rl = rl_k * 1e3 if rl_k is not None else None
        vs = self._read_float("lineEditVs")

        if self.target_mode == "AvT" and rl is None:
            self._clear_stage_and_total_outputs()
            self._set_mode("RL is required for AvT", "#fff3cd", "#856404")
            return

        result, possible, warning = self._solve_ce_cc(
            ce_bias=ce_bias,
            cc_bias=cc_bias,
            beta=beta,
            target_gain=abs(target_gain),
            mode=self.target_mode,
            Rs=rs,
            RL=rl,
            Vs=vs,
        )

        self._push_ce_cc_outputs(result)

        if possible:
            self._set_mode("Possible", "#d4edda", "#155724")
        else:
            self._set_mode(warning or "Impossible", "#fff3cd", "#856404")

    def _solve_ce_cc(self, *, ce_bias, cc_bias, beta, target_gain, mode, Rs, RL, Vs):
        """CE-CC design. Keeps showing nearest usable values even when target is impossible."""
        Rc1 = ce_bias["Rc"]
        Re1 = ce_bias["Re"]
        Rb1 = ce_bias["Rb"]
        rpi1 = ce_bias["rpi"]

        warnings = []
        possible = True

        def build(rx1):
            st1 = self._ce_stage(rx1, Rc1, Rb1, rpi1, beta)

            # The CC input is driven by the CE output resistance.
            st2 = self._cc_stage(
                Re=cc_bias["Re"],
                Rb=cc_bias["Rb"],
                rpi=cc_bias["rpi"],
                beta=beta,
                RL=RL,
                Rs=st1["ro"],
            )

            interstage = st2["Ri"] / (st2["Ri"] + st1["ro"])
            av0_total = st1["Av"] * interstage * st2["Av"]
            input_factor = st1["Ri"] / (Rs + st1["Ri"]) if Rs > 0 else 1.0
            avt_total = av0_total * input_factor if RL is not None else None
            vo_total = avt_total * Vs if (Vs is not None and avt_total is not None) else None

            return st1, st2, interstage, av0_total, input_factor, avt_total, vo_total

        def target_func(rx):
            built = build(rx)
            return built[5] if mode == "AvT" else built[3]

        at_min = target_func(0.0)
        at_max = target_func(Re1)
        lo_gain = min(at_min, at_max)
        hi_gain = max(at_min, at_max)

        if target_gain > hi_gain:
            possible = False
            warnings.append(f"Gain too high. Max {mode} is {hi_gain:.4g}.")
            Rx1 = 0.0
        elif target_gain < lo_gain:
            possible = False
            warnings.append(f"Gain too low. Min {mode} is {lo_gain:.4g}.")
            Rx1 = Re1
        else:
            Rx1 = self._bisect_decreasing(target_func, 0.0, Re1, target_gain)

        st1, st2, interstage, av0_total, input_factor, avt_total, vo_total = build(Rx1)

        return {
            "st1": st1,
            "st2": st2,
            "Rx1_raw": Rx1,
            "Ri_total": st1["Ri"],
            "Av0_total": av0_total,
            "AvT_total": avt_total,
            "ro_total": st2["ro"],
            "Vo_total": vo_total,
            "interstage": interstage,
            "input_factor": input_factor,
        }, possible, " | ".join(dict.fromkeys(warnings))

    # ---------------- output push ----------------

    def _push_bias_outputs(self, ce, cc, vcc, icmax_mA, beta):
        Ic = icmax_mA * 1e-3
        Ib = Ic / beta
        Vc1 = vcc - Ic * ce["Rc"]
        Vc2 = vcc

        # Stage 1 CE bias
        self._set_volt("labelOutputVbb", ce.get("Vbb"))
        self._set_res("labelOutputRb1", ce.get("Rb"))
        self._set_current("labelOutputIb", Ib)
        self._set_res("labelOutputRpi", ce.get("rpi"))
        self._set_volt("labelOutputVc1", Vc1)
        self._set_volt("labelOutputVb1", ce.get("Vb"))
        self._set_res("labelOutputRc", ce.get("Rc"))
        self._set_res("labelOutputRe1", ce.get("Re"))
        self._set_res("labelOutputR1", ce.get("R1"))
        self._set_res("labelOutputR2", ce.get("R2"))

        # Stage 2 CC bias
        self._set_res("labelOutputRb2", cc.get("Rb"))
        self._set_res("labelOutputRe2", cc.get("Re"))
        self._set_volt("labelOutputVc2", Vc2)
        self._set_volt("labelOutputVb2", cc.get("Vb"))

    def _push_ce_cc_outputs(self, r):
        st1 = r["st1"]
        st2 = r["st2"]

        # Stage 1 CE outputs
        self._set_res("labelOutputRx1", r["Rx1_raw"])
        self._set_res("labelOutputRxx1", st1["Rxx"])
        self._set_res("labelOutputRi1", st1["Ri"])
        self._set_res("labelOutputRo1", st1["ro"])
        self._set_num("labelOutputAvo", st1["Av"])

        # Stage 2 CC outputs. Rx row is reused as RE(ac)2.
        self._set_res("labelOutputRx_2", st2["Re_ac"])
        self._set_res("labelOutputRxx2", st2["Rxx"])
        self._set_res("labelOutputRi_2", st2["Ri"])
        self._set_res("labelOutputRo_2", st2["ro"])
        self._set_num("labelOutputAvo_2", st2["Av"])

        # Total outputs
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

        self._set_num("labelAvoMin", max(1.0, av_min))
        self._set_num("labelAvoMax", av_max)
        self._set_res("labelRiMin", ri_min)
        self._set_res("labelRiMax", ri_max)

    def _push_cc_limits_unloaded(self, cc, beta):
        st = self._cc_stage(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=None, Rs=0.0)

        self._set_num("labelAvoMin_2", st["Av"])
        self._set_num("labelAvoMax_2", st["Av"])
        self._set_res("labelRiMin_2", parallel(cc["Rb"], cc["rpi"]))
        self._set_res("labelRiMax_2", st["Ri"])

    def _clear_outputs_only(self):
        for name in [
            "labelOutputVbb", "labelOutputRb1", "labelOutputIb", "labelOutputRpi", "labelOutputVc1", "labelOutputVb1",
            "labelOutputRc", "labelOutputRe1", "labelOutputR1", "labelOutputR2",
            "labelOutputRb2", "labelOutputRe2", "labelOutputVc2", "labelOutputVb2",
            "labelOutputRx1", "labelOutputRxx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo",
            "labelOutputRx_2", "labelOutputRxx2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal", "labelOutputRoTotal", "labelOutputVoTotal",
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
    def _ce_stage(Rx, Rc, Rb, rpi, beta):
        Rxx = rpi + (beta + 1) * Rx
        Ri = parallel(Rb, Rxx)
        Av = beta * Rc / Rxx
        return {"Rx": Rx, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": Rc}

    @staticmethod
    def _cc_stage(*, Re, Rb, rpi, beta, RL=None, Rs=0.0):
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
    window = CECCDesignWidget()
    window.setWindowTitle("CE-CC Multistage Design")
    window.show()
    sys.exit(app.exec())
