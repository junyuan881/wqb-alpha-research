from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AlphaStage(str, Enum):
    NONE = "none"
    PENDING = "pending"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Alpha:
    name: str
    payload: dict[str, Any]
    stage: AlphaStage = AlphaStage.PENDING
    result: dict[str, Any] = field(default_factory=dict)

    @property
    def filename(self) -> str:
        if "/" in self.name or "\\" in self.name:
            raise ValueError("Alpha name cannot contain path separators")
        return f"{self.name}.json"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "payload": self.payload,
            "stage": self.stage.value,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Alpha":
        return cls(
            name=data["name"],
            payload=data["payload"],
            stage=AlphaStage(data.get("stage", AlphaStage.PENDING.value)),
            result=data.get("result", {}),
        )
