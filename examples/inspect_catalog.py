from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from wqb_alpha.data_field_catalog import DataFieldCatalog
from wqb_alpha.operator_catalog import OperatorCatalog

fields = DataFieldCatalog()
operators = OperatorCatalog()

print(f"Data fields: {fields.count}")
for row in fields.search("free cash flow", field_type="MATRIX", min_coverage=0.7, limit=10):
    print(row["id"], row.get("coverage"), row.get("description"))

print("\nTime-series operators:")
for row in operators.search(category="Time Series", limit=10):
    print(row["name"], row.get("definition"))
