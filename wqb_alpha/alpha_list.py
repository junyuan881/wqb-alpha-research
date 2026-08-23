from __future__ import annotations

import time

from tqdm.auto import tqdm

from .alpha import Alpha, AlphaStage
from .storage import AlphaStore


class AlphaList:
    def __init__(self, alphas: list[Alpha], store: AlphaStore | None = None) -> None:
        self._alphas = alphas
        self._names = [alpha.filename for alpha in alphas]
        self.store = store or AlphaStore()

    def update_and_check_status(self) -> tuple[int, int, int, int]:
        counts = {stage: 0 for stage in AlphaStage}
        for i, alpha in enumerate(self._alphas):
            stage = self.store.find_stage(alpha.filename)
            counts[stage] += 1
            if stage not in (AlphaStage.NONE, alpha.stage):
                path = self.store.locate(alpha.filename)
                if path:
                    self._alphas[i] = self.store.load(path)
        return (
            counts[AlphaStage.NONE],
            counts[AlphaStage.PENDING],
            counts[AlphaStage.COMPLETE],
            counts[AlphaStage.ERROR],
        )

    def persist_missing(self) -> None:
        for alpha in self._alphas:
            if self.store.find_stage(alpha.filename) == AlphaStage.NONE:
                self.store.save(alpha)

    def sim_and_wait(self, poll_seconds: float = 1.0) -> None:
        self.persist_missing()
        pbar = tqdm(total=len(self._alphas), desc="Waiting for simulations")
        last_done = 0
        while True:
            _, _, complete, error = self.update_and_check_status()
            done = complete + error
            pbar.update(max(0, done - last_done))
            last_done = done
            if done == len(self._alphas):
                break
            time.sleep(poll_seconds)
        pbar.close()

    def get_alphas(self) -> dict[str, Alpha]:
        self.update_and_check_status()
        return dict(zip(self._names, self._alphas))
