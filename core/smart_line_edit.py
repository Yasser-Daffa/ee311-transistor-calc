import re
from PyQt6.QtWidgets import QLineEdit, QApplication
from PyQt6.QtGui import QKeySequence


class SmartLineEdit(QLineEdit):
    """
    Custom QLineEdit that cleans pasted input by stripping units.

    Example:
        "1.9726 kΩ" → "1.9726"
        "2.2e3 Ω"   → "2.2e3"
    """

    def keyPressEvent(self, event):
        """
        Override key press behavior to intercept paste operations.
        If user pastes (Ctrl+V), clean the text before inserting.
        """
        if event.matches(QKeySequence.StandardKey.Paste):
            # Get raw text from clipboard
            text = QApplication.clipboard().text()

            # Strip units / extra characters and set cleaned value
            self.setText(self.strip_units(text))
        else:
            # Default behavior for all other keys
            super().keyPressEvent(event)

    @staticmethod
    def strip_units(text):
        """
        Extract the first valid number from a string.

        Supports:
            - integers: "10"
            - decimals: "1.9726"
            - scientific notation: "2.2e3", "1e-5"

        Ignores:
            - units like "kΩ", "V", etc.
            - any extra text

        Returns:
            Clean numeric string, or "" if no valid number is found.
        """

        # Regex breakdown:
        # [-+]?        → optional sign (+ or -)
        # \d*\.?\d+    → digits with optional decimal point
        # (?:eE...)    → optional scientific notation (e.g., e-5, E+3)
        match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)

        # Return the matched number, or empty string if none found
        return match.group(0) if match else ""