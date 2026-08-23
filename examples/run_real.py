from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os

from wqb_alpha.auth import prompt_credentials
from wqb_alpha.exporter import save_results
from wqb_alpha.genetic_search import GeneticAlgorithmProcess
from wqb_alpha.storage import AlphaStore
from wqb_alpha.worker import Worker

if not (os.getenv("WQB_USERNAME") and os.getenv("WQB_PASSWORD")):
    prompt_credentials()

store = AlphaStore()
# Uncomment only when you intentionally want to discard previous alpha results:
# store.reset(keep_session_cache=True)

process = GeneticAlgorithmProcess(
    name="glb_real",
    ga_config={"generation": 2, "population": 10},
    worker_cls=Worker,
    store=store,
    seed=123,
    multi_simulation=True,
)
rows = process.run()
print("saved:", save_results(rows, "real_results.csv"))
