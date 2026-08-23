from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .config import DATA_FIELDS_JSON


class DataFieldCatalog:
    def __init__(self, path: str | Path = DATA_FIELDS_JSON) -> None:
        self.path = Path(path).resolve()
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise ValueError("Data fields JSON must contain a `results` list")
        self.count = int(data.get("count", len(data["results"])))
        self.records: list[dict] = data["results"]
        self.by_id = {record.get("id"): record for record in self.records}

    def get(self, field_id: str) -> dict | None:
        return self.by_id.get(field_id)

    def ids(self) -> set[str]:
        return {field_id for field_id in self.by_id if isinstance(field_id, str)}

    def search(
        self,
        query: str = "",
        field_type: str | None = None,
        dataset_id: str | None = None,
        min_coverage: float | None = None,
        limit: int = 50,
    ) -> list[dict]:
        terms = [term for term in query.lower().split() if term]
        out = []
        for record in self.records:
            if field_type and str(record.get("type", "")).upper() != field_type.upper():
                continue
            if dataset_id and record.get("dataset", {}).get("id") != dataset_id:
                continue
            coverage = record.get("coverage")
            if min_coverage is not None and (coverage is None or float(coverage) < min_coverage):
                continue
            haystack = " ".join(
                [
                    str(record.get("id", "")),
                    str(record.get("description", "")),
                    str(record.get("dataset", {}).get("id", "")),
                    str(record.get("dataset", {}).get("name", "")),
                    str(record.get("category", {}).get("name", "")),
                    str(record.get("subcategory", {}).get("name", "")),
                ]
            ).lower()
            if terms and not all(term in haystack for term in terms):
                continue
            out.append(record)
            if len(out) >= limit:
                break
        return out

    def to_dataframe(self, records: list[dict] | None = None) -> pd.DataFrame:
        rows = []
        for record in records if records is not None else self.records:
            rows.append(
                {
                    "id": record.get("id"),
                    "description": record.get("description"),
                    "dataset_id": record.get("dataset", {}).get("id"),
                    "dataset_name": record.get("dataset", {}).get("name"),
                    "category": record.get("category", {}).get("name"),
                    "subcategory": record.get("subcategory", {}).get("name"),
                    "region": record.get("region"),
                    "delay": record.get("delay"),
                    "universe": record.get("universe"),
                    "type": record.get("type"),
                    "coverage": record.get("coverage"),
                    "dateCoverage": record.get("dateCoverage"),
                    "userCount": record.get("userCount"),
                    "alphaCount": record.get("alphaCount"),
                }
            )
        return pd.DataFrame(rows)
