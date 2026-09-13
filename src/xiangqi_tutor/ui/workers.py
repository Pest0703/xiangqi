from __future__ import annotations

import asyncio
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from xiangqi_tutor.engine import EngineService
from xiangqi_tutor.tutor.openai_compatible import OpenAICompatibleProvider
from xiangqi_tutor.tutor.provider import TutorRequest


class EngineAnalysisThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, *, executable: Path, nnue: Path | None, fen: str, threads: int, hash_mb: int, multipv: int, depth: int, movetime_ms: int, timeout: float) -> None:
        super().__init__()
        self.params = {
            "executable": executable, "nnue": nnue, "fen": fen,
            "threads": threads, "hash_mb": hash_mb, "multipv": multipv,
            "depth": depth, "movetime_ms": movetime_ms, "timeout": timeout,
        }
        self.service: EngineService | None = None

    def run(self) -> None:
        try:
            self.service = EngineService(self.params["executable"], timeout=self.params["timeout"])
            self.service.configure(threads=self.params["threads"], hash_mb=self.params["hash_mb"], multipv=self.params["multipv"], nnue=self.params["nnue"])
            result = self.service.analyze(self.params["fen"], depth=self.params["depth"], movetime_ms=self.params["movetime_ms"])
            if not self.isInterruptionRequested():
                self.completed.emit(result)
        except Exception as exc:
            if not self.isInterruptionRequested():
                self.failed.emit(str(exc))
        finally:
            if self.service:
                self.service.close()

    def cancel(self) -> None:
        self.requestInterruption()
        if self.service:
            try:
                self.service.stop()
            except Exception:
                pass


class TutorThread(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, *, base_url: str, api_key: str, model: str, temperature: float, timeout: float, request: TutorRequest) -> None:
        super().__init__()
        self.params = {
            "base_url": base_url, "api_key": api_key, "model": model,
            "temperature": temperature, "timeout": timeout, "request": request,
        }

    def run(self) -> None:
        try:
            provider = OpenAICompatibleProvider(
                base_url=self.params["base_url"], api_key=self.params["api_key"],
                model=self.params["model"], temperature=self.params["temperature"],
                timeout_seconds=self.params["timeout"],
            )
            self.completed.emit(asyncio.run(provider.complete(self.params["request"])))
        except Exception as exc:
            self.failed.emit(str(exc))
