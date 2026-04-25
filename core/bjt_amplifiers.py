import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

"""
Core BJT amplifier design/analysis calculations.

Conventions:
- Resistances passed into core functions are in ohms.
- Voltages are in volts.
- Currents are in amps unless the argument name says mA.
- GUI should convert kΩ/mA/etc. before calling these functions.
- Missing optional values return None for dependent outputs.
"""

from core.core_helpers import _check

VT_DEFAULT = 0.025
VBE_DEFAULT = 0.7


def parallel(*values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    if any(v == 0 for v in values):
        return 0.0
    return 1.0 / sum(1.0 / v for v in values)


def _require_positive_optional(name, value):
    if value is not None and value <= 0:
        raise ValueError(f"{name} must be positive if provided.")


def _require_nonnegative_optional(name, value):
    if value is not None and value < 0:
        raise ValueError(f"{name} must be zero or positive if provided.")


# ---------------- CE DESIGN ----------------

def design_ce_from_specs(*, Vcc, Icmax_mA, beta, Vs=None, VT=VT_DEFAULT, VBE=VBE_DEFAULT):
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _require_nonnegative_optional("Vs", Vs)

    Ic = Icmax_mA * 1e-3
    Ib = Ic / beta
    Ie = Ic + Ib

    # Classic thirds design: about 1/3 Vcc across RC, 1/3 across RE, 1/3 across VCE.
    Rc = (Vcc / 3.0) / Ic
    Re = (Vcc / 3.0) / Ie

    Ve = Ie * Re
    Vb = Ve + VBE

    # Thevenin resistance of the divider. Smaller Rb gives better beta stability.
    # Rule of thumb: divider current around 10x base current -> Rb ~= beta*Re/10.
    Rb = beta * Rc / 10.0

    # The Thevenin source must overcome the base-current drop across Rb.
    Vbb = Vb + Ib * Rb

    if not (0 < Vbb < Vcc):
        raise ValueError("Invalid CE design bias: calculated Vbb must be between 0 and Vcc.")

    # From: Vbb = Vcc*R2/(R1+R2), Rb = R1 || R2
    R1 = Rb * Vcc / Vbb
    R2 = Rb * Vcc / (Vcc - Vbb)

    rpi = beta * VT / Ic

    rx_min = 0.0
    rx_max = Re

    rxx_min = rpi + (beta + 1) * rx_min
    rxx_max = rpi + (beta + 1) * rx_max

    av0_max = abs(beta * Rc / rxx_min)
    av0_min = abs(beta * Rc / rxx_max)

    ri_min = parallel(Rb, rxx_min)
    ri_max = parallel(Rb, rxx_max)

    vo_min = av0_min * Vs if Vs is not None else None
    vo_max = av0_max * Vs if Vs is not None else None

    return {
        "Rc": Rc,
        "Re": Re,
        "Rb": Rb,
        "R1": R1,
        "R2": R2,
        "Vbb": Vbb,
        "Vb": Vb,
        "Ve": Ve,
        "rpi": rpi,
        "rx_min": rx_min,
        "rx_max": rx_max,
        "ri_min": ri_min,
        "ri_max": ri_max,
        "av0_min": av0_min,
        "av0_max": av0_max,
        "vo_min": vo_min,
        "vo_max": vo_max,
    }


# ---------------- CC DESIGN ----------------

def design_cc_from_specs(*, Vcc, Icmax_mA, beta, Vs=None, VT=VT_DEFAULT, VBE=VBE_DEFAULT):
    _check(Vcc=Vcc, Icmax_mA=Icmax_mA, beta=beta)
    _require_nonnegative_optional("Vs", Vs)

    Ic = Icmax_mA * 1e-3
    Ib = Ic / beta
    Ie = Ic + Ib

    # Emitter follower midpoint design.
    Ve = Vcc / 2.0
    Vb = Ve + VBE

    if Vb >= Vcc:
        raise ValueError("Invalid CC design bias: calculated base voltage is at/above Vcc.")

    Rc = 0.0
    Re = Ve / Ie
    Rb = (Vcc - Vb) / Ib

    # Kept for GUI compatibility. CC uses a single base resistor, not a divider.
    R1 = 0.0
    R2 = 0.0
    Vbb = Vb

    rpi = beta * VT / Ic

    av0_unloaded = ((beta + 1) * Re) / (rpi + (beta + 1) * Re)
    rxx_unloaded = rpi + (beta + 1) * Re
    ri_unloaded = parallel(Rb, rxx_unloaded)

    vo_min = 0.0 if Vs is not None else None
    vo_max = av0_unloaded * Vs if Vs is not None else None

    return {
        "Rc": Rc,
        "Re": Re,
        "Rb": Rb,
        "R1": R1,
        "R2": R2,
        "Vbb": Vbb,
        "Vb": Vb,
        "Ve": Ve,
        "rpi": rpi,
        "av0_min": 0.0,
        "av0_max": av0_unloaded,
        "ri_min": parallel(Rb, rpi),
        "ri_max": ri_unloaded,
        "rx_min": 0.0,
        "rx_max": Re,
        "vo_min": vo_min,
        "vo_max": vo_max,
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
    Vs=None,
    mode="given_rx",
    choice_value=0.0,
    VT=VT_DEFAULT,
    VBE=VBE_DEFAULT,
):
    _check(Vcc=Vcc, beta=beta, R1=R1, R2=R2, Rc=Rc, Re=Re)
    if Rs < 0:
        raise ValueError("Rs must be zero or positive.")
    _require_positive_optional("RL", RL)
    _require_nonnegative_optional("Vs", Vs)
    if choice_value < 0:
        raise ValueError("Choice value cannot be negative.")

    Rb = parallel(R1, R2)
    Vbb = Vcc * R2 / (R1 + R2)

    Ib = (Vbb - VBE) / (Rb + (beta + 1) * Re)
    if Ib <= 0:
        raise ValueError("Invalid bias: base current is zero or negative. Check R1/R2/Vcc.")

    Ic = beta * Ib
    Ie = (beta + 1) * Ib

    Ve = Ie * Re
    Vb = Ve + VBE
    Vc = Vcc - Ic * Rc
    Vce = Vc - Ve

    rpi = beta * VT / Ic

    rx_min = 0.0
    rx_max = Re

    rxx_min = rpi + (beta + 1) * rx_min
    rxx_max = rpi + (beta + 1) * rx_max

    av0_max = abs(beta * Rc / rxx_min)
    av0_min = abs(beta * Rc / rxx_max)

    ri_min = parallel(Rb, rxx_min)
    ri_max = parallel(Rb, rxx_max)

    ko = RL / (Rc + RL) if RL is not None else None
    rc_parallel_rl = parallel(Rc, RL) if RL is not None else None

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
        if RL is None:
            raise ValueError("RL is required when solving from AvT.")
        target_avt = abs(choice_value)
        if target_avt == 0:
            raise ValueError("AvT must be greater than zero.")
        if rx_max == rx_min:
            raise ValueError("Cannot solve AvT when Re is zero.")
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

    possible = True
    warning = ""
    if Rx < rx_min:
        possible = False
        warning = "Impossible result: Rx is negative."
    elif Rx > rx_max:
        possible = False
        warning = "Impossible result: Rx is greater than Re."

    Rx_calc = max(rx_min, min(Rx, rx_max))

    Rxx = rpi + (beta + 1) * Rx_calc
    Ri = parallel(Rb, Rxx)
    Ro = Rc

    Av0_signed = -beta * Rc / Rxx
    Av0 = abs(Av0_signed)

    input_factor = Ri / (Rs + Ri) if Rs > 0 else 1.0

    if RL is None:
        AvT_signed = None
        AvT = None
    else:
        AvT_signed = Av0_signed * ko * input_factor
        AvT = abs(AvT_signed)

    Vo = AvT * Vs if (Vs is not None and AvT is not None) else None

    if RL is None:
        avt_min = avt_max = vo_min = vo_max = None
    else:
        avt_at_min = _ce_avt_from_rx(Rx=rx_min, beta=beta, Rc=Rc, Rb=Rb, rpi=rpi, Rs=Rs, ko=ko)
        avt_at_max = _ce_avt_from_rx(Rx=rx_max, beta=beta, Rc=Rc, Rb=Rb, rpi=rpi, Rs=Rs, ko=ko)
        avt_min = min(avt_at_min, avt_at_max)
        avt_max = max(avt_at_min, avt_at_max)
        vo_min = avt_min * Vs if Vs is not None else None
        vo_max = avt_max * Vs if Vs is not None else None

    return {
        "Vbb": Vbb,
        "Rb": Rb,
        "Ib": Ib,
        "Ic": Ic,
        "Ie": Ie,
        "Vb": Vb,
        "Ve": Ve,
        "Vc": Vc,
        "Vce": Vce,
        "rpi": rpi,
        "Rx": Rx,
        "Rx_calc": Rx_calc,
        "Rxx": Rxx,
        "Ri": Ri,
        "Ro": Ro,
        "Ko": ko,
        "Rc_parallel_RL": rc_parallel_rl,
        "Av0": Av0,
        "Av0_signed": Av0_signed,
        "AvT": AvT,
        "AvT_signed": AvT_signed,
        "Vo": Vo,
        "input_factor": input_factor,
        "rx_min": rx_min,
        "rx_max": rx_max,
        "ri_min": ri_min,
        "ri_max": ri_max,
        "av0_min": av0_min,
        "av0_max": av0_max,
        "avt_min": avt_min,
        "avt_max": avt_max,
        "vo_min": vo_min,
        "vo_max": vo_max,
        "possible": possible,
        "warning": warning,
    }


def _ce_avt_from_rx(*, Rx, beta, Rc, Rb, rpi, Rs, ko):
    Rxx = rpi + (beta + 1) * Rx
    Ri = parallel(Rb, Rxx)
    Av0 = abs(beta * Rc / Rxx)
    input_factor = Ri / (Rs + Ri) if Rs > 0 else 1.0
    return Av0 * ko * input_factor


def _solve_ce_rx_for_avt(*, target_avt, beta, Rc, Rb, rpi, Rs, ko, rx_min, rx_max):
    avt_at_min = _ce_avt_from_rx(Rx=rx_min, beta=beta, Rc=Rc, Rb=Rb, rpi=rpi, Rs=Rs, ko=ko)
    avt_at_max = _ce_avt_from_rx(Rx=rx_max, beta=beta, Rc=Rc, Rb=Rb, rpi=rpi, Rs=Rs, ko=ko)

    high_gain = max(avt_at_min, avt_at_max)
    low_gain = min(avt_at_min, avt_at_max)

    if target_avt > high_gain:
        raise ValueError("Impossible AvT: requested gain is higher than maximum possible.")
    if target_avt < low_gain:
        raise ValueError("Impossible AvT: requested gain is lower than minimum possible.")

    low = rx_min
    high = rx_max
    for _ in range(100):
        mid = (low + high) / 2.0
        avt_mid = _ce_avt_from_rx(Rx=mid, beta=beta, Rc=Rc, Rb=Rb, rpi=rpi, Rs=Rs, ko=ko)
        if avt_mid > target_avt:
            low = mid
        else:
            high = mid
    return (low + high) / 2.0


# ---------------- CC ANALYSIS ----------------

def analyze_cc_general(*, Vcc, beta, Rb, Re, Rs=None, RL=None, Vs=None, VT=VT_DEFAULT, VBE=VBE_DEFAULT):
    """
    Common-Collector / Emitter-Follower AC/DC analysis.

    Required:
        Vcc, beta, Rb, Re

    Optional:
        RL: load resistance. Needed for loaded Rxx, Ri, Av0.
        Rs: source resistance. Needed for Ro, Ko, AvT.
        Vs: source signal voltage. Needed for Vo.

    Convention:
        None means "not provided yet", so dependent results return None.
    """

    _check(Vcc=Vcc, beta=beta, Rb=Rb, Re=Re)
    _require_nonnegative_optional("Rs", Rs)
    _require_positive_optional("RL", RL)
    _require_nonnegative_optional("Vs", Vs)

    # -------------------------
    # DC ANALYSIS
    # -------------------------
    Ib = (Vcc - VBE) / (Rb + (beta + 1) * Re)
    if Ib <= 0:
        raise ValueError("Invalid bias: base current is zero or negative.")

    Ic = beta * Ib
    Ie = (beta + 1) * Ib

    Vb = Vcc - Ib * Rb
    Ve = Ie * Re
    Vc = Vcc
    Vce = Vc - Ve

    rpi = beta * VT / Ic

    # Open-circuit emitter follower gain, useful as a reference only.
    Rxx_unloaded = rpi + (beta + 1) * Re
    Av0_unloaded = ((beta + 1) * Re) / Rxx_unloaded
    Ri_unloaded = parallel(Rb, Rxx_unloaded)

    # -------------------------
    # AC VALUES THAT NEED RL
    # -------------------------
    if RL is None:
        Re_ac = None
        Rxx = None
        Ri = None
        Av0 = None
        Av_loaded = None
    else:
        Re_ac = parallel(Re, RL)
        Rxx = rpi + (beta + 1) * Re_ac
        Ri = parallel(Rb, Rxx)

        # Internal loaded gain from base to emitter/load.
        # This depends on RL because the emitter AC resistance is Re || RL.
        Av0 = ((beta + 1) * Re_ac) / Rxx
        Av_loaded = Av0

    # -------------------------
    # VALUES THAT NEED RS
    # -------------------------
    # Rs=None  -> user has not provided it yet, skip all dependent outputs
    # Rs=0     -> ideal voltage source, valid: Rs||Rb=0, input_factor=1
    if Rs is None:
        Rs_parallel_Rb = None
        Ro = None
    else:
        Rs_parallel_Rb = 0.0 if Rs == 0 else parallel(Rs, Rb)
        Ro = parallel(Re, (rpi + Rs_parallel_Rb) / (beta + 1))

    # Ko is the output voltage divider: RL / (RL + Ro).
    if RL is None or Ro is None:
        Ko = None
    else:
        Ko = RL / (RL + Ro)

    # AvT needs both RL (for Av0, Ri) and Rs (for input_factor, Ko).
    if Ri is None or Rs is None or Ko is None:
        input_factor = None
        AvT = None
    else:
        # Rs=0: ideal source, full input voltage reaches base
        input_factor = 1.0 if Rs == 0 else Ri / (Rs + Ri)
        AvT = Av0 * input_factor * Ko   # Av0 already accounts for Re||RL loading

    Vo = AvT * Vs if (Vs is not None and AvT is not None) else None

    # -------------------------
    # LIMITS
    # -------------------------
    # These are single-point display values once the required optional values exist.
    # They are None until the required dependencies are provided by the GUI.
    if RL is None:
        ri_min = ri_max = av0_min = av0_max = None
    else:
        ri_min = ri_max = Ri
        av0_min = av0_max = Av0

    if AvT is None:
        avt_min = avt_max = None
        vo_min = vo_max = None
    else:
        avt_min = avt_max = AvT
        vo_min = vo_max = AvT * Vs if Vs is not None else None

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
        "Av0_unloaded": Av0_unloaded,
        "Av_loaded": Av_loaded,
        "AvT": AvT,
        "Vo": Vo,
        "Ko": Ko,
        "input_factor": input_factor,
        "Rs_parallel_Rb": Rs_parallel_Rb,

        # GUI compatibility
        "Rx": None,
        "Rc": 0.0,

        # Limits
        "ri_min": ri_min,
        "ri_max": ri_max,
        "ri_unloaded": Ri_unloaded,
        "av0_min": av0_min,
        "av0_max": av0_max,
        "av0_unloaded": Av0_unloaded,
        "avt_min": avt_min,
        "avt_max": avt_max,
        "vo_min": vo_min,
        "vo_max": vo_max,
        "ro_min": Ro,
        "ro_max": Ro,

        # Status
        "possible": True,
        "warning": "",
    }
