
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# bjt_widget.py
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QWidget
from core.bjt_transistor import BJT, fmt, solve_fixed_bias

class BJTWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("bjt_fixed_bias.ui", self)  # loads all your named widgets automatically
