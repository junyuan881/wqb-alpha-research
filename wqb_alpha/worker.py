from __future__ import annotations

import random
import time
from pathlib import Path

from .alpha import Alpha, AlphaStage
from .api_client import BrainClient
from .config import MULTI_SIMULATION_SIZE, SIMULATION_LIMIT
from .storage import AlphaStore


class Worker:
    def __init__(
        self,
        multi_simulation: bool = True,
        client: BrainClient | None = None,
        store: AlphaStore | None = None,
    ) -> None:
        self.client = client or BrainClient()
        self.multi_simulation = multi_simulation
        self.store = store or AlphaStore()

    def _post_payload(self, alpha: Alpha) -> str:
        response = self.client.post("/simulations", json=alpha.payload)
        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("Simulation submission returned no Location header")
        return location

    def _post_multi_payload(self, alphas: list[Alpha]) -> str:
        if not 2 <= len(alphas) <= MULTI_SIMULATION_SIZE:
            raise ValueError(
                f"multi-simulation batch must contain 2..{MULTI_SIMULATION_SIZE} alphas"
            )
        response = self.client.post("/simulations", json=[alpha.payload for alpha in alphas])
        location = response.headers.get("Location", "")
        if not location:
            raise RuntimeError("Multi-simulation submission returned no Location header")
        return location

    def _get_status(self, location_url: str) -> tuple[bool, float, str]:
        response = self.client.get(location_url)
        data = response.json()
        retry = float(response.headers.get("Retry-After", "0") or 0)
        if retry > 0:
            return False, retry, ""
        alpha_id = data.get("alpha") if isinstance(data, dict) else None
        if not alpha_id:
            raise RuntimeError(f"Completed simulation has no alpha id: {data}")
        return True, 0.0, str(alpha_id)

    def _get_multi_status(self, location_url: str) -> tuple[bool, float, list[str]]:
        response = self.client.get(location_url)
        data = response.json()
        retry = float(response.headers.get("Retry-After", "0") or 0)
        if retry > 0:
            return False, retry, []
        children = data.get("children") if isinstance(data, dict) else None
        if not isinstance(children, list):
            raise RuntimeError(f"Completed multi-simulation has no children: {data}")
        return True, 0.0, [str(child) for child in children]

    def _get_result(self, alpha_id: str) -> dict:
        return self.client.get(f"/alphas/{alpha_id}").json()

    def _mark_error(self, filepath: str | Path, reason: str) -> None:
        alpha = self.store.load(filepath)
        result = dict(alpha.result)
        result["pipelineError"] = reason
        self.store.move(alpha, AlphaStage.ERROR, result=result)

    def _complete(self, filepath: str | Path, alpha_id: str) -> None:
        alpha = self.store.load(filepath)
        result = self._get_result(alpha_id)
        self.store.move(alpha, AlphaStage.COMPLETE, result=result)

    def run(self) -> None:
        running: dict[str, list[Path]] = {}
        try:
            while True:
                while len(running) < SIMULATION_LIMIT:
                    already_running = [path for batch in running.values() for path in batch]
                    pending = self.store.pending_paths(already_running)
                    if not pending:
                        break

                    batch = (
                        pending[:MULTI_SIMULATION_SIZE]
                        if self.multi_simulation
                        else pending[:1]
                    )
                    alphas = [self.store.load(path) for path in batch]
                    try:
                        if len(alphas) == 1:
                            location = self._post_payload(alphas[0])
                        else:
                            location = self._post_multi_payload(alphas)
                        running[location] = batch
                    except Exception as exc:
                        for path in batch:
                            self._mark_error(path, f"submit failed: {exc}")
                    time.sleep(1.0)

                if not running:
                    if not self.store.pending_paths():
                        break
                    time.sleep(2.0)
                    continue

                for location, filepaths in list(running.items()):
                    try:
                        if len(filepaths) == 1:
                            done, retry, alpha_id = self._get_status(location)
                            if done:
                                self._complete(filepaths[0], alpha_id)
                                del running[location]
                            else:
                                time.sleep(max(retry, 0.2))
                        else:
                            done, retry, children = self._get_multi_status(location)
                            if not done:
                                time.sleep(max(retry, 0.2))
                                continue

                            for i, path in enumerate(filepaths):
                                if i >= len(children):
                                    self._mark_error(path, "multi-simulation returned fewer children than submitted")
                                    continue
                                child_location = f"/simulations/{children[i]}"
                                child_done, child_retry, alpha_id = self._get_status(child_location)
                                if not child_done:
                                    self._mark_error(
                                        path,
                                        f"child simulation still pending unexpectedly; retry={child_retry}",
                                    )
                                else:
                                    self._complete(path, alpha_id)
                            del running[location]
                    except Exception as exc:
                        for path in filepaths:
                            if self.store.find_stage(path.name) == AlphaStage.PENDING:
                                self._mark_error(path, f"poll/result failed: {exc}")
                        del running[location]
                    break
        finally:
            for location in list(running):
                try:
                    self.client.delete(location)
                except Exception:
                    pass


class FakeWorker:
    def __init__(
        self,
        multi_simulation: bool = True,
        store: AlphaStore | None = None,
        seed: int | None = 123,
        **_: object,
    ) -> None:
        self.multi_simulation = multi_simulation
        self.store = store or AlphaStore()
        self.rng = random.Random(seed)

    def run(self) -> None:
        while True:
            pending = self.store.pending_paths()
            if not pending:
                return
            batch = pending[:MULTI_SIMULATION_SIZE] if self.multi_simulation else pending[:1]
            for path in batch:
                alpha = self.store.load(path)
                sharpe = self.rng.uniform(-0.6, 2.4)
                result = {
                    "is": {
                        "sharpe": sharpe,
                        "turnover": self.rng.uniform(0.0, 1.0),
                        "fitness": sharpe,
                        "returns": self.rng.uniform(-0.1, 0.3),
                        "drawdown": self.rng.uniform(0.0, 0.25),
                        "margin": self.rng.uniform(0.0, 0.1),
                    },
                    "startDate": "2012-07-15",
                    "fake": True,
                }
                self.store.move(alpha, AlphaStage.COMPLETE, result=result)
