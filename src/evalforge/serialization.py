"""Stable serialization helpers used for hashes and artifacts."""

import json
from typing import Any

from pydantic import BaseModel


def canonical_json(value: Any) -> str:
    """Return deterministic compact JSON for a JSON-compatible value."""

    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

