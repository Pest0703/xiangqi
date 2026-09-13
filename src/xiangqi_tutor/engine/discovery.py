from __future__ import annotations

import os
import shutil
from pathlib import Path


def discover_pikafish(configured: Path | None = None) -> Path | None:
    candidates: list[Path] = []
    if configured:
        candidates.append(Path(configured))
    if found := shutil.which("pikafish"):
        candidates.append(Path(found))
    if found_exe := shutil.which("pikafish.exe"):
        candidates.append(Path(found_exe))
    project_root = Path(__file__).resolve().parents[3]
    candidates.extend(
        [
            project_root / "engines" / "pikafish.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "XiangqiTutor" / "engines" / "pikafish.exe",
        ]
    )
    return next((path.resolve() for path in candidates if path.is_file()), None)


def discover_nnue(engine_path: Path | None, configured: Path | None = None) -> Path | None:
    candidates = [Path(configured)] if configured else []
    if engine_path:
        candidates.extend(sorted(engine_path.parent.glob("*.nnue")))
    return next((path.resolve() for path in candidates if path.is_file()), None)
