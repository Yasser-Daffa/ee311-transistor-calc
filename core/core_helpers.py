
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PyQt6.QtGui import QDoubleValidator

"""
Helper functions used across multiple controllers and widgets, such as input validation and output formatting.
"""



def _check(**kwargs):
    """Raise ValueError for any zero or negative resistor/supply value."""
    for name, value in kwargs.items():
        if value <= 0:
            raise ValueError(f"{name} must be a positive number, got {value}.")



def fmt(value, unit, scale=None):
    """
    Format a value into a readable string with auto-scaled prefix.
    Use this in your GUI to display results cleanly.
    

    Examples:

    fmt(0.00115, "A")  →  "1.1500 mA"
    fmt(0.0000023, "A")  →  "2.3000 µA"
    fmt(6.35, "V")  →  "6.3500 V"
    """
    if unit == "Ω":
        if value is None:
            return "—"
        if abs(value) >= 1e6:
            return f"{value/1e6:.4f} MΩ"
        if abs(value) >= 1e3:
            return f"{value/1e3:.4f} kΩ"
        return f"{value:.4f} Ω"
    if unit == "A":
        if scale == "mA":
            return f"{value*1e3:.4f} mA"
        if scale == "µA":
            return f"{value*1e6:.4f} µA"
        # auto-scale fallback
        if abs(value) >= 1e-3:
            return f"{value*1e3:.4f} mA"
        else:
            return f"{value*1e6:.4f} µA"
    if unit == "V":
        return f"{value:.4f} V"
    return f"{value:.4f} {unit}"


def signed_validator(parent=None):
    validator = QDoubleValidator(-1e12, 1e12, 10, parent)
    validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
    return validator


def positive_validator(parent=None):
    validator = QDoubleValidator(0.0, 1e12, 10, parent)
    validator.setNotation(QDoubleValidator.Notation.ScientificNotation)
    return validator