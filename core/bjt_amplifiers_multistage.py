"""
bjt_amplifiers_multistage.py
============================
Multistage BJT amplifier design calculations for EE311-style problems.

Topologies supported:
  - CE-CE        : high gain
  - CC-CE        : high input resistance + CE gain
  - CE-CC        : CE gain + low output resistance
  - CE-CE-CC     : high gain + low output resistance
  - CC-CE-CE-CC  : high input resistance + high gain + low output resistance

Conventions:
  - Resistances are in ohms.
  - Voltages are in volts.
  - Currents are in amps unless the argument name says mA.
  - GUI should convert kΩ/mA/mV before calling these functions.
  - Missing optional values return None for dependent outputs.

Main slide model:
  For cascaded voltage stages:
      Av_total = A1 * (Ri2 / (Ri2 + ro1)) * A2

  A CC stage is used as:
      input buffer  -> raises Ri roughly by beta
      output buffer -> lowers ro roughly by beta
"""

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.core_helpers import _check
from core.bjt_amplifiers import (
    design_ce_from_specs,
    design_cc_from_specs,
    parallel,
    VT_DEFAULT,
    VBE_DEFAULT,
)


# ─────────────────────────────────────────────────────────────────────────────
# SMALL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

EPS = 1e-12


def _pos(name, value):
    if value is None or value <= 0:
        raise ValueError(f"{name} must be positive.")


def _nonneg(name, value):
    if value is not None and value < 0:
        raise ValueError(f"{name} must be zero or positive if provided.")


def _clean_warning(*parts):
    return " | ".join(p for p in parts if p)


def _clip_rx(Rx, Re):
    return max(0.0, min(Rx, Re))


def _validate_rx(Rx, Re, label="Rx"):
    """Return (possible, warning) for a CE emitter bypass resistor result."""
    if Rx < 0:
        return False, f"{label} is negative, so this target is impossible."
    if Rx > Re:
        return False, f"{label} is greater than Re, so this target is impossible."
    return True, ""


def _rx_for_ri(target_ri, Rb, rpi, beta):
    """Solve Ri = Rb || Rxx, where Rxx = rpi + (beta+1)Rx."""
    _pos("target_ri", target_ri)
    if target_ri >= Rb:
        raise ValueError(f"Impossible Ri: target Ri must be less than Rb ({Rb:.3g} Ω).")

    Rxx = (target_ri * Rb) / (Rb - target_ri)
    Rx = (Rxx - rpi) / (beta + 1)
    return Rx, Rxx


def _rx_for_av0(target_av0, Rc, rpi, beta):
    """Solve |Av0| = beta*Rc/Rxx, where Rxx = rpi + (beta+1)Rx."""
    _pos("target_av0", target_av0)
    Rxx = beta * Rc / abs(target_av0)
    Rx = (Rxx - rpi) / (beta + 1)
    return Rx, Rxx


def _ce_ac_from_rx(*, Rx, Rc, Rb, rpi, beta):
    """Return CE small-signal values for one CE stage."""
    Rxx = rpi + (beta + 1) * Rx
    Ri = parallel(Rb, Rxx)
    Av = beta * Rc / Rxx       # magnitude. CE sign is ignored in this design file.
    ro = Rc
    return {"Rx": Rx, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": ro}


def _cc_bias_from_specs(*, Vcc, Icmax_mA, beta, VT=VT_DEFAULT, VBE=VBE_DEFAULT):
    """Return the standard CC bias values using the same formulas as the slides."""
    bias = design_cc_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    return {
        "Re": bias["Re"],
        "Rb": bias["Rb"],
        "rpi": bias["rpi"],
        "Vbb": bias["Vbb"],
        "Vb": bias["Vb"],
        "Ve": bias["Ve"],
    }


def _cc_ac(*, Re, Rb, rpi, beta, RL=None, Rs=None):
    """
    Return CC small-signal values.

    RL is the resistance driven by the emitter follower.
    Rs is the resistance seen looking backward into the source/previous stage.
    """
    Re_ac = parallel(Re, RL) if RL is not None else Re
    Rxx = rpi + (beta + 1) * Re_ac
    Ri = parallel(Rb, Rxx)
    Av = ((beta + 1) * Re_ac) / Rxx

    if Rs is None:
        ro = None
    else:
        Rs_parallel_Rb = 0.0 if Rs == 0 else parallel(Rs, Rb)
        ro = parallel(Re, (rpi + Rs_parallel_Rb) / (beta + 1))

    return {"Re_ac": Re_ac, "Rxx": Rxx, "Ri": Ri, "Av": Av, "ro": ro}


def _solve_bisection(func, low, high, target, *, decreasing=True, iterations=100):
    """Simple robust numeric solve for monotonic gain-vs-Rx functions."""
    f_low = func(low)
    f_high = func(high)

    g_min = min(f_low, f_high)
    g_max = max(f_low, f_high)
    if target < g_min - 1e-9 or target > g_max + 1e-9:
        raise ValueError(
            f"Impossible gain target: requested {target:.4g}, possible range is {g_min:.4g} to {g_max:.4g}."
        )

    lo, hi = low, high
    for _ in range(iterations):
        mid = (lo + hi) / 2.0
        value = func(mid)
        if decreasing:
            if value > target:
                lo = mid
            else:
                hi = mid
        else:
            if value < target:
                lo = mid
            else:
                hi = mid
    return (lo + hi) / 2.0


def _standard_ce_bias(*, Vcc, Icmax_mA, beta, VT=VT_DEFAULT, VBE=VBE_DEFAULT):
    """Run the existing single-stage CE bias design and normalize key names."""
    bias = design_ce_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    return {
        "Rc": bias["Rc"],
        "Re": bias["Re"],
        "Rb": bias["Rb"],
        "R1": bias["R1"],
        "R2": bias["R2"],
        "Vbb": bias["Vbb"],
        "rpi": bias["rpi"],
        "Vb": bias["Vb"],
        "Ve": bias["Ve"],
    }


def _stage_dict(stage_type, number, **values):
    """Create a UI-friendly stage dictionary."""
    out = {"stage": number, "type": stage_type}
    out.update(values)
    return out


def _finish(topology, stages, totals, *, possible=True, warning="", notes=None):
    """Return both normalized UI data and common flat compatibility keys."""
    result = {
        "topology": topology,
        "stages": stages,
        "totals": totals,
        "possible": possible,
        "warning": warning,
        "notes": notes or [],
    }

    # Flat aliases make PyQt label wiring easier.
    for k, v in totals.items():
        result[k] = v
    for stage in stages:
        prefix = f"stage{stage['stage']}_"
        for k, v in stage.items():
            if k != "stage":
                result[prefix + k] = v
    return result


# ─────────────────────────────────────────────────────────────────────────────
# CE-CE: HIGH GAIN
# ─────────────────────────────────────────────────────────────────────────────

def design_ce_ce(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_ri,
    target_av0=None,
    target_avt=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """
    Design a CE-CE amplifier.

    Use this for:
      - required input resistance + internal gain Av0
      - required input resistance + total gain AvT with Rs and RL
    """
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _pos("target_ri", target_ri)
    _nonneg("Rs", Rs)
    _nonneg("Vs", Vs)
    if target_av0 is None and target_avt is None:
        raise ValueError("Provide either target_av0 or target_avt.")
    if target_avt is not None:
        _pos("RL", RL)

    ce = _standard_ce_bias(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]

    # Stage 1 is set by required input resistance.
    Rx1, _ = _rx_for_ri(target_ri, Rb, rpi, beta)
    ok1, warn1 = _validate_rx(Rx1, Re, "Rx1")
    ce1 = _ce_ac_from_rx(Rx=_clip_rx(Rx1, Re), Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)

    def total_av0_for_rx2(rx2):
        ce2_local = _ce_ac_from_rx(Rx=rx2, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
        interstage = ce2_local["Ri"] / (ce2_local["Ri"] + ce1["ro"])
        return ce1["Av"] * interstage * ce2_local["Av"]

    input_factor = ce1["Ri"] / (Rs + ce1["Ri"]) if Rs > 0 else 1.0
    ko_out = RL / (RL + Rc) if RL is not None else None

    if target_av0 is not None:
        wanted_av0 = abs(target_av0)
    else:
        wanted_av0 = abs(target_avt) / (input_factor * ko_out)

    Rx2 = _solve_bisection(lambda x: total_av0_for_rx2(x), 0.0, Re, wanted_av0, decreasing=True)
    ok2, warn2 = _validate_rx(Rx2, Re, "Rx2")
    ce2 = _ce_ac_from_rx(Rx=_clip_rx(Rx2, Re), Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)

    interstage = ce2["Ri"] / (ce2["Ri"] + ce1["ro"])
    Av0_total = ce1["Av"] * interstage * ce2["Av"]
    AvT_total = Av0_total * input_factor * ko_out if RL is not None else None
    Vo = AvT_total * Vs if (Vs is not None and AvT_total is not None) else None

    stages = [
        _stage_dict("CE", 1, **ce, Rx=Rx1, Rx_calc=ce1["Rx"], Rxx=ce1["Rxx"], Ri=ce1["Ri"], Av=ce1["Av"], ro=ce1["ro"]),
        _stage_dict("CE", 2, **ce, Rx=Rx2, Rx_calc=ce2["Rx"], Rxx=ce2["Rxx"], Ri=ce2["Ri"], Av=ce2["Av"], ro=ce2["ro"]),
    ]
    totals = {
        "Ri_total": ce1["Ri"],
        "Av0_total": Av0_total,
        "AvT_total": AvT_total,
        "ro_total": ce2["ro"],
        "Vo": Vo,
        "input_factor": input_factor,
        "interstage_factor": interstage,
        "output_factor": ko_out,
    }
    return _finish("CE-CE", stages, totals, possible=ok1 and ok2, warning=_clean_warning(warn1, warn2))


# ─────────────────────────────────────────────────────────────────────────────
# CC-CE: HIGH INPUT RESISTANCE
# ─────────────────────────────────────────────────────────────────────────────

def design_cc_ce(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_ri,
    target_av0=None,
    target_avt=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """
    Design a CC-CE amplifier.

    The CE stage supplies gain. The CC stage raises the input resistance seen by Vs.
    """
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _pos("target_ri", target_ri)
    _nonneg("Rs", Rs)
    _nonneg("Vs", Vs)
    if target_av0 is None and target_avt is None:
        raise ValueError("Provide either target_av0 or target_avt.")
    if target_avt is not None:
        _pos("RL", RL)

    ce = _standard_ce_bias(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    cc = _cc_bias_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]

    def build_for_rx_ce(rx_ce):
        ce_stage = _ce_ac_from_rx(Rx=rx_ce, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
        cc_stage = _cc_ac(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=ce_stage["Ri"], Rs=Rs)
        cc_to_ce = ce_stage["Ri"] / (ce_stage["Ri"] + (cc_stage["ro"] or 0.0))
        av0_total = cc_stage["Av"] * cc_to_ce * ce_stage["Av"]
        ko_out = RL / (RL + ce_stage["ro"]) if RL is not None else None
        input_factor = cc_stage["Ri"] / (Rs + cc_stage["Ri"]) if Rs > 0 else 1.0
        avt_total = av0_total * input_factor * ko_out if RL is not None else None
        return ce_stage, cc_stage, cc_to_ce, av0_total, avt_total, input_factor, ko_out

    # Solve the CE Rx from requested gain.
    if target_av0 is not None:
        wanted_av0 = abs(target_av0)
    else:
        # numeric solve directly on AvT because CC input loading depends on Rx_ce.
        wanted_avt = abs(target_avt)
        Rx_ce = _solve_bisection(lambda x: build_for_rx_ce(x)[4], 0.0, Re, wanted_avt, decreasing=True)
        wanted_av0 = None

    if target_av0 is not None:
        Rx_ce = _solve_bisection(lambda x: build_for_rx_ce(x)[3], 0.0, Re, wanted_av0, decreasing=True)

    ok_rx, warn_rx = _validate_rx(Rx_ce, Re, "Rx_CE")
    ce_stage, cc_stage, cc_to_ce, Av0_total, AvT_total, input_factor, ko_out = build_for_rx_ce(_clip_rx(Rx_ce, Re))
    Vo = AvT_total * Vs if (Vs is not None and AvT_total is not None) else None

    ri_ok = cc_stage["Ri"] >= target_ri
    warn_ri = "" if ri_ok else f"Ri_total is {cc_stage['Ri']:.3g} Ω, below required {target_ri:.3g} Ω."

    stages = [
        _stage_dict("CC", 1, **cc, Rxx=cc_stage["Rxx"], Ri=cc_stage["Ri"], Av=cc_stage["Av"], ro=cc_stage["ro"], Re_ac=cc_stage["Re_ac"]),
        _stage_dict("CE", 2, **ce, Rx=Rx_ce, Rx_calc=ce_stage["Rx"], Rxx=ce_stage["Rxx"], Ri=ce_stage["Ri"], Av=ce_stage["Av"], ro=ce_stage["ro"]),
    ]
    totals = {
        "Ri_total": cc_stage["Ri"],
        "Av0_total": Av0_total,
        "AvT_total": AvT_total,
        "ro_total": ce_stage["ro"],
        "Vo": Vo,
        "input_factor": input_factor,
        "interstage_factor": cc_to_ce,
        "output_factor": ko_out,
    }
    return _finish("CC-CE", stages, totals, possible=ok_rx and ri_ok, warning=_clean_warning(warn_rx, warn_ri))


# ─────────────────────────────────────────────────────────────────────────────
# CE-CC: LOW OUTPUT RESISTANCE
# ─────────────────────────────────────────────────────────────────────────────

def design_ce_cc(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_av0=None,
    target_avt=None,
    max_ro=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """
    Design a CE-CC amplifier.

    The CE stage supplies gain. The CC stage lowers output resistance.
    """
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _nonneg("Rs", Rs)
    _nonneg("Vs", Vs)
    if target_av0 is None and target_avt is None:
        raise ValueError("Provide either target_av0 or target_avt.")
    if target_avt is not None:
        _pos("RL", RL)

    ce = _standard_ce_bias(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    cc = _cc_bias_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]

    def build_for_rx_ce(rx_ce):
        ce_stage = _ce_ac_from_rx(Rx=rx_ce, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
        cc_stage = _cc_ac(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=RL, Rs=ce_stage["ro"])
        ce_to_cc = cc_stage["Ri"] / (cc_stage["Ri"] + ce_stage["ro"])
        av0_total = ce_stage["Av"] * ce_to_cc * cc_stage["Av"]
        input_factor = ce_stage["Ri"] / (Rs + ce_stage["Ri"]) if Rs > 0 else 1.0
        avt_total = av0_total * input_factor if RL is not None else None
        return ce_stage, cc_stage, ce_to_cc, av0_total, avt_total, input_factor

    if target_av0 is not None:
        wanted = abs(target_av0)
        Rx_ce = _solve_bisection(lambda x: build_for_rx_ce(x)[3], 0.0, Re, wanted, decreasing=True)
    else:
        wanted = abs(target_avt)
        Rx_ce = _solve_bisection(lambda x: build_for_rx_ce(x)[4], 0.0, Re, wanted, decreasing=True)

    ok_rx, warn_rx = _validate_rx(Rx_ce, Re, "Rx_CE")
    ce_stage, cc_stage, ce_to_cc, Av0_total, AvT_total, input_factor = build_for_rx_ce(_clip_rx(Rx_ce, Re))
    Vo = AvT_total * Vs if (Vs is not None and AvT_total is not None) else None

    ro_total = cc_stage["ro"]
    ro_ok = True if max_ro is None or ro_total is None else ro_total <= max_ro
    warn_ro = "" if ro_ok else f"ro_total is {ro_total:.3g} Ω, above required {max_ro:.3g} Ω."

    stages = [
        _stage_dict("CE", 1, **ce, Rx=Rx_ce, Rx_calc=ce_stage["Rx"], Rxx=ce_stage["Rxx"], Ri=ce_stage["Ri"], Av=ce_stage["Av"], ro=ce_stage["ro"]),
        _stage_dict("CC", 2, **cc, Rxx=cc_stage["Rxx"], Ri=cc_stage["Ri"], Av=cc_stage["Av"], ro=cc_stage["ro"], Re_ac=cc_stage["Re_ac"]),
    ]
    totals = {
        "Ri_total": ce_stage["Ri"],
        "Av0_total": Av0_total,
        "AvT_total": AvT_total,
        "ro_total": ro_total,
        "Vo": Vo,
        "input_factor": input_factor,
        "interstage_factor": ce_to_cc,
        "output_factor": None,
    }
    return _finish("CE-CC", stages, totals, possible=ok_rx and ro_ok, warning=_clean_warning(warn_rx, warn_ro))


# ─────────────────────────────────────────────────────────────────────────────
# CE-CE-CC: HIGH GAIN + LOW OUTPUT RESISTANCE
# ─────────────────────────────────────────────────────────────────────────────

def design_ce_ce_cc(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_ri,
    target_av0=None,
    target_avt=None,
    max_ro=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """Design CE-CE followed by a CC output buffer."""
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _pos("target_ri", target_ri)
    _nonneg("Rs", Rs)
    _nonneg("Vs", Vs)
    if target_av0 is None and target_avt is None:
        raise ValueError("Provide either target_av0 or target_avt.")
    if target_avt is not None:
        _pos("RL", RL)

    ce = _standard_ce_bias(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    cc = _cc_bias_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]

    Rx1, _ = _rx_for_ri(target_ri, Rb, rpi, beta)
    ok1, warn1 = _validate_rx(Rx1, Re, "Rx1")
    ce1 = _ce_ac_from_rx(Rx=_clip_rx(Rx1, Re), Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)

    def build_for_rx2(rx2):
        ce2_local = _ce_ac_from_rx(Rx=rx2, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
        cc_local = _cc_ac(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=RL, Rs=ce2_local["ro"])
        f12 = ce2_local["Ri"] / (ce2_local["Ri"] + ce1["ro"])
        f23 = cc_local["Ri"] / (cc_local["Ri"] + ce2_local["ro"])
        av0_total = ce1["Av"] * f12 * ce2_local["Av"] * f23 * cc_local["Av"]
        input_factor = ce1["Ri"] / (Rs + ce1["Ri"]) if Rs > 0 else 1.0
        avt_total = av0_total * input_factor if RL is not None else None
        return ce2_local, cc_local, f12, f23, av0_total, avt_total, input_factor

    if target_av0 is not None:
        wanted = abs(target_av0)
        Rx2 = _solve_bisection(lambda x: build_for_rx2(x)[4], 0.0, Re, wanted, decreasing=True)
    else:
        wanted = abs(target_avt)
        Rx2 = _solve_bisection(lambda x: build_for_rx2(x)[5], 0.0, Re, wanted, decreasing=True)

    ok2, warn2 = _validate_rx(Rx2, Re, "Rx2")
    ce2, cc3, f12, f23, Av0_total, AvT_total, input_factor = build_for_rx2(_clip_rx(Rx2, Re))
    Vo = AvT_total * Vs if (Vs is not None and AvT_total is not None) else None

    ro_total = cc3["ro"]
    ro_ok = True if max_ro is None or ro_total is None else ro_total <= max_ro
    warn_ro = "" if ro_ok else f"ro_total is {ro_total:.3g} Ω, above required {max_ro:.3g} Ω."

    stages = [
        _stage_dict("CE", 1, **ce, Rx=Rx1, Rx_calc=ce1["Rx"], Rxx=ce1["Rxx"], Ri=ce1["Ri"], Av=ce1["Av"], ro=ce1["ro"]),
        _stage_dict("CE", 2, **ce, Rx=Rx2, Rx_calc=ce2["Rx"], Rxx=ce2["Rxx"], Ri=ce2["Ri"], Av=ce2["Av"], ro=ce2["ro"]),
        _stage_dict("CC", 3, **cc, Rxx=cc3["Rxx"], Ri=cc3["Ri"], Av=cc3["Av"], ro=cc3["ro"], Re_ac=cc3["Re_ac"]),
    ]
    totals = {
        "Ri_total": ce1["Ri"],
        "Av0_total": Av0_total,
        "AvT_total": AvT_total,
        "ro_total": ro_total,
        "Vo": Vo,
        "input_factor": input_factor,
        "interstage_factor_12": f12,
        "interstage_factor_23": f23,
        "output_factor": None,
    }
    return _finish("CE-CE-CC", stages, totals, possible=ok1 and ok2 and ro_ok, warning=_clean_warning(warn1, warn2, warn_ro))


# ─────────────────────────────────────────────────────────────────────────────
# CC-CE-CE-CC: HIGH Ri + HIGH GAIN + LOW ro
# ─────────────────────────────────────────────────────────────────────────────

def design_cc_ce_ce_cc(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_ri,
    target_av0=None,
    target_avt=None,
    max_ro=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """Design CC input buffer + CE-CE gain block + CC output buffer."""
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _pos("target_ri", target_ri)
    _nonneg("Rs", Rs)
    _nonneg("Vs", Vs)
    if target_av0 is None and target_avt is None:
        raise ValueError("Provide either target_av0 or target_avt.")
    if target_avt is not None:
        _pos("RL", RL)

    ce = _standard_ce_bias(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    cc = _cc_bias_from_specs(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta, VT=VT, VBE=VBE)
    Rc, Re, Rb, rpi = ce["Rc"], ce["Re"], ce["Rb"], ce["rpi"]

    # Since the first CC boosts input resistance, choose CE1 for max gain by default.
    # If the boosted Ri is too low, the UI will show impossible/warning.
    Rx1 = 0.0
    ce1 = _ce_ac_from_rx(Rx=Rx1, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
    cc1 = _cc_ac(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=ce1["Ri"], Rs=Rs)

    def build_for_rx2(rx2):
        ce2_local = _ce_ac_from_rx(Rx=rx2, Rc=Rc, Rb=Rb, rpi=rpi, beta=beta)
        cc4_local = _cc_ac(Re=cc["Re"], Rb=cc["Rb"], rpi=cc["rpi"], beta=beta, RL=RL, Rs=ce2_local["ro"])

        f12 = ce1["Ri"] / (ce1["Ri"] + (cc1["ro"] or 0.0))
        f23 = ce2_local["Ri"] / (ce2_local["Ri"] + ce1["ro"])
        f34 = cc4_local["Ri"] / (cc4_local["Ri"] + ce2_local["ro"])

        av0_total = cc1["Av"] * f12 * ce1["Av"] * f23 * ce2_local["Av"] * f34 * cc4_local["Av"]
        input_factor = cc1["Ri"] / (Rs + cc1["Ri"]) if Rs > 0 else 1.0
        avt_total = av0_total * input_factor if RL is not None else None
        return ce2_local, cc4_local, f12, f23, f34, av0_total, avt_total, input_factor

    if target_av0 is not None:
        wanted = abs(target_av0)
        Rx2 = _solve_bisection(lambda x: build_for_rx2(x)[5], 0.0, Re, wanted, decreasing=True)
    else:
        wanted = abs(target_avt)
        Rx2 = _solve_bisection(lambda x: build_for_rx2(x)[6], 0.0, Re, wanted, decreasing=True)

    ok2, warn2 = _validate_rx(Rx2, Re, "Rx2")
    ce2, cc4, f12, f23, f34, Av0_total, AvT_total, input_factor = build_for_rx2(_clip_rx(Rx2, Re))
    Vo = AvT_total * Vs if (Vs is not None and AvT_total is not None) else None

    ri_ok = cc1["Ri"] >= target_ri
    warn_ri = "" if ri_ok else f"Ri_total is {cc1['Ri']:.3g} Ω, below required {target_ri:.3g} Ω."
    ro_total = cc4["ro"]
    ro_ok = True if max_ro is None or ro_total is None else ro_total <= max_ro
    warn_ro = "" if ro_ok else f"ro_total is {ro_total:.3g} Ω, above required {max_ro:.3g} Ω."

    stages = [
        _stage_dict("CC", 1, **cc, Rxx=cc1["Rxx"], Ri=cc1["Ri"], Av=cc1["Av"], ro=cc1["ro"], Re_ac=cc1["Re_ac"]),
        _stage_dict("CE", 2, **ce, Rx=Rx1, Rx_calc=Rx1, Rxx=ce1["Rxx"], Ri=ce1["Ri"], Av=ce1["Av"], ro=ce1["ro"]),
        _stage_dict("CE", 3, **ce, Rx=Rx2, Rx_calc=ce2["Rx"], Rxx=ce2["Rxx"], Ri=ce2["Ri"], Av=ce2["Av"], ro=ce2["ro"]),
        _stage_dict("CC", 4, **cc, Rxx=cc4["Rxx"], Ri=cc4["Ri"], Av=cc4["Av"], ro=cc4["ro"], Re_ac=cc4["Re_ac"]),
    ]
    totals = {
        "Ri_total": cc1["Ri"],
        "Av0_total": Av0_total,
        "AvT_total": AvT_total,
        "ro_total": ro_total,
        "Vo": Vo,
        "input_factor": input_factor,
        "interstage_factor_12": f12,
        "interstage_factor_23": f23,
        "interstage_factor_34": f34,
        "output_factor": None,
    }
    return _finish("CC-CE-CE-CC", stages, totals, possible=ok2 and ri_ok and ro_ok, warning=_clean_warning(warn2, warn_ri, warn_ro))


# ─────────────────────────────────────────────────────────────────────────────
# AUTO SUGGESTION WRAPPER
# ─────────────────────────────────────────────────────────────────────────────

def suggest_multistage(
    *,
    Vcc,
    Icmax_mA,
    beta,
    target_ri=None,
    target_av0=None,
    target_avt=None,
    max_ro=None,
    Rs=0.0,
    RL=None,
    Vs=None,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    """
    Choose a topology using the lecture strategy:
      high gain -> CE-CE
      high Ri -> CC-CE
      low ro -> CE-CC or CE-CE-CC
      high gain + high Ri + low ro -> CC-CE-CE-CC
    """
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)

    if target_ri is None:
        target_ri = 1.0  # basically no Ri requirement

    candidates = []

    attempts = [
        ("CE-CE", design_ce_ce, dict(target_ri=target_ri)),
        ("CC-CE", design_cc_ce, dict(target_ri=target_ri)),
        ("CE-CC", design_ce_cc, dict(max_ro=max_ro)),
        ("CE-CE-CC", design_ce_ce_cc, dict(target_ri=target_ri, max_ro=max_ro)),
        ("CC-CE-CE-CC", design_cc_ce_ce_cc, dict(target_ri=target_ri, max_ro=max_ro)),
    ]

    for name, fn, extra in attempts:
        try:
            result = fn(
                Vcc=Vcc,
                Icmax_mA=Icmax_mA,
                beta=beta,
                target_av0=target_av0,
                target_avt=target_avt,
                Rs=Rs,
                RL=RL,
                Vs=Vs,
                VT=VT,
                VBE=VBE,
                **extra,
            )
            if result["possible"]:
                candidates.append(result)
        except Exception:
            pass

    if not candidates:
        raise ValueError("No supported multistage topology could satisfy the requested targets.")

    # Prefer the simplest working topology.
    candidates.sort(key=lambda r: len(r["stages"]))
    chosen = candidates[0]
    chosen["notes"].append("Auto-selected simplest topology that satisfies the available targets.")
    return chosen


# Backward-friendly aliases you may prefer in the GUI
make_ce_ce = design_ce_ce
make_cc_ce = design_cc_ce
make_ce_cc = design_ce_cc
make_ce_ce_cc = design_ce_ce_cc
make_cc_ce_ce_cc = design_cc_ce_ce_cc
