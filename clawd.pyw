"""
Clawd — desktop study buddy.

Run with:  pythonw clawd.pyw   (no console window)
       or  python  clawd.pyw   (console, useful for debugging)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.app import main  # noqa: E402

if __name__ == "__main__":
    main()
