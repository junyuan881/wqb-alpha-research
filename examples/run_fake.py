from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wqb_alpha.exporter import save_results
from wqb_alpha.genetic_search import GeneticAlgorithmProcess
from wqb_alpha.storage import AlphaStore
from wqb_alpha.worker import FakeWorker

store = AlphaStore()
store.reset(keep_session_cache=True)

process = GeneticAlgorithmProcess(
    name="demo_fake",
    ga_config={"generation": 2, "population": 10},
    worker_cls=FakeWorker,
    store=store,
    seed=123,
)
rows = process.run()
print("saved:", save_results(rows, "fake_demo.csv"))
