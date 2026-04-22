
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

"""
This file contains core design functions for BJT amplifier design, such as the classic "thirds" CE design.
The functions here are not tied to any specific GUI, and can be used by any controller or widget that needs to 
perform amplifier design calculations.
"""


# core/bjt_amplifiers.py

def design_ce_from_specs(*, Vcc, Icmax_mA, beta, vbe=0.7, divider_factor=10):
    """
    Design a single-stage CE amplifier from:
    - Vcc (V)
    - Icmax_mA (mA)
    - beta

    Assumptions:
    - thirds bias: VRC ≈ VCE ≈ VE ≈ VCC/3
    - ICQ = ICmax
    - divider stiffness: RB(th) = beta*RE/divider_factor
    """

    if Vcc <= 0:
        raise ValueError("Vcc must be positive.")
    if Icmax_mA <= 0:
        raise ValueError("Icmax must be positive.")
    if beta <= 0:
        raise ValueError("beta must be positive.")

    Ic = Icmax_mA * 1e-3          # mA -> A
    Ie = Ic * (1 + 1 / beta)

    # thirds design
    Vrc = Vcc / 3
    Ve  = Vcc / 3
    Vce = Vcc / 3
    Vb  = Ve + vbe

    Rc = Vrc / Ic
    Re = Ve / Ie

    # Thevenin equivalent seen by the base
    Rb_th = beta * Re / divider_factor
    Vbb   = Vb

    # Solve divider from:
    #   Vbb = Vcc * R2 / (R1 + R2)
    #   Rb_th = R1 || R2
    R1 = Rb_th * Vcc / Vbb
    R2 = Rb_th * Vcc / (Vcc - Vbb)

    return {
        "Rc": Rc,
        "Re": Re,
        "Rb": Rb_th,   # Thevenin resistance of divider
        "Vbb": Vbb,
        "R1": R1,
        "R2": R2,
        "Vce": Vce,
        "Ve": Ve,
        "Ic": Ic,
        "Ie": Ie,
    }