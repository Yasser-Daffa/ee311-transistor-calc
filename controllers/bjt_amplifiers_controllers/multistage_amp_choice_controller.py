import os
import sys

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QWidget, QPushButton, QApplication
from PyQt6.uic import loadUi

# If this file is inside controllers/bjt_amplifiers_controllers/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE_DIR, '..', '..'))

# User folder layout: ui/multistage/(ui files)
CHOICE_UI_PATH = os.path.join(PROJECT_ROOT, 'ui', 'multistage', 'multistage_amp_choice.ui')


class MultistageAmpChoiceWidget(QWidget):
    """
    Separate topology-choice page.

    Emits:
        topologySelected(str)

    Values emitted:
        CE-CE, CC-CE, CE-CC, CE-CE-CC, CC-CE-CE-CC, Auto
    """

    topologySelected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi(CHOICE_UI_PATH, self)
        self._connect_buttons()

    def _connect_buttons(self):
        # First try common object names.
        name_map = {
            'buttonCECE': 'CE-CE',
            'pushButtonCECE': 'CE-CE',
            'buttonCCCE': 'CC-CE',
            'pushButtonCCCE': 'CC-CE',
            'buttonCECC': 'CE-CC',
            'pushButtonCECC': 'CE-CC',
            'buttonCECECC': 'CE-CE-CC',
            'pushButtonCECECC': 'CE-CE-CC',
            'buttonCCCECECC': 'CC-CE-CE-CC',
            'pushButtonCCCECECC': 'CC-CE-CE-CC',
            'buttonAuto': 'Auto',
            'pushButtonAuto': 'Auto',
        }

        connected = set()
        for name, topology in name_map.items():
            btn = getattr(self, name, None)
            if isinstance(btn, QPushButton):
                btn.clicked.connect(lambda checked=False, t=topology: self.topologySelected.emit(t))
                connected.add(btn)

        # Then also connect by button text, so the file survives UI object-name changes.
        text_map = {
            'CE-CE': 'CE-CE',
            'CC-CE': 'CC-CE',
            'CE-CC': 'CE-CC',
            'CE CE': 'CE-CE',
            'CC CE': 'CC-CE',
            'CE CC': 'CE-CC',
            'CE-CE-CC': 'CE-CE-CC',
            'CC-CE-CE-CC': 'CC-CE-CE-CC',
            'AUTO': 'Auto',
        }
        for btn in self.findChildren(QPushButton):
            if btn in connected:
                continue
            raw = btn.text().strip().upper().replace('–', '-').replace('—', '-')
            raw = ' '.join(raw.split())
            for key, topology in text_map.items():
                if key in raw:
                    btn.clicked.connect(lambda checked=False, t=topology: self.topologySelected.emit(t))
                    break


if __name__ == '__main__':
    app = QApplication(sys.argv)
    w = MultistageAmpChoiceWidget()
    w.topologySelected.connect(print)
    w.show()
    sys.exit(app.exec())
