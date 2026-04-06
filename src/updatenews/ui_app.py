"""UI entrypoint.

Run recommended:
  python -m src.updatenews.ui_app

This file also supports being executed directly (PyCharm run file), by
falling back to absolute imports.
"""

import os
import sys

try:
    # When executed as a module: python -m src.updatenews.ui_app
    from .main_window import MainWindow
except ImportError:  # pragma: no cover
    # When executed as a script: python src/updatenews/ui_app.py
    # Ensure project root is on sys.path so `import src...` works.
    _here = os.path.abspath(os.path.dirname(__file__))
    _project_root = os.path.abspath(os.path.join(_here, "..", ".."))
    if _project_root not in sys.path:
        sys.path.insert(0, _project_root)
    from src.updatenews.main_window import MainWindow

def main():
    app = MainWindow()
    app.mainloop()

if __name__ == "__main__":
    main()