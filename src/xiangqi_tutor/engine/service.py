from __future__ import annotations

import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Sequence

from xiangqi_tutor.engine.protocol import normalize_score_for_red, parse_info_line
from xiangqi_tutor.models.engine import AnalysisResult, CandidateMove


class EngineError(RuntimeError):
    pass


class EngineTimeout(EngineError):
    pass


class EngineService:
    """长生命周期 UCI 进程。调用方必须在工作线程中执行 analyze。"""

    def __init__(self, executable: Path | str, *, args: Sequence[str] = (), timeout: float = 10) -> None:
        self.command = [str(executable), *args]
        self.timeout = timeout
        self.process: subprocess.Popen[str] | None = None
        self._lines: queue.Queue[str | None] = queue.Queue()
        self._reader: threading.Thread | None = None

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return
        try:
            self.process = subprocess.Popen(
                self.command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0,
            )
        except OSError as exc:
            raise EngineError("无法启动 Pikafish，请检查可执行文件路径") from exc
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        self._send("uci")
        self._wait_for("uciok")
        self._send("isready")
        self._wait_for("readyok")

    def _read_stdout(self) -> None:
        assert self.process and self.process.stdout
        try:
            for line in self.process.stdout:
                self._lines.put(line.rstrip("\r\n"))
        finally:
            self._lines.put(None)

    def _send(self, command: str) -> None:
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            raise EngineError("Pikafish进程未运行")
        try:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
        except OSError as exc:
            raise EngineError("Pikafish通信失败") from exc

    def _next_line(self, deadline: float) -> str:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise EngineTimeout("Pikafish响应超时")
        try:
            line = self._lines.get(timeout=remaining)
        except queue.Empty as exc:
            raise EngineTimeout("Pikafish响应超时") from exc
        if line is None:
            raise EngineError("Pikafish意外退出")
        return line

    def _wait_for(self, token: str) -> None:
        deadline = time.monotonic() + self.timeout
        while token not in self._next_line(deadline):
            pass

    def configure(self, *, threads: int, hash_mb: int, multipv: int, nnue: Path | None = None) -> None:
        self.start()
        for name, value in (("Threads", threads), ("Hash", hash_mb), ("MultiPV", multipv)):
            self._send(f"setoption name {name} value {value}")
        if nnue:
            self._send(f"setoption name EvalFile value {nnue}")
        self._send("isready")
        self._wait_for("readyok")

    def analyze(self, fen: str, *, depth: int | None = 16, movetime_ms: int | None = None) -> AnalysisResult:
        self.start()
        side = fen.split()[1]
        self._send(f"position fen {fen}")
        self._send(f"go movetime {movetime_ms}" if movetime_ms else f"go depth {depth or 16}")
        deadline = time.monotonic() + self.timeout
        candidates: dict[int, CandidateMove] = {}
        best_move: str | None = None
        started = time.monotonic()
        while True:
            try:
                line = self._next_line(deadline)
            except EngineTimeout:
                self.stop()
                raise
            if parsed := parse_info_line(line, side_to_move=side):
                candidates[parsed[0]] = parsed[1]
            if line.startswith("bestmove"):
                parts = line.split()
                best_move = None if len(parts) < 2 or parts[1] in ("(none)", "0000") else parts[1]
                break
        ordered = tuple(candidate for _, candidate in sorted(candidates.items()))
        first = ordered[0] if ordered else None
        raw = first.score_cp if first else None
        return AnalysisResult(
            fen=fen, side_to_move=side, best_move=best_move,
            depth=first.depth if first else 0, nodes=max((c.nodes for c in ordered), default=0),
            time_ms=int((time.monotonic() - started) * 1000), score_raw=raw,
            score_for_red=normalize_score_for_red(raw, side), candidates=ordered,
        )

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self._send("stop")

    def close(self) -> None:
        process = self.process
        self.process = None
        if not process:
            return
        if process.poll() is None:
            try:
                if process.stdin:
                    process.stdin.write("quit\n")
                    process.stdin.flush()
                process.wait(timeout=2)
            except (OSError, subprocess.TimeoutExpired):
                process.kill()
                process.wait(timeout=2)
        for stream in (process.stdin, process.stdout):
            if stream:
                stream.close()

    def __enter__(self) -> "EngineService":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.close()
