#!/usr/bin/env python3
"""
main.py — Global Currency Converter Pro

Entry point. Keeps startup minimal (per the performance requirement of
launching in under ~3 seconds): heavy imports are already lazily organised
across modules, and the window is shown as soon as it's built.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import MainWindow


def main() -> None:
    app = MainWindow()
    app.mainloop()


if __name__ == "__main__":
    main()
