
import sys, os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# always finds the .ui file next to this .py file, regardless of where you run from
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # controllers/
UI_PATH = os.path.join(BASE_DIR, "..", "..", "ui", "bjt_transistors", "bjt_emitter_bias.ui")


# bjt_widget.py
from PyQt6.QtWidgets import QApplication, QLineEdit, QWidget
from PyQt6.uic import loadUi
from PyQt6.QtWidgets import QWidget
from core.bjt_transistor import BJT, solve_fixed_or_emitter_bias
from core.core_helpers import positive_validator, signed_validator, fmt


class BJTEmitterBiasWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(UI_PATH, self)

        # Set up validators for input fields
        
        # Vcc, Vee, Vbb can be negative, so use signed_validator
        self.lineEditVcc.setValidator(signed_validator(self))
        self.lineEditVee.setValidator(signed_validator(self))
        self.lineEditVbb.setValidator(signed_validator(self))

        # Rb, Rc, Re must be positive, so use positive_validator
        self.lineEditRb.setValidator(positive_validator(self))
        self.lineEditRc.setValidator(positive_validator(self))
        self.lineEditRe.setValidator(positive_validator(self))
        self.lineEditBeta.setValidator(positive_validator(self))

        for field in [self.lineEditVcc, self.lineEditVee, self.lineEditVbb,
                      self.lineEditRb, self.lineEditRc, self.lineEditRe, self.lineEditBeta]:
            field.textChanged.connect(self.calculate)


        self.pushButtonClear.clicked.connect(self.clear_fields)   # change name if your button is named differently

    def clear_fields(self):
        # clear all line edits in this widget
        for w in self.findChildren(QLineEdit):
            w.clear()

        # optional: clear output labels too
        for name in [
            "labelOutputIb",
            "labelOutputIc",
            "labelOutputIe",
            "labelOutputVe",
            "labelOutputVb",
            "labelOutputVc",
            "labelOutputRpi",
        ]:
            if hasattr(self, name):
                getattr(self, name).setText("-")


    def calculate(self):
        # --- step 1: wait silently until all fields have valid numbers ---
        try:
            vcc  = float(self.lineEditVcc.text())
            vbb  = float(self.lineEditVbb.text())
            rb   = float(self.lineEditRb.text())
            rc   = float(self.lineEditRc.text())
            vee = float(self.lineEditVee.text() or 0)
            re  = float(self.lineEditRe.text()  or 0)
            beta = float(self.lineEditBeta.text())
        except ValueError:
            self._set_mode("— awaiting input —", "#e8eaf6", "#3d3d9e")
            return

        # --- step 2: run solver, catch bad values (Rb=0 etc.) ---
        try:
            result = solve_fixed_or_emitter_bias(
                bjt=BJT(beta=beta),
                Vb=vbb, Vcc=vcc, Rb=rb, Rc=rc, Re=re, Vee=vee,
            )
        except ValueError as e:
            self._set_mode(f"Error: {e}", "#f8d7da", "#721c24")
            return

        # --- step 3: push results to output labels ---
        self.labelOutputVb.setText(fmt(result["Vb"],  "V"))
        self.labelOutputVc.setText(fmt(result["Vc"],  "V"))
        self.labelOutputVe.setText(fmt(result["Ve"],  "V"))
        self.labelOutputIb.setText(fmt(result["Ib"],  "A", scale="µA"))
        self.labelOutputIc.setText(fmt(result["Ic"],  "A", scale="mA"))
        self.labelOutputIe.setText(fmt(result["Ie"],  "A", scale="mA"))
        self.labelOutputRpi.setText(fmt(result["rpi"], "Ω"))

        colors = {
            "active":     ("#d4edda", "#155724"),
            "saturation": ("#fff3cd", "#856404"),
            "cutoff":     ("#f8d7da", "#721c24"),
        }
        bg, fg = colors[result["mode"]]
        self._set_mode(result["mode"].upper(), bg, fg)

    def _set_mode(self, text, bg, fg):
        self.labelMode.setText(text)
        self.labelMode.setStyleSheet(
            f"border-radius:6px; font: 700 11pt 'Rockwell'; "
            f"padding: 4px 14px; background-color:{bg}; color:{fg};"
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BJTEmitterBiasWidget()
    window.setWindowTitle("BJT DC Bias — Test")
    window.show()
    sys.exit(app.exec())