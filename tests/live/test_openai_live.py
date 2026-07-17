from __future__ import annotations

import os

import pytest


@pytest.mark.live
@pytest.mark.parametrize("variable", ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"])
def test_live_environment_is_explicitly_opted_in(variable: str) -> None:
    assert os.getenv(variable), f"Set {variable} before explicitly running live tests"
