from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .alpha_template import ALPHA_SPACE, ALPHA_TEMPLATE
from .data_field_catalog import DataFieldCatalog
from .operator_catalog import OperatorCatalog

if TYPE_CHECKING:
    from .template_schema import GeneratedTemplateSpec


@dataclass
class ValidationReport:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


FIELD_PLACEHOLDERS = {"<funds_data>", "<debt_data>"}
OPERATOR_PLACEHOLDERS = {
    "<group_neut_op>",
    "<ts_decay_op>",
    "<ts_neut_op>",
    "<diff_op>",
}
GROUP_VALUES = {"market", "sector", "industry", "subindustry", "country"}
_CALL_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_PLACEHOLDER_RE = re.compile(r"<[^<>]+>")


def _static_operator_calls(template: str) -> set[str]:
    return set(_CALL_RE.findall(template))


def validate_template(
    template: str = ALPHA_TEMPLATE,
    alpha_space: dict[str, list[str]] = ALPHA_SPACE,
    fields: DataFieldCatalog | None = None,
    operators: OperatorCatalog | None = None,
) -> ValidationReport:
    """Validate the original hand-written template."""
    fields = fields or DataFieldCatalog()
    operators = operators or OperatorCatalog()
    errors: list[str] = []
    warnings: list[str] = []

    for placeholder in alpha_space:
        if placeholder not in template:
            warnings.append(f"Placeholder {placeholder} is in ALPHA_SPACE but not used by the template")

    field_ids = fields.ids()
    for placeholder in FIELD_PLACEHOLDERS:
        for value in alpha_space.get(placeholder, []):
            if value not in field_ids:
                errors.append(f"Unknown GLB data field: {value} ({placeholder})")

    operator_names = operators.names()
    for placeholder in OPERATOR_PLACEHOLDERS:
        for value in alpha_space.get(placeholder, []):
            if value not in operator_names:
                errors.append(f"Unknown REGULAR operator: {value} ({placeholder})")

    for value in _static_operator_calls(template):
        if value not in operator_names:
            errors.append(f"Template uses operator not present in catalog: {value}")

    return ValidationReport(errors=errors, warnings=warnings)


def validate_generated_template(
    spec: "GeneratedTemplateSpec",
    fields: DataFieldCatalog | None = None,
    operators: OperatorCatalog | None = None,
    allowed_field_ids: set[str] | None = None,
    allowed_operator_names: set[str] | None = None,
) -> ValidationReport:
    """Validate a model-generated template against the real WQB catalogs.

    The LLM can only propose candidates; this function is the hard gate before the
    generated template can reach the genetic search or BRAIN simulation.
    """
    fields = fields or DataFieldCatalog()
    operators = operators or OperatorCatalog()
    errors: list[str] = []
    warnings: list[str] = []
    field_ids = fields.ids()
    operator_names = operators.names()

    if not spec.expression_template.strip():
        errors.append("Generated expression_template is empty")
        return ValidationReport(errors=errors, warnings=warnings)

    seen_placeholders: set[str] = set()
    for variable in spec.variables:
        p = variable.placeholder
        if p in seen_placeholders:
            errors.append(f"Duplicate variable placeholder: {p}")
        seen_placeholders.add(p)
        if p not in spec.expression_template:
            warnings.append(f"Variable {p} is defined but unused")
        if not variable.values:
            errors.append(f"Variable {p} has no candidate values")
            continue

        kind = variable.kind.upper()
        if kind == "FIELD":
            field_types: set[str] = set()
            for value in variable.values:
                if value not in field_ids:
                    errors.append(f"Unknown GLB data field: {value} ({p})")
                    continue
                if allowed_field_ids is not None and value not in allowed_field_ids:
                    errors.append(f"Field was not in the retrieved allowed shortlist: {value} ({p})")
                record = fields.get(value) or {}
                field_types.add(str(record.get("type", "")).upper())
            field_types.discard("")
            if len(field_types) > 1:
                errors.append(
                    f"FIELD variable {p} mixes incompatible field types: {sorted(field_types)}"
                )
            if field_types == {"VECTOR"}:
                vector_wrapped = any(
                    re.search(rf"\b{name}\s*\(\s*{re.escape(p)}\s*\)", spec.expression_template)
                    for name in ("vec_avg", "vec_sum", "vec_min", "vec_max", "vec_stddev", "vec_range", "vec_count")
                )
                if not vector_wrapped:
                    errors.append(
                        f"VECTOR field placeholder {p} must be reduced with a vec_* operator before matrix operations"
                    )
        elif kind == "OPERATOR":
            for value in variable.values:
                if value not in operator_names:
                    errors.append(f"Unknown REGULAR operator: {value} ({p})")
                elif allowed_operator_names is not None and value not in allowed_operator_names:
                    errors.append(f"Operator was not in the retrieved allowed shortlist: {value} ({p})")
        elif kind == "GROUP":
            for value in variable.values:
                if value not in GROUP_VALUES:
                    warnings.append(
                        f"Unrecognized group literal {value!r} in {p}; BRAIN may still support it."
                    )
        elif kind == "PARAMETER":
            for value in variable.values:
                if not str(value).strip():
                    errors.append(f"Empty parameter value in {p}")
        else:
            errors.append(f"Unsupported variable kind {variable.kind!r} in {p}")

    unresolved_defs = set(_PLACEHOLDER_RE.findall(spec.expression_template)) - seen_placeholders
    for p in sorted(unresolved_defs):
        errors.append(f"Expression contains placeholder with no variable definition: {p}")

    # Every literal function call must be a real REGULAR operator. Operator placeholders
    # such as <op>(...) are not matched here and are checked via kind=OPERATOR above.
    for name in sorted(_static_operator_calls(spec.expression_template)):
        if name not in operator_names:
            errors.append(f"Expression uses unknown REGULAR operator: {name}")
        elif allowed_operator_names is not None and name not in allowed_operator_names:
            errors.append(f"Expression uses operator outside retrieved shortlist: {name}")

    return ValidationReport(errors=errors, warnings=warnings)
