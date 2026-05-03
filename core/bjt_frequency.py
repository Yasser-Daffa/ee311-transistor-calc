"""
core/bjt_frequency.py

EE311 BJT Frequency Response helpers.

Unit convention inside this file:
- Resistances are in ohms (Ω)
- Capacitances are in farads (F)
- Frequencies are in hertz (Hz)
- Currents are in amps (A)
- Voltages are in volts (V)

This file is intentionally UI-independent.
Your PyQt widgets should convert user inputs to these units before calling these functions.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import pi
from typing import Iterable, Optional


# ---------------------------------------------------------------------------
# Basic helpers
# ---------------------------------------------------------------------------

def parallel(*values: Optional[float]) -> Optional[float]:
    """
    Parallel resistance/capacitance style helper.

    Ignores None values.
    Returns None if no valid values are provided.
    Raises ValueError for zero/negative values because resistance-style
    parallel calculations in this app should use positive numbers.
    """
    vals = [v for v in values if v is not None]

    if not vals:
        return None

    for v in vals:
        if v <= 0:
            raise ValueError("parallel() values must be positive.")

    return 1.0 / sum(1.0 / v for v in vals)


def cutoff_frequency(resistance_ohm: float, capacitance_f: float) -> float:
    """
    f = 1 / (2πRC)
    """
    if resistance_ohm <= 0:
        raise ValueError("Resistance must be positive.")
    if capacitance_f <= 0:
        raise ValueError("Capacitance must be positive.")

    return 1.0 / (2.0 * pi * resistance_ohm * capacitance_f)


def conservative_low_range(freqs_hz: Iterable[Optional[float]]) -> dict:
    """
    Low cutoff range:
        max(fi) <= fL <= sum(fi)

    Used for CE, CC, and multistage low-frequency analysis.
    """
    freqs = [f for f in freqs_hz if f is not None]

    if not freqs:
        return {
            "fL_min": None,
            "fL_max": None,
            "fL_conservative": None,
        }

    return {
        "fL_min": max(freqs),
        "fL_max": sum(freqs),
        "fL_conservative": max(freqs),
    }


def conservative_high_range(freqs_hz: Iterable[Optional[float]]) -> dict:
    """
    High cutoff range:
        parallel(fi) <= fH <= min(fi)

    Conservative high cutoff is the parallel combination.
    """
    freqs = [f for f in freqs_hz if f is not None]

    if not freqs:
        return {
            "fH_min": None,
            "fH_max": None,
            "fH_conservative": None,
        }

    return {
        "fH_min": parallel(*freqs),
        "fH_max": min(freqs),
        "fH_conservative": parallel(*freqs),
    }


# ---------------------------------------------------------------------------
# CE low-frequency analysis
# ---------------------------------------------------------------------------

@dataclass
class CELowInputs:
    """
    Common-emitter low-frequency inputs.

    Use either:
    - rb_ohm directly, OR
    - r1_ohm and r2_ohm to calculate RB = R1 || R2

    Capacitors may be None. Missing capacitors are skipped.
    """
    rs_ohm: float
    rc_ohm: float
    re_ohm: float
    rx_ohm: float
    rl_ohm: float
    beta: float
    rpi_ohm: float

    c1_f: Optional[float] = None
    c2_f: Optional[float] = None
    ce_f: Optional[float] = None

    rb_ohm: Optional[float] = None
    r1_ohm: Optional[float] = None
    r2_ohm: Optional[float] = None


def ce_low_frequency(inputs: CELowInputs, mode: str = "full") -> dict:
    """
    CE low-frequency analysis.

    mode options:
    - "full"
    - "c1_only"
    - "c2_only"
    - "ce_only"

    Slide formulas:
        RB  = R1 || R2
        RXX = rπ + (β + 1)RX
        RSB = RS || RB

        R11 = RS + (RB || RXX)
        R22 = RL + RC
        REE = RE || ( RX + (rπ + RSB)/(β + 1) )

        f1 = 1/(2πR11C1)
        f2 = 1/(2πR22C2)
        fE = 1/(2πREECE)

        max(f1, f2, fE) <= fL <= f1 + f2 + fE
    """
    mode = mode.lower().strip()

    rb = inputs.rb_ohm
    if rb is None:
        rb = parallel(inputs.r1_ohm, inputs.r2_ohm)

    if rb is None:
        raise ValueError("CE low analysis requires RB or both R1 and R2.")

    if inputs.beta <= 0:
        raise ValueError("beta must be positive.")

    rxx = inputs.rpi_ohm + (inputs.beta + 1.0) * inputs.rx_ohm
    rsb = parallel(inputs.rs_ohm, rb)

    r11 = inputs.rs_ohm + parallel(rb, rxx)
    r22 = inputs.rl_ohm + inputs.rc_ohm
    ree = parallel(
        inputs.re_ohm,
        inputs.rx_ohm + (inputs.rpi_ohm + rsb) / (inputs.beta + 1.0),
    )

    f1 = cutoff_frequency(r11, inputs.c1_f) if inputs.c1_f else None
    f2 = cutoff_frequency(r22, inputs.c2_f) if inputs.c2_f else None
    fE = cutoff_frequency(ree, inputs.ce_f) if inputs.ce_f else None

    if mode == "c1_only":
        active_freqs = [f1]
    elif mode == "c2_only":
        active_freqs = [f2]
    elif mode == "ce_only":
        active_freqs = [fE]
    elif mode == "full":
        active_freqs = [f1, f2, fE]
    else:
        raise ValueError("mode must be: full, c1_only, c2_only, or ce_only.")

    low = conservative_low_range(active_freqs)

    return {
        "RB": rb,
        "RXX": rxx,
        "RSB": rsb,
        "R11": r11,
        "R22": r22,
        "REE": ree,
        "f1": f1,
        "f2": f2,
        "fE": fE,
        **low,
    }


# ---------------------------------------------------------------------------
# CC low-frequency analysis
# ---------------------------------------------------------------------------

@dataclass
class CCLowInputs:
    """
    Common-collector low-frequency inputs.

    Capacitors may be None. Missing capacitors are skipped.
    """
    rs_ohm: float
    rb_ohm: float
    re_ohm: float
    rl_ohm: float
    beta: float
    rpi_ohm: float

    c1_f: Optional[float] = None
    c2_f: Optional[float] = None


def cc_low_frequency(inputs: CCLowInputs, mode: str = "full") -> dict:
    """
    CC low-frequency analysis.

    mode options:
    - "full"
    - "c1_only"
    - "c2_only"

    Slide formulas:
        REL = RE || RL
        RSB = RS || RB

        R11 = RS + RB || [rπ + (β + 1)REL]
        R22 = RL + RE || ((rπ + RSB)/(β + 1))

        f1 = 1/(2πR11C1)
        f2 = 1/(2πR22C2)

        max(f1, f2) <= fL <= f1 + f2
    """
    mode = mode.lower().strip()

    if inputs.beta <= 0:
        raise ValueError("beta must be positive.")

    rel = parallel(inputs.re_ohm, inputs.rl_ohm)
    rsb = parallel(inputs.rs_ohm, inputs.rb_ohm)

    r11 = inputs.rs_ohm + parallel(
        inputs.rb_ohm,
        inputs.rpi_ohm + (inputs.beta + 1.0) * rel,
    )

    r22 = inputs.rl_ohm + parallel(
        inputs.re_ohm,
        (inputs.rpi_ohm + rsb) / (inputs.beta + 1.0),
    )

    f1 = cutoff_frequency(r11, inputs.c1_f) if inputs.c1_f else None
    f2 = cutoff_frequency(r22, inputs.c2_f) if inputs.c2_f else None

    if mode == "c1_only":
        active_freqs = [f1]
    elif mode == "c2_only":
        active_freqs = [f2]
    elif mode == "full":
        active_freqs = [f1, f2]
    else:
        raise ValueError("mode must be: full, c1_only, or c2_only.")

    low = conservative_low_range(active_freqs)

    return {
        "REL": rel,
        "RSB": rsb,
        "R11": r11,
        "R22": r22,
        "f1": f1,
        "f2": f2,
        **low,
    }


# ---------------------------------------------------------------------------
# High-frequency analysis and Cx design
# ---------------------------------------------------------------------------

@dataclass
class HighFreqInputs:
    """
    Generic high-frequency input.

    This works for quiz-style problems where Rπ, Rµ, Cπ, Cµ are already given.
    """
    rpi_eq_ohm: float
    rmu_eq_ohm: float
    cpi_f: float
    cmu_f: float


def high_frequency(inputs: HighFreqInputs) -> dict:
    """
    High-frequency analysis:
        fπ = 1/(2πRπCπ)
        fµ = 1/(2πRµCµ)

        fπ || fµ <= fH <= min(fπ, fµ)
    """
    fpi = cutoff_frequency(inputs.rpi_eq_ohm, inputs.cpi_f)
    fmu = cutoff_frequency(inputs.rmu_eq_ohm, inputs.cmu_f)

    high = conservative_high_range([fpi, fmu])

    return {
        "fpi": fpi,
        "fmu": fmu,
        **high,
    }


def design_cx_for_high_cutoff(
    target_fh_hz: float,
    rpi_eq_ohm: float,
    cpi_f: float,
    rmu_eq_ohm: float,
    cmu_f: float,
) -> dict:
    """
    Design collector capacitor Cx to reduce high cutoff frequency.

    Conservative design:
        target_fH = fπ || fµ_new

    Rearranged:
        Cx = (1/Rµ) * (1/(2πfH) - RπCπ) - Cµ

    If Cx <= 0, adding a capacitor cannot achieve the requested target.
    """
    if target_fh_hz <= 0:
        raise ValueError("target_fh_hz must be positive.")

    cx = (1.0 / rmu_eq_ohm) * (
        (1.0 / (2.0 * pi * target_fh_hz)) - (rpi_eq_ohm * cpi_f)
    ) - cmu_f

    possible = cx > 0
    cmu_total = cmu_f + cx if possible else cmu_f

    return {
        "Cx": cx if possible else None,
        "possible": possible,
        "Cmu_total": cmu_total,
        "reason": None if possible else "Not possible: required Cx is zero or negative.",
    }


# ---------------------------------------------------------------------------
# Low-frequency capacitor design
# ---------------------------------------------------------------------------

def design_equal_ce_low_caps(
    target_fl_hz: float,
    r11_ohm: float,
    r22_ohm: float,
    ree_ohm: float,
) -> dict:
    """
    CE conservative low cutoff design with:
        C1 = C2 = CE = C

    Formula:
        C = 1 / [2π fL (1/R11 + 1/R22 + 1/REE)]
    """
    if target_fl_hz <= 0:
        raise ValueError("target_fl_hz must be positive.")

    conductance_sum = (1.0 / r11_ohm) + (1.0 / r22_ohm) + (1.0 / ree_ohm)
    c = 1.0 / (2.0 * pi * target_fl_hz * conductance_sum)

    return {
        "C": c,
        "C1": c,
        "C2": c,
        "CE": c,
    }


def design_equal_cc_low_caps(
    target_fl_hz: float,
    r11_ohm: float,
    r22_ohm: float,
) -> dict:
    """
    CC conservative low cutoff design with:
        C1 = C2 = C

    Formula:
        C = 1 / [2π fL (1/R11 + 1/R22)]
    """
    if target_fl_hz <= 0:
        raise ValueError("target_fl_hz must be positive.")

    conductance_sum = (1.0 / r11_ohm) + (1.0 / r22_ohm)
    c = 1.0 / (2.0 * pi * target_fl_hz * conductance_sum)

    return {
        "C": c,
        "C1": c,
        "C2": c,
    }


# ---------------------------------------------------------------------------
# BJT capacitance model
# ---------------------------------------------------------------------------

def calculate_cmu(cjc_f: float, vjc_v: float, vb_v: float, vc_v: float) -> dict:
    """
    BJT collector-base junction capacitance:
        VCB = VC - VB
        Cµ = CJC / (1 + VCB/VJC)^(1/3)

    For normal active NPN operation, VC > VB.
    """
    if cjc_f <= 0:
        raise ValueError("CJC must be positive.")
    if vjc_v <= 0:
        raise ValueError("VJC must be positive.")

    vcb = vc_v - vb_v
    if vcb < 0:
        raise ValueError("VCB is negative. Check VB and VC or transistor polarity.")

    cmu = cjc_f / ((1.0 + vcb / vjc_v) ** (1.0 / 3.0))

    return {
        "VCB": vcb,
        "Cmu": cmu,
    }


def calculate_cpi(
    tau_f_s: float,
    ic_a: float,
    vt_v: float,
    cje_f: float,
    vje_v: float,
    vb_v: float,
    ve_v: float,
) -> dict:
    """
    BJT base-emitter capacitance:
        VBE = VB - VE
        Cπ = τF * IC / VT + CJE / (1 - VBE/VJE)^(1/3)

    Important:
    This formula can become invalid if VBE >= VJE.
    The course slides use it as the small-signal model formula.
    """
    if tau_f_s < 0:
        raise ValueError("tauF cannot be negative.")
    if ic_a < 0:
        raise ValueError("IC cannot be negative.")
    if vt_v <= 0:
        raise ValueError("VT must be positive.")
    if cje_f <= 0:
        raise ValueError("CJE must be positive.")
    if vje_v <= 0:
        raise ValueError("VJE must be positive.")

    vbe = vb_v - ve_v
    denominator = 1.0 - (vbe / vje_v)

    if denominator <= 0:
        raise ValueError("Invalid Cπ calculation: VBE must be less than VJE.")

    diffusion = tau_f_s * ic_a / vt_v
    depletion = cje_f / (denominator ** (1.0 / 3.0))
    cpi = diffusion + depletion

    return {
        "VBE": vbe,
        "Cpi": cpi,
        "Cpi_diffusion": diffusion,
        "Cpi_depletion": depletion,
    }


# ---------------------------------------------------------------------------
# Equivalent high-frequency resistances from CE / CC circuit data
# ---------------------------------------------------------------------------

@dataclass
class CEHighResistanceInputs:
    rs_ohm: float
    rb_ohm: float
    rpi_ohm: float
    rx_ohm: float
    rc_ohm: float
    rl_ohm: float
    beta: float


def ce_high_resistances(inputs: CEHighResistanceInputs) -> dict:
    """
    CE high-frequency equivalent resistances.

    Slide definitions:
        RSB = RS || RB
        RCL = RC || RL
        RXX = rπ + (β + 1)RX

        Rπ = rπ(RSB + RX)/(RSB + RXX)

        Rµ = [RXX(RSB + RCL) + (β + 1)RSB RCL] / (RSB + RXX)
    """
    rsb = parallel(inputs.rs_ohm, inputs.rb_ohm)
    rcl = parallel(inputs.rc_ohm, inputs.rl_ohm)
    rxx = inputs.rpi_ohm + (inputs.beta + 1.0) * inputs.rx_ohm

    rpi_eq = inputs.rpi_ohm * (rsb + inputs.rx_ohm) / (rsb + rxx)

    rmu_eq = (
        rxx * (rsb + rcl)
        + (inputs.beta + 1.0) * rsb * rcl
    ) / (rsb + rxx)

    return {
        "RSB": rsb,
        "RCL": rcl,
        "RXX": rxx,
        "Rpi_eq": rpi_eq,
        "Rmu_eq": rmu_eq,
    }


@dataclass
class CCHighResistanceInputs:
    rs_ohm: float
    rb_ohm: float
    re_ohm: float
    rl_ohm: float
    rpi_ohm: float
    beta: float


def cc_high_resistances(inputs: CCHighResistanceInputs) -> dict:
    """
    CC high-frequency equivalent resistances.

    Slide definitions:
        RSB = RS || RB
        REL = RE || RL

        Rµ = RSB || [rπ + (β + 1)REL]
        Rπ = rπ || [RSB + (β + 1)REL]
    """
    rsb = parallel(inputs.rs_ohm, inputs.rb_ohm)
    rel = parallel(inputs.re_ohm, inputs.rl_ohm)

    rmu_eq = parallel(rsb, inputs.rpi_ohm + (inputs.beta + 1.0) * rel)
    rpi_eq = parallel(inputs.rpi_ohm, rsb + (inputs.beta + 1.0) * rel)

    return {
        "RSB": rsb,
        "REL": rel,
        "Rpi_eq": rpi_eq,
        "Rmu_eq": rmu_eq,
    }


# ---------------------------------------------------------------------------
# Unit conversion helpers for UI/controller use
# ---------------------------------------------------------------------------

def ohm(value: float) -> float:
    return value


def kohm(value: float) -> float:
    return value * 1e3


def mohms(value: float) -> float:
    return value * 1e6


def farad(value: float) -> float:
    return value


def uf(value: float) -> float:
    return value * 1e-6


def nf(value: float) -> float:
    return value * 1e-9


def pf(value: float) -> float:
    return value * 1e-12


def hz(value: float) -> float:
    return value


def khz(value: float) -> float:
    return value * 1e3


def mhz(value: float) -> float:
    return value * 1e6


def ma(value: float) -> float:
    return value * 1e-3


def ua(value: float) -> float:
    return value * 1e-6
