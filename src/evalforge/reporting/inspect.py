"""Readable terminal failure timeline from immutable artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import cast


def render_failure_timeline(experiment: Path, episode_id: str) -> str:
    """Render exact trace truth, observations, diffs, and violated rules."""

    episode_dir = experiment / "episodes" / episode_id
    episode = _json(episode_dir / "episode.json")
    verification = _json(episode_dir / "verification.json")
    failure = _json(episode_dir / "failure.json")
    lines = [
        f"EPISODE: {episode_id}",
        f"TASK: {cast(dict[str, object], episode['public_request'])['task']}",
        "TRACE:",
    ]
    for raw in cast(list[dict[str, object]], episode["events"]):
        lines.extend(
            [
                f"  [{raw['step_index']}] {raw['tool_name']} {raw['arguments']}",
                f"    VISIBLE: {raw['visible_observation']}",
                f"    ACTUAL: {raw['actual_outcome']}",
                f"    STATE DIFF: {raw['state_diff']}",
            ]
        )
    lines.append("VIOLATED RULES:")
    for finding in cast(list[dict[str, object]], verification["findings"]):
        if not finding["passed"]:
            lines.append(
                f"  - {finding['rule_id']}: {finding['message']} "
                f"events={finding['evidence_event_ids']}"
            )
    lines.extend(
        [
            f"FAILURE SIGNATURE: {failure['canonical_signature']}",
            f"LINEAGE: parent={failure.get('parent_scenario_id')} "
            f"target={failure.get('parent_failure_signature')}",
        ]
    )
    return "\n".join(lines) + "\n"


def _json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))
