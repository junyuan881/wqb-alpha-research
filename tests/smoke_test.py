from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wqb_alpha.alpha_template import ALPHA_SPACE
from wqb_alpha.data_field_catalog import DataFieldCatalog
from wqb_alpha.exporter import save_results
from wqb_alpha.genetic_search import GeneticAlgorithmProcess
from wqb_alpha.operator_catalog import OperatorCatalog
from wqb_alpha.storage import AlphaStore
from wqb_alpha.validator import validate_template
from wqb_alpha.worker import FakeWorker


def main() -> None:
    fields = DataFieldCatalog()
    operators = OperatorCatalog()
    assert fields.count == len(fields.records)
    assert len(operators.records) > 0

    report = validate_template(fields=fields, operators=operators)
    assert report.ok, report.errors

    for field_id in ALPHA_SPACE["<funds_data>"] + ALPHA_SPACE["<debt_data>"]:
        assert fields.get(field_id) is not None, field_id

    store = AlphaStore()
    store.reset(keep_session_cache=True)
    process = GeneticAlgorithmProcess(
        name="smoke",
        ga_config={"generation": 2, "population": 4},
        worker_cls=FakeWorker,
        store=store,
        seed=123,
    )
    rows = process.run()
    assert len(rows) == 8
    assert all(row["stage"] == "complete" for row in rows)
    output = save_results(rows, "smoke_test.csv")
    assert Path(output).is_absolute()
    assert Path(output).exists()
    print("SMOKE TEST PASS")
    print(output)


if __name__ == "__main__":
    main()
