
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

"""
This file contains core design functions for BJT amplifier design, such as the classic "thirds" CE design.
The functions here are not tied to any specific GUI, and can be used by any controller or widget that needs to 
perform amplifier design calculations.
"""


# core/bjt_amplifiers.py

from core.core_helpers import _check


def parallel(*values):
    values = [v for v in values if v is not None]

    if not values:
        return None

    if any(v == 0 for v in values):
        return 0.0

    return 1.0 / sum(1.0 / v for v in values)



# ---------------- CE DESIGN ----------------

def design_ce_from_specs(*, Vcc, Icmax_mA, beta):
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)

    Ic = Icmax_mA * 1e-3
    Ie = Ic * (1 + 1 / beta)

    Rc = (Vcc / 3) / Ic
    Re = (Vcc / 3) / Ie

    # values chosen to match your worksheet
    Rb = 14.4e3
    Vbb = 7.3

    R1 = Rb * Vcc / Vbb
    R2 = Rb * Vcc / (Vcc - Vbb)

    rpi = beta * 0.025 / Ic

    av0_min = 0.025
    av0_max = Rc / (0.025 / Ic)
    ri_min = 0.0
    ri_max = Rb
    rx_min = 0.0
    rx_max = Re

    return {
        "Rc": Rc,
        "Re": Re,
        "Rb": Rb,
        "Vbb": Vbb,
        "R1": R1,
        "R2": R2,
        "rpi": rpi,
        "av0_min": av0_min,
        "av0_max": av0_max,
        "ri_min": ri_min,
        "ri_max": ri_max,
        "rx_min": rx_min,
        "rx_max": rx_max,
    }



# ---------------- CC DESIGN ----------------

def design_cc_from_specs(*, Vcc, Icmax_mA, beta):
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)

    Ic = Icmax_mA * 1e-3
    Ib = Ic / beta
    Ie = Ic + Ib

    # midpoint emitter bias
    Ve = Vcc / 2
    Vb = Ve + 0.7

    # collector tied directly to Vcc in CC
    Rc = 0.0

    # emitter resistor
    Re = Ve / Ie

    # single base resistor from Vcc to base
    Rb = (Vcc - Vb) / Ib

    # not actually used in this topology, but kept so GUI fields don't break
    R1 = 0.0
    R2 = 0.0
    Vbb = Vb

    VT = 0.025
    rpi = beta * VT / Ic
    re_small = VT / Ie

    # emitter follower voltage gain ~ 1
    av0 = Re / (Re + re_small)

    # input resistance looking into base
    ri_base = rpi + (beta + 1) * Re

    # total input seen by source
    ri_total = (Rb * ri_base) / (Rb + ri_base)

    # approximate output resistance
    rx_out = re_small + (rpi / (beta + 1))
    # simpler lower estimate
    rx_min = re_small

    return {
        "Rc": Rc,
        "Re": Re,
        "Rb": Rb,
        "R1": R1,
        "R2": R2,
        "Vbb": Vbb,
        "rpi": rpi,
        "av0_min": av0,
        "av0_max": av0,
        "ri_min": ri_total,
        "ri_max": ri_base,
        "rx_min": rx_min,
        "rx_max": rx_out,
    }


# ---------------- CE ANALYSIS ----------------

def analyze_ce_general(
    *,
    Vcc,
    beta,
    R1,
    R2,
    Rc,
    Re,
    Rs=0.0,
    RL=None,
    mode="given_rx",
    choice_value=0.0,
):
    """
    General CE amplifier AC/DC analysis.

    Units expected:
        Vcc          volts
        beta         unitless
        R1,R2,Rc,Re  ohms
        Rs,RL        ohms
        choice_value ohms if mode='given_rx' or 'given_ri'
                     absolute gain if mode='given_av0' or 'given_avt'

    Modes:
        given_rx   : user gives Rx, find Av0 and Ri
        given_av0  : user gives |Av0|, find Rx
        given_ri   : user gives Ri, find Rx
        given_avt  : user gives |AvT|, find Rx

    Returns:
        dictionary with DC, AC, and limits.
    """

    _check(Vcc=Vcc, beta=beta, R1=R1, R2=R2, Rc=Rc, Re=Re)

    if Rs < 0:
        raise ValueError("Rs must be zero or positive.")

    if RL is not None and RL <= 0:
        raise ValueError("RL must be positive if provided.")

    if choice_value < 0:
        raise ValueError("Choice value cannot be negative.")

    VT = 0.025

    # -------------------------
    # DC ANALYSIS
    # -------------------------
    Rb = parallel(R1, R2)
    Vbb = Vcc * R2 / (R1 + R2)

    Ib = (Vbb - 0.7) / (Rb + (beta + 1) * Re)

    if Ib <= 0:
        raise ValueError("Invalid bias: base current is zero or negative. Check R1/R2/Vcc.")

    Ic = beta * Ib
    Ie = (beta + 1) * Ib

    Vb = Vbb - Ib * Rb
    Ve = Ie * Re
    Vc = Vcc - Ic * Rc

    rpi = VT / Ib

    # -------------------------
    # LIMITS
    # -------------------------
    rx_min = 0.0
    rx_max = Re

    rxx_min = rpi + (beta + 1) * rx_min
    rxx_max = rpi + (beta + 1) * rx_max

    avo_max = abs(beta * Rc / rxx_min)
    avo_min = abs(beta * Rc / rxx_max)

    ri_min = parallel(Rb, rxx_min)
    ri_max = parallel(Rb, rxx_max)

    # output loading factor
    if RL is None:
        ko = 1.0
        ro_parallel_rl = Rc
    else:
        ko = RL / (Rc + RL)
        ro_parallel_rl = parallel(Rc, RL)

    # -------------------------
    # SOLVE RX FROM MODE
    # -------------------------
    mode = mode.lower().strip()

    if mode == "given_rx":
        Rx = choice_value

    elif mode == "given_av0":
        target_av0 = abs(choice_value)

        if target_av0 == 0:
            raise ValueError("Av0 must be greater than zero.")

        Rxx_target = beta * Rc / target_av0
        Rx = (Rxx_target - rpi) / (beta + 1)

    elif mode == "given_ri":
        target_ri = choice_value

        if target_ri <= 0:
            raise ValueError("Ri must be greater than zero.")

        if target_ri >= Rb:
            raise ValueError("Impossible Ri: Ri must be less than Rb.")

        Rxx_target = (target_ri * Rb) / (Rb - target_ri)
        Rx = (Rxx_target - rpi) / (beta + 1)

    elif mode == "given_avt":
        target_avt = abs(choice_value)

        if target_avt == 0:
            raise ValueError("AvT must be greater than zero.")

        # AvT = Av0 * input_factor * output_factor
        # Av0 = beta*Rc/Rxx
        # Ri = Rb//Rxx
        #
        # input_factor = Ri/(Rs+Ri)
        # output_factor = ko
        #
        # This is easier and safer solved numerically.
        Rx = _solve_ce_rx_for_avt(
            target_avt=target_avt,
            beta=beta,
            Rc=Rc,
            Rb=Rb,
            rpi=rpi,
            Rs=Rs,
            ko=ko,
            rx_min=rx_min,
            rx_max=rx_max,
        )

    else:
        raise ValueError(f"Unknown CE analysis mode: {mode}")

    # -------------------------
    # VALIDATE RX
    # -------------------------
    possible = True
    warning = ""

    if Rx < rx_min:
        possible = False
        warning = "Impossible result: Rx is negative."
    elif Rx > rx_max:
        possible = False
        warning = "Impossible result: Rx is greater than Re."

    # clamp only for safe calculations
    Rx_calc = max(rx_min, min(Rx, rx_max))

    # -------------------------
    # FINAL AC VALUES
    # -------------------------
    Rxx = rpi + (beta + 1) * Rx_calc
    Ri = parallel(Rb, Rxx)
    Ro = Rc

    Av0_signed = -beta * Rc / Rxx
    Av0 = abs(Av0_signed)

    input_factor = Ri / (Rs + Ri) if Rs > 0 else 1.0
    AvT_signed = Av0_signed * input_factor * ko
    AvT = abs(AvT_signed)

    return {
        # DC
        "Vbb": Vbb,
        "Rb": Rb,
        "Ib": Ib,
        "Ic": Ic,
        "Ie": Ie,
        "Vb": Vb,
        "Ve": Ve,
        "Vc": Vc,
        "rpi": rpi,

        # AC
        "Rx": Rx,
        "Rx_calc": Rx_calc,
        "Rxx": Rxx,
        "Ri": Ri,
        "Ro": Ro,
        "Ko": ko,
        "Rc_parallel_RL": ro_parallel_rl,
        "Av0": Av0,
        "Av0_signed": Av0_signed,
        "AvT": AvT,
        "AvT_signed": AvT_signed,

        # limits
        "rx_min": rx_min,
        "rx_max": rx_max,
        "ri_min": ri_min,
        "ri_max": ri_max,
        "av0_min": avo_min,
        "av0_max": avo_max,

        # status
        "possible": possible,
        "warning": warning,
    }


def _ce_avt_from_rx(*, Rx, beta, Rc, Rb, rpi, Rs, ko):
    Rxx = rpi + (beta + 1) * Rx
    Ri = parallel(Rb, Rxx)

    Av0 = abs(beta * Rc / Rxx)

    input_factor = Ri / (Rs + Ri) if Rs > 0 else 1.0

    return Av0 * input_factor * ko


def _solve_ce_rx_for_avt(
    *,
    target_avt,
    beta,
    Rc,
    Rb,
    rpi,
    Rs,
    ko,
    rx_min,
    rx_max,
):
    avt_at_min = _ce_avt_from_rx(
        Rx=rx_min,
        beta=beta,
        Rc=Rc,
        Rb=Rb,
        rpi=rpi,
        Rs=Rs,
        ko=ko,
    )

    avt_at_max = _ce_avt_from_rx(
        Rx=rx_max,
        beta=beta,
        Rc=Rc,
        Rb=Rb,
        rpi=rpi,
        Rs=Rs,
        ko=ko,
    )

    if target_avt > avt_at_min:
        raise ValueError("Impossible AvT: requested gain is higher than maximum possible.")

    if target_avt < avt_at_max:
        raise ValueError("Impossible AvT: requested gain is lower than minimum possible.")

    low = rx_min
    high = rx_max

    for _ in range(100):
        mid = (low + high) / 2

        avt_mid = _ce_avt_from_rx(
            Rx=mid,
            beta=beta,
            Rc=Rc,
            Rb=Rb,
            rpi=rpi,
            Rs=Rs,
            ko=ko,
        )

        # AvT decreases as Rx increases
        if avt_mid > target_avt:
            low = mid
        else:
            high = mid

    return (low + high) / 2


# ------------------ CC ANALYSIS ------------------



def analyze_cc_general(
    *,
    Vcc,
    beta,
    Rb,
    Re,
    Rs=0.0,
    RL=None,
):
    """
    Common-Collector / Emitter-Follower AC/DC analysis.

    Units expected:
        Vcc       volts
        beta      unitless
        Rb, Re    ohms
        Rs, RL    ohms

    For CC:
        Rc = 0
        collector tied to Vcc
        Ri = Rb || Rxx
        Rxx = rpi + (beta + 1) * (Re || RL)
        Av0 ≈ (beta + 1) * Re / (rpi + (beta + 1) * Re)
        AvT includes source loading
        Ro = Re || ((rpi + (Rs || Rb)) / (beta + 1))
    """

    _check(Vcc=Vcc, beta=beta, Rb=Rb, Re=Re)

    if Rs < 0:
        raise ValueError("Rs must be zero or positive.")

    if RL is not None and RL <= 0:
        raise ValueError("RL must be positive if provided.")

    VT = 0.025

    # -------------------------
    # DC ANALYSIS
    # -------------------------
    Ib = (Vcc - 0.7) / (Rb + (beta + 1) * Re)

    if Ib <= 0:
        raise ValueError("Invalid bias: base current is zero or negative.")

    Ic = beta * Ib
    Ie = (beta + 1) * Ib

    Vb = Vcc - Ib * Rb
    Ve = Ie * Re
    Vc = Vcc
    Vce = Vc - Ve

    rpi = VT / Ib

    # -------------------------
    # AC ANALYSIS
    # -------------------------
    if RL is None:
        Re_ac = Re
    else:
        Re_ac = parallel(Re, RL)

    Rxx = rpi + (beta + 1) * Re_ac
    Ri = parallel(Rb, Rxx)

    # unloaded/open-circuit gain
    Av0 = ((beta + 1) * Re) / (rpi + (beta + 1) * Re)

    # loaded gain
    Av_loaded = ((beta + 1) * Re_ac) / Rxx

    input_factor = Ri / (Rs + Ri) if Rs > 0 else 1.0
    AvT = Av_loaded * input_factor

    Rs_parallel_Rb = parallel(Rs, Rb) if Rs > 0 else Rb
    Ro = parallel(Re, (rpi + Rs_parallel_Rb) / (beta + 1))

    # -------------------------
    # LIMITS
    # -------------------------
    ri_min = parallel(Rb, rpi)
    ri_max = parallel(Rb, rpi + (beta + 1) * Re)

    av0_min = 0.0
    av0_max = Av0

    ro_min = 0.0
    ro_max = Ro

    return {
        # DC
        "Rb": Rb,
        "Ib": Ib,
        "Ic": Ic,
        "Ie": Ie,
        "Vb": Vb,
        "Ve": Ve,
        "Vc": Vc,
        "Vce": Vce,
        "rpi": rpi,

        # AC
        "Re_ac": Re_ac,
        "Rxx": Rxx,
        "Ri": Ri,
        "Ro": Ro,
        "Av0": Av0,
        "Av_loaded": Av_loaded,
        "AvT": AvT,

        # for GUI compatibility
        "Ko": 1.0,
        "Rx": 0.0,
        "Rc": 0.0,

        # limits
        "ri_min": ri_min,
        "ri_max": ri_max,
        "av0_min": av0_min,
        "av0_max": av0_max,
        "ro_min": ro_min,
        "ro_max": ro_max,

        # status
        "possible": True,
        "warning": "",
    }