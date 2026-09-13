from __future__ import annotations

import os
import sys
from pathlib import Path

_DLL_DIRECTORIES: list[object] = []
if getattr(sys, "frozen", False) and hasattr(os, "add_dll_directory"):
    frozen_root = Path(sys._MEIPASS)
    for relative in ("PySide6", "shiboken6"):
        candidate = frozen_root / relative
        if candidate.is_dir():
            _DLL_DIRECTORIES.append(os.add_dll_directory(candidate))

from xiangqi_tutor.app import main  # noqa: E402 - frozen DLL search path must be set first

raise SystemExit(main())
