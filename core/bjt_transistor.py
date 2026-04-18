"""
BJT DC Bias Solver -> NPN only
Topologies: fixed_bias, emitter_bias, voltage_divider_bias, collector_feedback_bias
All values in SI units: Ohms, Volts, Amperes.
GUI-ready: all errors raised as ValueError, results are plain dicts, use fmt() for display.
"""


class BJT:
    """NPN BJT parameters."""
    def __init__(self, beta=100, vbe=0.7, vce_sat=0.2, vbe_sat=0.8):
        if beta <= 0:
            raise ValueError("beta must be positive.")
        self.beta = beta
        self.vbe = vbe
        self.vce_sat = vce_sat
        self.vbe_sat = vbe_sat


def _check(**kwargs):
    """Raise ValueError for any zero or negative resistor/supply value."""
    for name, value in kwargs.items():
        if value <= 0:
            raise ValueError(f"{name} must be a positive number, got {value}.")


def _result(mode, ib, ic, ie, vb, vc, ve):
    """Pack node voltages and branch currents into a result dict."""
    d = dict(mode=mode, Ib=ib, Ic=ic, Ie=ie, Vb=vb, Vc=vc, Ve=ve, Vce=vc-ve, Vbe=vb-ve)
    if mode == "saturation" and ib > 0:
        d["beta_forced"] = ic / ib   # should be < beta to confirm saturation
    return d


def fmt(value, unit):
    """
    Format a value into a readable string with auto-scaled prefix.
    Use this in your GUI to display results cleanly.

    fmt(0.00115, "A")  →  "1.1500 mA"
    fmt(0.0000023, "A")  →  "2.3000 µA"
    fmt(6.35, "V")  →  "6.3500 V"
    """
    if unit == "A":
        if abs(value) >= 1e-3:
            return f"{value*1e3:.4f} mA"
        else:
            return f"{value*1e6:.4f} µA"
    if unit == "V":
        return f"{value:.4f} V"
    return f"{value:.4f} {unit}"


#  1. FIXED BIAS  (emitter grounded, base driven via Rb from Vb) 

def solve_fixed_bias(*, bjt, Vb, Vcc, Rb, Rc):
    _check(Rb=Rb, Rc=Rc, Vcc=Vcc)

    if Vb < bjt.vbe:                             # cutoff: junction not forward biased
        return _result("cutoff", 0, 0, 0, 0, Vcc, 0)

    ib = (Vb - bjt.vbe) / Rb                     # KVL base loop
    ic = bjt.beta * ib
    vc = Vcc - ic * Rc

    if vc > bjt.vce_sat:                          # active region
        return _result("active", ib, ic, ib+ic, bjt.vbe, vc, 0)

    # saturation: Vce and Vbe clamp, solve independently from each loop
    ib = (Vb - bjt.vbe_sat) / Rb
    ic = (Vcc - bjt.vce_sat) / Rc
    return _result("saturation", ib, ic, ib+ic, bjt.vbe_sat, bjt.vce_sat, 0)


#  2. EMITTER BIAS  (emitter resistor Re, optional negative supply Vee) 

def solve_emitter_bias(*, bjt, Vb, Vcc, Rb, Rc, Re, Vee=0.0):
    _check(Rb=Rb, Rc=Rc, Re=Re, Vcc=Vcc)

    if Vb < Vee + bjt.vbe:                        # cutoff
        return _result("cutoff", 0, 0, 0, 0, Vcc, 0)

    # active: KVL base loop with emitter degeneration  Ib = (Vb-Vbe-Vee)/(Rb+(β+1)Re)
    ib = (Vb - bjt.vbe - Vee) / (Rb + (bjt.beta + 1) * Re)
    ic = bjt.beta * ib
    ie = ib + ic
    ve = Vee + ie * Re
    vc = Vcc - ic * Rc

    if vc - ve > bjt.vce_sat:                     # active confirmed
        return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve)

    # saturation: KCL at emitter node, one unknown (Ve), solve A·Ve = B
    A = 1/Re + 1/Rb + 1/Rc
    B = Vee/Re + (Vb - bjt.vbe_sat)/Rb + (Vcc - bjt.vce_sat)/Rc
    ve = B / A
    vb, vc = ve + bjt.vbe_sat, ve + bjt.vce_sat
    ib = (Vb  - vb) / Rb
    ic = (Vcc - vc) / Rc
    ie = (ve  - Vee) / Re
    return _result("saturation", ib, ic, ie, vb, vc, ve)


#  3. VOLTAGE DIVIDER BIAS  (R1 from Vcc, R2 to GND, Re on emitter) 

def solve_voltage_divider_bias(*, bjt, Vcc, R1, R2, Rc, Re):
    _check(R1=R1, R2=R2, Rc=Rc, Re=Re, Vcc=Vcc)

    vth = Vcc * R2 / (R1 + R2)                   # Thevenin base voltage
    rth = R1 * R2 / (R1 + R2)                    # Thevenin resistance

    if vth < bjt.vbe:                             # cutoff
        return _result("cutoff", 0, 0, 0, 0, Vcc, 0)

    # active: standard emitter-degeneration formula using Thevenin equivalent
    ib = (vth - bjt.vbe) / (rth + (bjt.beta + 1) * Re)
    ic = bjt.beta * ib
    ie = ib + ic
    ve = ie * Re
    vc = Vcc - ic * Rc

    if vc - ve > bjt.vce_sat:                     # active confirmed
        return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve)

    # saturation: KCL at emitter, solve A·Ve = B (uses full R1/R2, not Thevenin)
    A = 1/Re + 1/R1 + 1/R2 + 1/Rc
    B = (Vcc - bjt.vbe_sat)/R1 - bjt.vbe_sat/R2 + (Vcc - bjt.vce_sat)/Rc
    ve = B / A
    vb, vc = ve + bjt.vbe_sat, ve + bjt.vce_sat
    ib = (Vcc - vb)/R1 - vb/R2                   # KCL at base node
    ic = (Vcc - vc) / Rc
    ie = ve / Re
    return _result("saturation", ib, ic, ie, vb, vc, ve)


#  4. COLLECTOR-FEEDBACK BIAS  (Rb from collector to base, emitter grounded) 

def solve_collector_feedback_bias(*, bjt, Vcc, Rb, Rc):
    _check(Rb=Rb, Rc=Rc, Vcc=Vcc)

    if Vcc < bjt.vbe:                             # cutoff
        return _result("cutoff", 0, 0, 0, 0, Vcc, 0)

    # active: KVL  Vcc - Ic·Rc - Ib·Rb - Vbe = 0,  Ic = β·Ib
    ib = (Vcc - bjt.vbe) / (Rb + bjt.beta * Rc)
    ic = bjt.beta * ib
    vc = Vcc - ic * Rc

    if vc > bjt.vce_sat:                          # active confirmed
        return _result("active", ib, ic, ib+ic, bjt.vbe, vc, 0)

    # saturation: KCL at collector node  (Vcc-Vc)/Rc = Ic + (Vb-Vc)/Rb
    vb, vc = bjt.vbe_sat, bjt.vce_sat
    ic = (Vcc - vc)/Rc - (vb - vc)/Rb
    ib = (vb - vc) / Rb
    ie = ib + ic
    return _result("saturation", ib, ic, ie, vb, vc, 0)


#  Dispatcher 

SOLVERS = {
    "fixed_bias":             solve_fixed_bias,
    "emitter_bias":           solve_emitter_bias,
    "voltage_divider_bias":   solve_voltage_divider_bias,
    "collector_feedback_bias":solve_collector_feedback_bias,
}

def solve_bjt(*, topology, bjt, **kwargs):
    if topology not in SOLVERS:
        raise ValueError(f"Unknown topology '{topology}'. Options: {list(SOLVERS)}")
    return SOLVERS[topology](bjt=bjt, **kwargs)


#  Pretty printer (terminal use) 

def print_result(label, r):
    print(f"\n{''*44}")
    print(f"  {label}  [{r['mode'].upper()}]")
    print(f"{''*44}")
    print(f"  Ib = {fmt(r['Ib'],'A'):>12}    Vb  = {fmt(r['Vb'],'V')}")
    print(f"  Ic = {fmt(r['Ic'],'A'):>12}    Vc  = {fmt(r['Vc'],'V')}")
    print(f"  Ie = {fmt(r['Ie'],'A'):>12}    Ve  = {fmt(r['Ve'],'V')}")
    print(f"  {'':12}         Vce = {fmt(r['Vce'],'V')}")
    if "beta_forced" in r:
        print(f"  beta_forced = {r['beta_forced']:.2f}  (< β confirms saturation)")


#  Test cases 

if __name__ == "__main__":
    bjt = BJT(beta=100)

    print_result("Fixed Bias -> Active",
        solve_bjt(topology="fixed_bias", bjt=bjt, Vb=3, Vcc=12, Rb=200_000, Rc=2_000))

    print_result("Fixed Bias -> Saturation",
        solve_bjt(topology="fixed_bias", bjt=bjt, Vb=3, Vcc=12, Rb=5_000, Rc=2_000))

    print_result("Fixed Bias -> Cutoff",
        solve_bjt(topology="fixed_bias", bjt=bjt, Vb=0.3, Vcc=12, Rb=200_000, Rc=2_000))

    print_result("Emitter Bias -> Dual Supply (Vee=-12V)",
        solve_bjt(topology="emitter_bias", bjt=bjt, Vb=3, Vcc=12, Vee=-12, Rb=200_000, Rc=2_000, Re=1_000))

    print_result("Emitter Bias -> Single Supply",
        solve_bjt(topology="emitter_bias", bjt=bjt, Vb=3, Vcc=12, Rb=200_000, Rc=2_000, Re=1_000))

    print_result("Voltage Divider Bias -> Active",
        solve_bjt(topology="voltage_divider_bias", bjt=bjt, Vcc=12, R1=100_000, R2=60_000, Rc=2_000, Re=1_000))

    print_result("Voltage Divider Bias -> Saturation",
        solve_bjt(topology="voltage_divider_bias", bjt=bjt, Vcc=12, R1=5_000, R2=60_000, Rc=2_000, Re=1_000))

    print_result("Collector-Feedback Bias -> Active",
        solve_bjt(topology="collector_feedback_bias", bjt=bjt, Vcc=12, Rb=200_000, Rc=2_000))

    #  Validation test 
    print("\n Error handling test ")
    try:
        solve_bjt(topology="fixed_bias", bjt=bjt, Vb=3, Vcc=12, Rb=0, Rc=2_000)
    except ValueError as e:
        print(f"  Caught: {e}")

    try:
        solve_bjt(topology="fixed_bias", bjt=bjt, Vb=3, Vcc=12, Rb=-500, Rc=2_000)
    except ValueError as e:
        print(f"  Caught: {e}")

    try:
        solve_bjt(topology="unknown_topology", bjt=bjt, Vb=3, Vcc=12, Rb=200_000, Rc=2_000)
    except ValueError as e:
        print(f"  Caught: {e}")