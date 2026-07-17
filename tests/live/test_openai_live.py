from __future__ import annotations

import os

import pytest


@pytest.mark.live
def test_live_environment_is_explicitly_opted_in() -> None:
    assert os.getenv("OPENAI_API_KEY"), "Set OPENAI_API_KEY before explicitly running live tests"
