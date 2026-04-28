import os
import sys

# Allows running this file directly during testing.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QWidget, QApplication, QLabel
from PyQt6.uic import loadUi

from core.core_helpers import fmt
from core.bjt_amplifiers_multistage import (
    design_ce_ce,
    design_cc_ce,
    design_ce_cc,
    design_ce_ce_cc,
    design_cc_ce_ce_cc,
    suggest_multistage,
)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, "..", ".."))

# Adjust these two paths if your controller is stored somewhere else.
CHOICE_UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_amp_choice.ui")
DESIGN_UI_PATH = os.path.join(PROJECT_ROOT, "ui", "multistage", "multistage_design.ui")

# Optional image mapping. If these images do not exist, the controller simply keeps the placeholder.
IMAGE_MAP = {
    "CE-CE": os.path.join(PROJECT_ROOT, "assets", "images", "ce_ce_amp.png"),
    "CC-CE": os.path.join(PROJECT_ROOT, "assets", "images", "cc_ce_amp.png"),
    "CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "ce_cc_amp.png"),
    "CE-CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "ce_ce_cc_amp.png"),
    "CC-CE-CE-CC": os.path.join(PROJECT_ROOT, "assets", "images", "cc_ce_ce_cc_amp.png"),
}


class MultistageAmpChoiceWidget(QWidget):
    """Small menu page that lets the user choose a multistage topology."""

    topologySelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(CHOICE_UI_PATH, self)

        self.buttonCECE.clicked.connect(lambda: self.topologySelected.emit("CE-CE"))
        self.buttonCCCE.clicked.connect(lambda: self.topologySelected.emit("CC-CE"))
        self.buttonCECC.clicked.connect(lambda: self.topologySelected.emit("CE-CC"))


class MultistageDesignWidget(QWidget):
    """
    Universal multistage design page.

    Supports:
        CE-CE
        CC-CE
        CE-CC
        CE-CE-CC
        CC-CE-CE-CC
        Auto

    UI input convention:
        Vcc  -> V
        Icmax -> mA
        beta -> unitless
        Ri, Rs, RL -> kΩ in the UI, converted to Ω for core
        Av0, AvT -> unitless magnitude
        Vs -> V
    """

    def __init__(self, topology="CE-CE", parent=None):
        super().__init__(parent)
        loadUi(DESIGN_UI_PATH, self)

        self.topology = topology
        self.target_mode = "Av0"

        self._setup_static_text()
        self._connect_signals()
        self.set_topology(topology)
        self.calculate()

    # ─────────────────────────────────────────────────────────────────────
    # SETUP
    # ─────────────────────────────────────────────────────────────────────

    def _setup_static_text(self):
        # Fix the optional Vs description/unit from the placeholder text in the UI.
        self._set_text("labelRlInfo_2", "Source Signal Voltage")
        self._set_text("labelRlUnit_2", "V")

        self._make_checkable(self.pushButtonModeAv0, True)
        self._make_checkable(self.pushButtonModeAvt, True)
        self.pushButtonModeAv0.setChecked(True)
        self.pushButtonModeAvt.setChecked(False)

        self._set_status("— awaiting input —", "neutral")
        self._clear_outputs()

    def _connect_signals(self):
        for name in [
            "lineEditVcc", "lineEditIcmax", "lineEditBeta", "lineEditRi",
            "lineEditAv0", "lineEditRs", "lineEditRl", "lineEditVs",
        ]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.textChanged.connect(self.calculate)

        self.pushButtonModeAv0.clicked.connect(lambda: self.set_target_mode("Av0"))
        self.pushButtonModeAvt.clicked.connect(lambda: self.set_target_mode("AvT"))
        self.pushButtonClear.clicked.connect(self.clear_inputs)

    def _make_checkable(self, button, checked):
        button.setCheckable(True)
        button.setAutoExclusive(False)
        button.setChecked(checked)

    # ─────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────────────────────────────

    def set_topology(self, topology):
        self.topology = topology
        self._update_topology_view()
        self.calculate()

    def set_target_mode(self, mode):
        self.target_mode = mode
        self.pushButtonModeAv0.setChecked(mode == "Av0")
        self.pushButtonModeAvt.setChecked(mode == "AvT")

        # AvT needs Rs/RL to be meaningful. Av0 does not require them.
        needs_loading = mode == "AvT"
        for name in ["lineEditRs", "lineEditRl"]:
            w = getattr(self, name, None)
            if w is not None:
                w.setEnabled(needs_loading or self.topology in ("CE-CC", "CE-CE-CC", "CC-CE-CE-CC"))

        self.calculate()

    def clear_inputs(self):
        for name in [
            "lineEditVcc", "lineEditIcmax", "lineEditBeta", "lineEditRi",
            "lineEditAv0", "lineEditRs", "lineEditRl", "lineEditVs",
        ]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.clear()
        self._clear_outputs()
        self._set_status("— awaiting input —", "neutral")

    # ─────────────────────────────────────────────────────────────────────
    # CALCULATION
    # ─────────────────────────────────────────────────────────────────────

    def calculate(self):
        try:
            args = self._read_inputs()
            if args is None:
                self._clear_outputs()
                self._set_status("— awaiting input —", "neutral")
                return

            result = self._run_core(args)
            self._display_result(result)

        except Exception as exc:
            self._clear_outputs()
            self._set_status(str(exc), "bad")

    def _read_inputs(self):
        Vcc = self._read_float("lineEditVcc")
        Icmax_mA = self._read_float("lineEditIcmax")
        beta = self._read_float("lineEditBeta")
        gain = self._read_float("lineEditAv0")

        # Required basics must exist before calculating.
        if Vcc is None or Icmax_mA is None or beta is None or gain is None:
            return None

        # Ri is required for CE-CE, CC-CE, CE-CE-CC, CC-CE-CE-CC.
        Ri_k = self._read_float("lineEditRi")
        Ri = Ri_k * 1e3 if Ri_k is not None else None

        Rs_k = self._read_float("lineEditRs")
        RL_k = self._read_float("lineEditRl")
        Vs = self._read_float("lineEditVs")

        Rs = 0.0 if Rs_k is None else Rs_k * 1e3
        RL = None if RL_k is None else RL_k * 1e3

        target_av0 = abs(gain) if self.target_mode == "Av0" else None
        target_avt = abs(gain) if self.target_mode == "AvT" else None

        return {
            "Vcc": Vcc,
            "Icmax_mA": Icmax_mA,
            "beta": beta,
            "target_ri": Ri,
            "target_av0": target_av0,
            "target_avt": target_avt,
            "Rs": Rs,
            "RL": RL,
            "Vs": Vs,
        }

    def _run_core(self, args):
        topology = self.topology

        if topology == "Auto":
            return suggest_multistage(**args)

        if topology == "CE-CE":
            if args["target_ri"] is None:
                raise ValueError("Target Ri is required for CE-CE design.")
            return design_ce_ce(**args)

        if topology == "CC-CE":
            if args["target_ri"] is None:
                raise ValueError("Minimum target Ri is required for CC-CE design.")
            return design_cc_ce(**args)

        if topology == "CE-CC":
            # CE-CC does not require target_ri, so remove it.
            args = dict(args)
            args.pop("target_ri", None)
            return design_ce_cc(**args)

        if topology == "CE-CE-CC":
            if args["target_ri"] is None:
                raise ValueError("Target Ri is required for CE-CE-CC design.")
            return design_ce_ce_cc(**args)

        if topology == "CC-CE-CE-CC":
            if args["target_ri"] is None:
                raise ValueError("Minimum target Ri is required for CC-CE-CE-CC design.")
            return design_cc_ce_ce_cc(**args)

        raise ValueError(f"Unknown topology: {topology}")

    # ─────────────────────────────────────────────────────────────────────
    # DISPLAY
    # ─────────────────────────────────────────────────────────────────────

    def _display_result(self, result):
        self._update_topology_view(result.get("topology", self.topology))

        # Shared/basic bias summary. Uses stage 1 values if available.
        self._set_res("labelOutputVbb", result.get("stage1_Vbb"))
        self._set_res("labelOutputRb", result.get("stage1_Rb"))
        self._set_res("labelOutputRpi", result.get("stage1_rpi"))
        self._set_volt("labelOutputVb", result.get("stage1_Vb"))
        self._set_volt("labelOutputVc", result.get("stage1_Vc"))
        self._set_text("labelOutputIb", "—")  # design file does not currently return Ib

        # Totals.
        self._set_res("labelOutputRiTotal", result.get("Ri_total"))
        self._set_num("labelOutputAv0Total", result.get("Av0_total"))
        self._set_num("labelOutputAvtTotal", result.get("AvT_total"))
        self._set_res("labelOutputRoTotal", result.get("ro_total"))
        self._set_volt("labelOutputVoTotal", result.get("Vo"))

        # Stage cards. Your UI has two stage cards; for 3/4-stage designs this shows
        # the first two stages and keeps totals accurate.
        stages = result.get("stages", [])
        self._display_stage(1, stages[0] if len(stages) >= 1 else None)
        self._display_stage(2, stages[1] if len(stages) >= 2 else None)

        if len(stages) > 2:
            extra = " | Extra stages included in totals: " + " → ".join(s["type"] for s in stages[2:])
        else:
            extra = ""

        warning = result.get("warning", "")
        if result.get("possible", True):
            self._set_status("Possible" + extra if not warning else "Possible — " + warning + extra, "good")
        else:
            self._set_status("Impossible — " + warning + extra, "bad")

    def _display_stage(self, number, stage):
        suffix = "" if number == 1 else "_2"

        rx_label = f"labelOutputRx{number}" if number == 1 else "labelOutputRx_2"
        ri_label = f"labelOutputRi{number}" if number == 1 else "labelOutputRi_2"
        ro_label = "labelOutputRo1" if number == 1 else "labelOutputRo_2"
        av_label = "labelOutputAvo" if number == 1 else "labelOutputAvo_2"
        avt_label = "labelOutputAvt" if number == 1 else "labelOutputAvt_2"

        title_label = "labelInput_2" if number == 1 else "labelInput_3"
        limits_title = "labelLimitsTitle" if number == 1 else "labelLimitsTitle_2"

        if stage is None:
            for label in [rx_label, ri_label, ro_label, av_label, avt_label]:
                self._set_text(label, "—")
            return

        stage_type = stage.get("type", "?")
        self._set_text(title_label, f"Stage {number} Output ({stage_type})")
        self._set_text(limits_title, f"Stage {number} Limits")

        if stage_type == "CE":
            self._set_res(rx_label, stage.get("Rx"))
        else:
            # CC has no Rx. Show Re_ac instead in the Rx slot to avoid wasting UI space.
            self._set_res(rx_label, stage.get("Re_ac"))

        self._set_res(ri_label, stage.get("Ri"))
        self._set_res(ro_label, stage.get("ro"))
        self._set_num(av_label, stage.get("Av"))
        self._set_text(avt_label, "—")  # stage AvT is not separately defined in the core

        # Simple limits display. These are mainly helpful for CE stages.
        if stage_type == "CE":
            self._set_text(f"labelRxMin{suffix}", "0 Ω")
            self._set_res(f"labelRxMax{suffix}", stage.get("Re"))
            self._set_num(f"labelAvoMin{suffix}", None)
            self._set_num(f"labelAvoMax{suffix}", None)
            self._set_num(f"labelRiMin{suffix}", None)
            self._set_num(f"labelRiMax{suffix}", None)
        else:
            self._set_text(f"labelRxMin{suffix}", "CC")
            self._set_text(f"labelRxMax{suffix}", "uses Re_ac")
            self._set_num(f"labelAvoMin{suffix}", stage.get("Av"))
            self._set_num(f"labelAvoMax{suffix}", stage.get("Av"))
            self._set_res(f"labelRiMin{suffix}", stage.get("Ri"))
            self._set_res(f"labelRiMax{suffix}", stage.get("Ri"))

    def _update_topology_view(self, topology=None):
        topology = topology or self.topology
        self._set_text("labelCircuitTitle", f"{topology} Multistage Amplifier")
        self._set_text("labelOutput_2", f"Total Output ({topology})")

        stage_names = self._stage_types_for(topology)
        if len(stage_names) >= 1:
            self._set_text("labelInput_2", f"Stage 1 Output ({stage_names[0]})")
        if len(stage_names) >= 2:
            self._set_text("labelInput_3", f"Stage 2 Output ({stage_names[1]})")

        img = IMAGE_MAP.get(topology)
        if img and os.path.exists(img) and hasattr(self, "labelCircuitImage"):
            pix = QPixmap(img)
            self.labelCircuitImage.setPixmap(pix.scaled(
                self.labelCircuitImage.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            ))

    def _stage_types_for(self, topology):
        return {
            "CE-CE": ["CE", "CE"],
            "CC-CE": ["CC", "CE"],
            "CE-CC": ["CE", "CC"],
            "CE-CE-CC": ["CE", "CE", "CC"],
            "CC-CE-CE-CC": ["CC", "CE", "CE", "CC"],
            "Auto": ["?", "?"],
        }.get(topology, ["?", "?"])

    def _clear_outputs(self):
        label_names = [
            "labelOutputVbb", "labelOutputRb", "labelOutputIb", "labelOutputRpi",
            "labelOutputVc", "labelOutputVb",
            "labelOutputRiTotal", "labelOutputAv0Total", "labelOutputAvtTotal",
            "labelOutputRoTotal", "labelOutputVoTotal",
            "labelOutputRx1", "labelOutputRi1", "labelOutputRo1", "labelOutputAvo", "labelOutputAvt",
            "labelOutputRx_2", "labelOutputRi_2", "labelOutputRo_2", "labelOutputAvo_2", "labelOutputAvt_2",
            "labelAvoMin", "labelAvoMax", "labelRiMin", "labelRiMax", "labelRxMin", "labelRxMax",
            "labelAvoMin_2", "labelAvoMax_2", "labelRiMin_2", "labelRiMax_2", "labelRxMin_2", "labelRxMax_2",
        ]
        for name in label_names:
            self._set_text(name, "—")

    # ─────────────────────────────────────────────────────────────────────
    # SMALL UI HELPERS
    # ─────────────────────────────────────────────────────────────────────

    def _read_float(self, name):
        widget = getattr(self, name, None)
        if widget is None:
            return None
        text = widget.text().strip().replace(",", "")
        if not text:
            return None
        return float(text)

    def _set_text(self, name, value):
        widget = getattr(self, name, None)
        if widget is not None:
            widget.setText(str(value))

    def _set_num(self, name, value, digits=4):
        if value is None:
            self._set_text(name, "—")
        else:
            self._set_text(name, f"{value:.{digits}g}")

    def _set_res(self, name, value):
        self._set_text(name, fmt(value, "Ω") if value is not None else "—")

    def _set_volt(self, name, value):
        self._set_text(name, fmt(value, "V") if value is not None else "—")

    def _set_status(self, text, state="neutral"):
        self._set_text("labelMode", text)
        self._set_text("labelMode_2", text)

        color = {
            "good": "#16a34a",
            "bad": "#dc2626",
            "neutral": "#6b7280",
        }.get(state, "#6b7280")

        style = f"color: {color}; font-weight: 700;"
        for name in ["labelMode", "labelMode_2"]:
            widget = getattr(self, name, None)
            if widget is not None:
                widget.setStyleSheet(style)


# Optional direct-run test. Useful while wiring the UI.
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MultistageDesignWidget("CE-CE")
    w.show()
    sys.exit(app.exec())
