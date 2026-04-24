
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.core_helpers import fmt, _check

"""
BJT DC Bias Solver -> NPN only
Topologies: fixed_bias, emitter_bias, voltage_divider_bias, collector_feedback_bias
All values in SI units: Ohms, Volts, Amperes.
GUI-ready: all errors raised as ValueError, results are plain dicts, use fmt() for display.
"""


class BJT:
    """NPN BJT parameters."""
    def __init__(self, beta=100, vbe=0.7, vce_sat=0.2, vbe_sat=0.8, sat_margin=0.1):
        if beta <= 0:
            raise ValueError("beta must be positive.")
        self.beta = beta
        self.vbe = vbe
        self.vce_sat = vce_sat
        self.vbe_sat = vbe_sat
        self.sat_margin = sat_margin # V above vce_sat still considered saturated



def _result(mode, ib, ic, ie, vb, vc, ve, beta=None):
    """Pack node voltages and branch currents into a result dict."""
    VT = 0.025  # thermal voltage for rpi calculation
    rpi = (beta * VT / ic) if (ic > 0 and beta) else None

    d = dict(mode=mode, Ib=ib, Ic=ic, Ie=ie, Vb=vb, Vc=vc, Ve=ve, Vce=vc-ve, Vbe=vb-ve, rpi=rpi)
    if mode == "saturation" and ib > 0:
        d["beta_forced"] = ic / ib   # should be < beta to confirm saturation
    return d


#  1. FIXED or EMITTER BIAS  (emitter grounded, base driven via Rb from Vb) 

def solve_fixed_or_emitter_bias(*, bjt, Vb, Vcc, Rb, Rc, Re=0.0, Vee=0.0):
    _check(Rb=Rb, Rc=Rc, Vcc=Vcc)

    if Vb < Vee + bjt.vbe:
        return _result("cutoff", 0, 0, 0, Vb, Vcc, Vee, beta=None)

    ib = (Vb - bjt.vbe - Vee) / (Rb + (bjt.beta + 1) * Re)
    ic = bjt.beta * ib
    ie = ib + ic
    ve = Vee + ie * Re
    vc = Vcc - ic * Rc
    

    if vc - ve > bjt.vce_sat + bjt.sat_margin:
        return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve, beta=bjt.beta)

    # saturation
    if Re == 0:
        ve = Vee
        ib = (Vb - bjt.vbe_sat) / Rb
        ic = (Vcc - bjt.vce_sat) / Rc
        return _result("saturation", ib, ic, ib+ic, bjt.vbe_sat, bjt.vce_sat, ve, beta=bjt.beta)

    A = 1/Re + 1/Rb + 1/Rc
    B = (Vee / Re) + (Vb - bjt.vbe_sat) / Rb + (Vcc - bjt.vce_sat) / Rc
    ve = B / A
    vb = ve + bjt.vbe_sat
    vc = ve + bjt.vce_sat
    ib = (Vb  - vb) / Rb
    ic = (Vcc - vc) / Rc
    ie = (ve  - Vee) / Re
    # saturation Re>0 return:
    return _result("saturation", ib, ic, ie, vb, vc, ve, beta=bjt.beta)

#  2. VOLTAGE DIVIDER BIAS  (R1 from Vcc, R2 to GND, Re on emitter) 

def solve_voltage_divider_bias(*, bjt, Vcc, R1, R2, Rc, Re, Vee=0.0):
    # Check only components that must always be positive here.
    # Re is handled separately because we want to allow Re = 0.
    _check(R1=R1, R2=R2, Rc=Rc, Vcc=Vcc)

    vth = Vcc * R2 / (R1 + R2)                   # Thevenin base voltage
    rth = R1 * R2 / (R1 + R2)                   # Thevenin resistance

    # Cutoff: base-emitter junction is not forward biased
    # Must include Vee shift in the check.
    if vth < Vee + bjt.vbe:
        return _result("cutoff", 0, 0, 0, 0, Vcc, Vee, beta=None)

    # Special case: Re = 0
    # This becomes voltage-divider bias with emitter tied directly to Vee.
    # We must handle it separately to avoid division by zero in saturation math.
    if Re == 0:
        # Active region: emitter voltage is fixed at Vee
        ib = (vth - bjt.vbe - Vee) / rth
        ic = bjt.beta * ib
        ie = ib + ic
        ve = Vee
        vc = Vcc - ic * Rc

        # Check if transistor really stays in active region
        if vc - ve > bjt.vce_sat + bjt.sat_margin:
            return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve, beta=bjt.beta)

        # Saturation: clamp Vbe and Vce to saturation values
        ve = Vee
        vb = ve + bjt.vbe_sat
        vc = ve + bjt.vce_sat

        # Base current from KCL at base node
        ib = (Vcc - vb) / R1 - vb / R2

        # Collector current from collector resistor branch
        ic = (Vcc - vc) / Rc

        # Emitter current from transistor current relation
        ie = ib + ic

        return _result("saturation", ib, ic, ie, vb, vc, ve, beta=bjt.beta)

    # Normal case: Re > 0
    # Now it is safe to validate Re as a positive resistor.
    _check(Re=Re)

    # Active region: standard emitter-degeneration formula using Thevenin equivalent
    # Base-loop KVL includes Vee and emitter degeneration term (β+1)Re
    ib = (vth - bjt.vbe - Vee) / (rth + (bjt.beta + 1) * Re)
    ic = bjt.beta * ib
    ie = ib + ic
    ve = Vee + ie * Re
    vc = Vcc - ic * Rc

    # Check whether active-region assumption is valid
    if vc - ve > bjt.vce_sat + bjt.sat_margin:
        return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve, beta=bjt.beta)

    # Saturation: KCL at emitter node, solve A·Ve = B
    # This form uses the full R1/R2 network, not the Thevenin equivalent.
    A = 1 / Re + 1 / R1 + 1 / R2 + 1 / Rc
    B = Vee / Re + (Vcc - bjt.vbe_sat) / R1 - bjt.vbe_sat / R2 + (Vcc - bjt.vce_sat) / Rc
    ve = B / A

    # Clamp base and collector to saturation offsets above emitter
    vb = ve + bjt.vbe_sat
    vc = ve + bjt.vce_sat

    # Currents from each branch
    ib = (Vcc - vb) / R1 - vb / R2              # KCL at base node
    ic = (Vcc - vc) / Rc
    ie = (ve - Vee) / Re

    return _result("saturation", ib, ic, ie, vb, vc, ve, beta=bjt.beta)


#  3. COLLECTOR-FEEDBACK BIAS  (Rb from collector to base, emitter grounded) 

def solve_collector_feedback_bias(*, bjt, Vcc, Rcb, Rc, Re=0.0, Vee=0.0):
    _check(Rcb=Rcb, Rc=Rc, Vcc=Vcc)

    if Vcc < Vee + bjt.vbe:                             # cutoff
        return _result("cutoff", 0, 0, 0, 0, Vcc, Vee, beta=None)

    # active: current through Rc is Ic + Ib = (β+1)Ib
    # so Rc must use (β+1), not just β
    ib = (Vcc - bjt.vbe - Vee) / (Rcb + (bjt.beta + 1) * (Rc + Re))
    ic = bjt.beta * ib
    ie = ib + ic
    ve = Vee + ie * Re
    vc = Vcc - (ic + ib) * Rc

    if vc - ve > bjt.vce_sat + bjt.sat_margin:
        return _result("active", ib, ic, ie, ve + bjt.vbe, vc, ve, beta=bjt.beta)

    # saturation
    if Re == 0:
        ve = Vee
        vb = bjt.vbe_sat
        vc = bjt.vce_sat + ve
        ic = (Vcc - vc) / Rc - (vb - vc) / Rcb
        ib = (vb - vc) / Rcb
        ie = ib + ic
        return _result("saturation", ib, ic, ie, vb, vc, ve, beta=bjt.beta)

    # Re > 0: solve for Ve via KCL
    # ie = ib + ic
    # (ve-Vee)/Re = (vc-vb)/Rcb + (Vcc-vc)/Rc,  vb=ve+vbe_sat, vc=ve+vce_sat
    A = 1/Re + 1/Rcb + 1/Rc
    B = Vee/Re + (Vcc - bjt.vce_sat)/Rc + (bjt.vce_sat - bjt.vbe_sat)/Rcb
    ve = B / A
    vb = ve + bjt.vbe_sat
    vc = ve + bjt.vce_sat
    ic = (Vcc - vc) / Rc
    ib = (vc - vb) / Rcb
    ie = (ve - Vee) / Re
    return _result("saturation", ib, ic, ie, vb, vc, ve, beta=bjt.beta)


#  Dispatcher 

SOLVERS = {
    "fixed_or_emitter_bias": solve_fixed_or_emitter_bias,
    "voltage_divider_bias": solve_voltage_divider_bias,
    "collector_feedback_bias": solve_collector_feedback_bias,
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