"""Canonical world hashing and structural diffs."""

from __future__ import annotations

import hashlib
from typing import cast

from evalforge.domain.trace import StateChange, StateDiff
from evalforge.domain.world import JsonValue, WorldState
from evalforge.serialization import canonical_json


def world_hash(world: WorldState) -> str:
    """Hash all serialized world state deterministically."""

    return hashlib.sha256(canonical_json(world).encode()).hexdigest()


def state_diff(before: WorldState, after: WorldState) -> StateDiff:
    """Produce a sorted leaf-oriented diff of two worlds."""

    left = cast(JsonValue, before.model_dump(mode="json"))
    right = cast(JsonValue, after.model_dump(mode="json"))
    changes: list[StateChange] = []
    _walk_diff(left, right, "", changes)
    return StateDiff(changes=sorted(changes, key=lambda change: change.path))


def _walk_diff(before: JsonValue, after: JsonValue, path: str, changes: list[StateChange]) -> None:
    if before == after:
        return
    if isinstance(before, dict) and isinstance(after, dict):
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}" if path else key
            _walk_diff(before.get(key), after.get(key), child, changes)
        return
    if isinstance(before, list) and isinstance(after, list):
        if before != after:
            changes.append(StateChange(path=path, before=before, after=after))
        return
    changes.append(StateChange(path=path, before=before, after=after))
