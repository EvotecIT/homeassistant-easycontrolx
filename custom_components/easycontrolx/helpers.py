from __future__ import annotations

from typing import Any


def nested_get(data: dict[str, Any] | None, *path: str, default: Any = None) -> Any:
    """Safely read a nested dictionary path."""
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def normalize_optional_string(value: str | None) -> str | None:
    """Normalize an optional string."""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def section_attributes(
    data: dict[str, Any] | None,
    section: str,
    *,
    include_item_count: bool = True,
) -> dict[str, Any]:
    """Build common attributes for a top-level status section."""
    section_data = nested_get(data, section, default={}) or {}
    if not isinstance(section_data, dict):
        return {}

    attributes: dict[str, Any] = {}
    if "summary" in section_data:
        attributes["summary"] = section_data.get("summary")
    if "freshness" in section_data:
        attributes["freshness"] = section_data.get("freshness")
    if include_item_count and "itemCount" in section_data:
        attributes["item_count"] = section_data.get("itemCount")

    return {key: value for key, value in attributes.items() if value is not None}
