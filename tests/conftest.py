from __future__ import annotations

import socket

import pytest


@pytest.fixture(autouse=True)
def forbid_unmarked_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail fast if a default test attempts external socket I/O."""

    def denied(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise AssertionError("Network access is forbidden in default EvalForge tests")

    monkeypatch.setattr(socket.socket, "connect", denied)
