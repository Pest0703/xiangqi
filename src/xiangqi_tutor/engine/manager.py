from __future__ import annotations

import hashlib
import json
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import Lock
from typing import Sequence

from PySide6.QtCore import QObject, Signal

from xiangqi_tutor.database.connection import Database
from xiangqi_tutor.engine.service import EngineService
from xiangqi_tutor.models.engine import AnalysisResult, CandidateMove, EvalScore, ScoreKind


@dataclass(frozen=True, slots=True)
class EngineJob:
    request_id: str
    fen: str
    position_version: int
    depth: int
    movetime_ms: int
    multipv: int = 1


@dataclass(frozen=True, slots=True)
class EngineJobResult:
    job: EngineJob
    analysis: AnalysisResult


@dataclass(frozen=True, slots=True)
class EngineJobFailure:
    job: EngineJob
    message: str


class EngineManager(QObject):
    """在单一后台执行器中串行复用一个 UCI 进程。"""

    completed = Signal(object)
    failed = Signal(object)

    def __init__(
        self,
        executable: Path,
        *,
        args: Sequence[str] = (),
        nnue: Path | None = None,
        threads: int = 2,
        hash_mb: int = 256,
        timeout: float = 15,
        database: Database | None = None,
    ) -> None:
        super().__init__()
        self.executable = Path(executable)
        self.args = tuple(args)
        self.nnue = nnue
        self.threads = threads
        self.hash_mb = hash_mb
        self.timeout = timeout
        self.database = database
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="pikafish")
        self._service: EngineService | None = None
        self._cancelled: set[str] = set()
        self._lock = Lock()
        self._closed = False

    def submit(self, job: EngineJob) -> Future[EngineJobResult | None]:
        if self._closed:
            raise RuntimeError("引擎管理器已经关闭")
        return self._executor.submit(self._run, job)

    def _ensure_service(self, multipv: int) -> EngineService:
        if self._service is None:
            self._service = EngineService(self.executable, args=self.args, timeout=self.timeout)
        self._service.configure(threads=self.threads, hash_mb=self.hash_mb, multipv=multipv, nnue=self.nnue)
        return self._service

    def _run(self, job: EngineJob) -> EngineJobResult | None:
        with self._lock:
            if job.request_id in self._cancelled or self._closed:
                self._cancelled.discard(job.request_id)
                return None
            try:
                cache_key, cache_settings = self._cache_identity(job)
                cached = self.database.get_engine_cache(cache_key) if self.database else None
                if cached:
                    result = EngineJobResult(job, self._deserialize(cached))
                    self.completed.emit(result)
                    return result
                service = self._ensure_service(job.multipv)
                analysis = service.analyze(job.fen, depth=job.depth, movetime_ms=job.movetime_ms)
                if job.request_id in self._cancelled or self._closed:
                    self._cancelled.discard(job.request_id)
                    return None
                result = EngineJobResult(job, analysis)
                if self.database:
                    self.database.put_engine_cache(cache_key, job.fen, cache_settings, asdict(analysis))
                self.completed.emit(result)
                return result
            except Exception as exc:
                if self._service:
                    self._service.close()
                    self._service = None
                if job.request_id not in self._cancelled and not self._closed:
                    self.failed.emit(EngineJobFailure(job, str(exc)))
                self._cancelled.discard(job.request_id)
                return None

    def _cache_identity(self, job: EngineJob) -> tuple[str, dict[str, object]]:
        settings: dict[str, object] = {
            "engine": str(self.executable.resolve()),
            "engine_mtime": self.executable.stat().st_mtime_ns,
            "args": self.args,
            "nnue": str(self.nnue.resolve()) if self.nnue else "",
            "threads": self.threads,
            "hash_mb": self.hash_mb,
            "multipv": job.multipv,
            "depth": job.depth,
            "movetime_ms": job.movetime_ms,
        }
        raw = json.dumps({"fen": job.fen, **settings}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest(), settings

    @staticmethod
    def _deserialize(data: dict[str, object]) -> AnalysisResult:
        candidates = []
        for raw in data.get("candidates", []):
            item = dict(raw)
            evaluation = item.get("evaluation")
            if evaluation:
                value = dict(evaluation)
                item["evaluation"] = EvalScore(
                    ScoreKind(value["kind"]), value["value"], value.get("pov", "side_to_move"), value.get("score_for_red")
                )
            item["pv"] = tuple(item.get("pv", ()))
            candidates.append(CandidateMove(**item))
        payload = dict(data)
        payload["candidates"] = tuple(candidates)
        return AnalysisResult(**payload)

    def cancel(self, request_id: str) -> None:
        self._cancelled.add(request_id)
        service = self._service
        if service:
            try:
                service.stop()
            except Exception:
                pass

    def close(self) -> None:
        self._closed = True
        service = self._service
        if service:
            try:
                service.stop()
            except Exception:
                pass
        self._executor.shutdown(wait=True, cancel_futures=True)
        if self._service:
            self._service.close()
            self._service = None
