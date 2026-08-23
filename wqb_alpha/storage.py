from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Iterable

from .alpha import Alpha, AlphaStage
from .config import COMPLETE_DIR, ERROR_DIR, PENDING_DIR, ensure_runtime_directories


class AlphaStore:
    def __init__(self) -> None:
        ensure_runtime_directories()
        self._dirs = {
            AlphaStage.PENDING: PENDING_DIR,
            AlphaStage.COMPLETE: COMPLETE_DIR,
            AlphaStage.ERROR: ERROR_DIR,
        }

    def stage_dir(self, stage: AlphaStage) -> Path:
        if stage == AlphaStage.NONE:
            raise ValueError("AlphaStage.NONE has no directory")
        return self._dirs[stage]

    def path_for(self, filename: str, stage: AlphaStage) -> Path:
        return (self.stage_dir(stage) / filename).resolve()

    def find_stage(self, filename: str) -> AlphaStage:
        for stage in (AlphaStage.PENDING, AlphaStage.COMPLETE, AlphaStage.ERROR):
            if self.path_for(filename, stage).exists():
                return stage
        return AlphaStage.NONE

    def locate(self, filename: str) -> Path | None:
        stage = self.find_stage(filename)
        if stage == AlphaStage.NONE:
            return None
        return self.path_for(filename, stage)

    def save(self, alpha: Alpha) -> Path:
        path = self.path_for(alpha.filename, alpha.stage)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = path.with_name(f"tmp_{path.name}")
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(alpha.to_dict(), f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, path)
        return path

    def load(self, path: str | Path) -> Alpha:
        absolute = Path(path).resolve()
        with absolute.open("r", encoding="utf-8") as f:
            return Alpha.from_dict(json.load(f))

    def load_by_filename(self, filename: str) -> Alpha | None:
        path = self.locate(filename)
        return self.load(path) if path else None

    def move(self, alpha: Alpha, new_stage: AlphaStage, result: dict | None = None) -> Path:
        old_path = self.locate(alpha.filename)
        if old_path and old_path.exists():
            old_path.unlink()
        alpha.stage = new_stage
        if result is not None:
            alpha.result = result
        return self.save(alpha)

    def pending_paths(self, exclude: Iterable[str | Path] = ()) -> list[Path]:
        excluded = {str(Path(p).resolve()) for p in exclude}
        paths = []
        for path in PENDING_DIR.glob("*.json"):
            if path.name.startswith("tmp_"):
                continue
            resolved = str(path.resolve())
            if resolved not in excluded:
                paths.append(path.resolve())
        return sorted(paths)

    def reset(self, keep_session_cache: bool = True) -> None:
        for directory in (PENDING_DIR, COMPLETE_DIR, ERROR_DIR):
            shutil.rmtree(directory, ignore_errors=True)
            directory.mkdir(parents=True, exist_ok=True)
        if not keep_session_cache:
            from .config import SESSION_CACHE

            SESSION_CACHE.unlink(missing_ok=True)
