import os
import sys

from PyQt6.QtWidgets import QApplication, QWidget, QPushButton, QLineEdit, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt
from PyQt6.uic import loadUi

# Make project imports work when this file is inside controllers/bjt_amplifiers_controllers
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))
sys.path.append(PROJECT_ROOT)

from core.core_helpers import fmt, positive_validator, signed_validator
from core.bjt_amplifiers_multistage import (
    design_ce_ce,
    design_cc_ce,
    design_ce_cc,
    design_ce_ce_cc,
    design_cc_ce_ce_cc,
    suggest_multistage,
)

DESIGN_UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design.ui")

IMAGE_MAP = {
    "CE-CE": os.path.join(PROJECT_ROOT, "assets", "images", "ce_ce_amp.png"),
    "CC-CE": os.path.join(PROJECT_ROOT, "assets", "images", "cc_ce_amp.png"),
    "CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "ce_cc_amp.png"),
    "CE-CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "ce_ce_cc_amp.png"),
    "CC-CE-CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "cc_ce_ce_cc_amp.png"),
}


class MultistageDesignWidget(QWidget):
    """Universal multistage design page.

    UI units:
      Vcc: V
      Icmax: mA
      beta: unitless
      Ri, Rs, RL: kΩ
      Vs: V
      gain: unitless
    """

    def __init__(self, topology="CE-CE", parent=None):
        super().__init__(parent)
        loadUi(DESIGN_UI_PATH, self)

        self.topology = self._normalize_topology(topology)
        self.target_mode = "Av0"
        self._clearing = False

        self._setup_validators()
        self._setup_buttons()
        self._setup_connections()
        self._set_static_text()
        self.set_topology(self.topology)
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- SETUP ----------------

    def _setup_validators(self):
        if hasattr(self, "lineEditVcc"):
            self.lineEditVcc.setValidator(signed_validator(self))

        for name in [
            "lineEditIcmax", "lineEditBeta", "lineEditRi", "lineEditAv0",
            "lineEditRs", "lineEditRl", "lineEditVs",
        ]:
            if hasattr(self, name):
                getattr(self, name).setValidator(positive_validator(self))

    def _setup_buttons(self):
        self._mode_buttons = []

        for name in ["pushButtonModeAv0", "pushButtonModeAvt"]:
            btn = getattr(self, name, None)
            if isinstance(btn, QPushButton):
                btn.setCheckable(True)
                btn.setAutoExclusive(False)
                self._mode_buttons.append(btn)

        if hasattr(self, "pushButtonModeAv0"):
            self.pushButtonModeAv0.clicked.connect(lambda: self.set_target_mode("Av0"))
        if hasattr(self, "pushButtonModeAvt"):
            self.pushButtonModeAvt.clicked.connect(lambda: self.set_target_mode("AvT"))
        if hasattr(self, "pushButtonClear"):
            self.pushButtonClear.clicked.connect(self.clear_fields)

        self._sync_mode_buttons()

    def _setup_connections(self):
        for line_edit in self.findChildren(QLineEdit):
            line_edit.textChanged.connect(self.calculate)

    def _set_static_text(self):
        self._set_label("labelVsInfo", "Source Signal Voltage")
        self._set_label("labelVsUnit", "V")
        self._update_gain_target_labels()

    # ---------------- PUBLIC ----------------

    def set_topology(self, topology):
        self.topology = self._normalize_topology(topology)
        self._update_topology_ui()
        self.calculate()

    def set_target_mode(self, mode):
        self.target_mode = "AvT" if str(mode).lower() == "avt" else "Av0"
        self._sync_mode_buttons()
        self._update_gain_target_labels()
        self.calculate()

    def clear_fields(self):
        self._clearing = True
        for line_edit in self.findChildren(QLineEdit):
            line_edit.clear()
        self._clearing = False
        self._clear_outputs_only()
        self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")

    # ---------------- CALCULATION ----------------

    def calculate(self):
        if self._clearing:
            return

        try:
            inputs = self._read_inputs()
            if inputs is None:
                self._clear_outputs_only()
                self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
                return

            result = self._run_core(inputs)
            self._push_outputs(result)

            if result.get("possible", True):
                self._set_mode("DESIGNED", "#d4edda", "#155724")
            else:
                self._set_mode(result.get("warning") or "IMPOSSIBLE", "#fff3cd", "#856404")

        except ValueError as e:
            self._clear_outputs_only()
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")

    def _read_inputs(self):
        vcc = self._read_float("lineEditVcc")
        icmax = self._read_float("lineEditIcmax")
        beta = self._read_float("lineEditBeta")
        gain = self._read_float("lineEditAv0")

        # Required for any calculation.
        if None in (vcc, icmax, beta, gain):
            return None

        ri_k = self._read_float("lineEditRi")
        rs_k = self._read_float("lineEditRs")
        rl_k = self._read_float("lineEditRl")
        vs = self._read_float("lineEditVs")

        return {
            "Vcc": vcc,
            "Icmax_mA": icmax,
            "beta": beta,
            "target_ri": None if ri_k is None else ri_k * 1e3,
            "target_av0": abs(gain) if self.target_mode == "Av0" else None,
            "target_avt": abs(gain) if self.target_mode == "AvT" else None,
            "Rs": 0.0 if rs_k is None else rs_k * 1e3,
            "RL": None if rl_k is None else rl_k * 1e3,
            "Vs": vs,
        }

    def _run_core(self, args):
        if self.topology == "Auto":
            return suggest_multistage(**args)

        if self.topology == "CE-CE":
            self._require_ri(args)
            return design_ce_ce(**args)

        if self.topology == "CC-CE":
            self._require_ri(args)
            return design_cc_ce(**args)

        if self.topology == "CE-CC":
            args = dict(args)
            args.pop("target_ri", None)  # CE-CC is mainly gain + output buffer
            return design_ce_cc(**args)

        if self.topology == "CE-CE-CC":
            self._require_ri(args)
            return design_ce_ce_cc(**args)

        if self.topology == "CC-CE-CE-CC":
            self._require_ri(args)
            return design_cc_ce_ce_cc(**args)

        raise ValueError(f"Unknown topology: {self.topology}")

    def _require_ri(self, args):
        if args.get("target_ri") is None:
            raise ValueError(f"Target Ri is required for {self.topology}.")

    # ---------------- OUTPUTS ----------------

    def _push_outputs(self, result):
        stages = result.get("stages", [])
        totals = result.get("totals", {})

        self._update_topology_ui(result.get("topology", self.topology))
        self._push_bias(stages[0] if stages else {})
        self._push_stage(1, stages[0] if len(stages) >= 1 else None)
        self._push_stage(2, stages[1] if len(stages) >= 2 else None)
        self._push_totals(totals)

    def _push_bias(self, stage):
        self._set_volt("labelOutputVbb", stage.get("Vbb"))
        self._set_res("labelOutputRb", stage.get("Rb"))
        self._set_res("labelOutputRpi", stage.get("rpi"))
        self._set_volt("labelOutputVb", stage.get("Vb"))
        self._set_current("labelOutputIb", self._estimate_ib())
        self._set_volt("labelOutputVc", self._estimate_vc(stage))

    def _push_totals(self, totals):
        self._set_res("labelOutputRiTotal", totals.get("Ri_total"))
        self._set_num("labelOutputAv0Total", totals.get("Av0_total"))
        self._set_num("labelOutputAvtTotal", totals.get("AvT_total"))
        self._set_res("labelOutputRoTotal", totals.get("ro_total"))
        self._set_volt("labelOutputVoTotal", totals.get("Vo"))

    def _push_stage(self, number, stage):
        names = self._stage_names(number)

        if stage is None:
            for key in ["rx", "ri", "ro", "av", "avt"]:
                self._set_label(names[key], "—")
            return

        stype = stage.get("type", "?")
        self._set_label(names["title"], f"STAGE {number} OUTPUT: {stype}")

        if stype == "CC":
            self._set_label(names["rx_icon"], f"R<sub>E(ac)</sub> {number}")
            self._set_res(names["rx"], stage.get("Re_ac"))
            self._set_cc_limits(stage, names)
        else:
            self._set_label(names["rx_icon"], f"R<sub>X{number}</sub>")
            self._set_res(names["rx"], stage.get("Rx"))
            self._set_ce_limits(stage, names)

        self._set_res(names["ri"], stage.get("Ri"))
        self._set_res(names["ro"], stage.get("ro"))
        self._set_num(names["av"], stage.get("Av"))
        self._set_label(names["avt"], "—")  # AvT is a total/system value, not a per-stage value here.

    def _set_ce_limits(self, stage, names):
        beta = self._read_float("lineEditBeta")
        Rc, Re, Rb, rpi = stage.get("Rc"), stage.get("Re"), stage.get("Rb"), stage.get("rpi")

        if None in (beta, Rc, Re, Rb, rpi):
            return

        av_max = beta * Rc / rpi
        av_min = beta * Rc / (rpi + (beta + 1) * Re)
        ri_min = self._parallel(Rb, rpi)
        ri_max = self._parallel(Rb, rpi + (beta + 1) * Re)

        self._set_num(names["av_min"], max(1.0, av_min))
        self._set_num(names["av_max"], av_max)
        self._set_res(names["ri_min"], ri_min)
        self._set_res(names["ri_max"], ri_max)
        self._set_res(names["rx_min"], 0.0)
        self._set_res(names["rx_max"], Re)
        self._set_label(names["rx_op"], "≤ Rx ≤")

    def _set_cc_limits(self, stage, names):
        self._set_num(names["av_min"], stage.get("Av"))
        self._set_num(names["av_max"], stage.get("Av"))
        self._set_res(names["ri_min"], stage.get("Ri"))
        self._set_res(names["ri_max"], stage.get("Ri"))
        self._set_label(names["rx_min"], "—")
        self._set_label(names["rx_op"], "CC")
        self._set_label(names["rx_max"], "—")

    def _stage_names(self, number):
        if number == 1:
            return {
                "title": "labelInput_2",
                "rx_icon": "labelIconRx1", "rx": "labelOutputRx1",
                "ri": "labelOutputRi1", "ro": "labelOutputRo1",
                "av": "labelOutputAvo", "avt": "labelOutputAvt",
                "av_min": "labelAvoMin", "av_max": "labelAvoMax",
                "ri_min": "labelRiMin", "ri_max": "labelRiMax",
                "rx_min": "labelRxMin", "rx_op": "labelRxOp", "rx_max": "labelRxMax",
            }

        return {
            "title": "labelInput_3",
            "rx_icon": "labelIconRx_2", "rx": "labelOutputRx_2",
            "ri": "labelOutputRi_2", "ro": "labelOutputRo_2",
            "av": "labelOutputAvo_2", "avt": "labelOutputAvt_2",
            "av_min": "labelAvoMin_2", "av_max": "labelAvoMax_2",
            "ri_min": "labelRiMin_2", "ri_max": "labelRiMax_2",
            "rx_min": "labelRxMin_2", "rx_op": "labelRxOp_2", "rx_max": "labelRxMax_2",
        }

    # ---------------- UI TEXT ----------------

    def _update_gain_target_labels(self):
        if self.target_mode == "AvT":
            self._set_label("labelBeta_3", "AvT")
            self._set_label("labelGain_3", "Total Gain")
        else:
            self._set_label("labelBeta_3", "Av0")
            self._set_label("labelGain_3", "Internal Gain")

    def _update_topology_ui(self, topology=None):
        topology = topology or self.topology
        self._set_label("labelCircuitTitle", f"{topology} Multistage Amplifier")
        self._set_label("labelOutput_2", f"Total Output ({topology})")

        stage_types = self._stage_types(topology)
        if len(stage_types) >= 1:
            self._set_label("labelInput_2", f"STAGE 1 OUTPUT: {stage_types[0]}")
        if len(stage_types) >= 2:
            self._set_label("labelInput_3", f"STAGE 2 OUTPUT: {stage_types[1]}")

        img = IMAGE_MAP.get(topology)
        image_label = getattr(self, "labelCircuitImage", None)
        if img and os.path.exists(img) and image_label is not None:
            pix = QPixmap(img)
            image_label.setPixmap(
                pix.scaled(
                    image_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def _sync_mode_buttons(self):
        if hasattr(self, "pushButtonModeAv0"):
            self.pushButtonModeAv0.setChecked(self.target_mode == "Av0")
        if hasattr(self, "pushButtonModeAvt"):
            self.pushButtonModeAvt.setChecked(self.target_mode == "AvT")

    def _set_mode(self, text, bg, fg):
        # Same visual approach as your CE controller: only status labels get restyled.
        style = (
            f"border-radius:6px; font: 700 11pt 'Rockwell'; "
            f"padding: 4px 14px; background-color:{bg}; color:{fg};"
        )
        for name in ["labelMode", "labelMode_2"]:
            w = getattr(self, name, None)
            if w is not None:
                w.setText(text)
                w.setStyleSheet(style)

    # ---------------- SMALL HELPERS ----------------

    def _read_float(self, name):
        w = getattr(self, name, None)
        if w is None:
            return None
        text = w.text().strip().replace(",", "")
        return None if text == "" else float(text)

    def _set_label(self, name, text):
        w = getattr(self, name, None)
        if w is not None:
            w.setText(str(text))

    def _set_num(self, name, value):
        self._set_label(name, "—" if value is None else f"{value:.4g}")

    def _set_res(self, name, value):
        self._set_label(name, fmt(value, "Ω"))

    def _set_volt(self, name, value):
        self._set_label(name, fmt(value, "V"))

    def _set_current(self, name, value):
        self._set_label(name, fmt(value, "A", scale="µA"))

    def _clear_outputs_only(self):
        # Explicit list only. Do NOT clear input labels like labelRi.
        output_labels = [
            "labelOutputVbb", "labelOutputRb", "labelOutputIb", "labelOutputRpi",
            "labelOutputVc", "labelOutputVb",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal",
            "labelOutputRoTotal", "labelOutputVoTotal",
            "labelOutputRx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo", "labelOutputAvt",
            "labelAvoMin", "labelAvoMax", "labelRiMin", "labelRiMax", "labelRxMin", "labelRxMax",
            "labelOutputRx_2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2", "labelOutputAvt_2",
            "labelAvoMin_2", "labelAvoMax_2", "labelRiMin_2", "labelRiMax_2", "labelRxMin_2", "labelRxMax_2",
        ]
        for name in output_labels:
            self._set_label(name, "—")

    def _estimate_ib(self):
        icmax = self._read_float("lineEditIcmax")
        beta = self._read_float("lineEditBeta")
        if icmax is None or beta in (None, 0):
            return None
        return (icmax * 1e-3) / beta

    def _estimate_vc(self, stage):
        vcc = self._read_float("lineEditVcc")
        icmax = self._read_float("lineEditIcmax")
        Rc = stage.get("Rc")
        if None in (vcc, icmax, Rc):
            return None
        return vcc - (icmax * 1e-3) * Rc

    @staticmethod
    def _parallel(*values):
        values = [v for v in values if v is not None]
        if not values:
            return None
        if any(v == 0 for v in values):
            return 0.0
        return 1.0 / sum(1.0 / v for v in values)

    @staticmethod
    def _normalize_topology(text):
        key = str(text).strip().upper().replace("–", "-").replace("—", "-").replace(" ", "")
        return {
            "AUTO": "Auto",
            "CECE": "CE-CE", "CE-CE": "CE-CE",
            "CCCE": "CC-CE", "CC-CE": "CC-CE",
            "CECC": "CE-CC", "CE-CC": "CE-CC",
            "CECECC": "CE-CE-CC", "CE-CE-CC": "CE-CE-CC",
            "CCCECECC": "CC-CE-CE-CC", "CC-CE-CE-CC": "CC-CE-CE-CC",
        }.get(key, "CE-CE")

    @staticmethod
    def _stage_types(topology):
        return {
            "CE-CE": ["CE", "CE"],
            "CC-CE": ["CC", "CE"],
            "CE-CC": ["CE", "CC"],
            "CE-CE-CC": ["CE", "CE", "CC"],
            "CC-CE-CE-CC": ["CC", "CE", "CE", "CC"],
            "Auto": ["?", "?"],
        }.get(topology, ["?", "?"])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MultistageDesignWidget("CE-CE")
    w.show()
    sys.exit(app.exec())
