from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from evalforge.domain.world import default_world
from evalforge.simulator.engine import Simulator


@given(st.lists(st.sampled_from(["payments-api", "checkout-api"]), max_size=15))
@settings(max_examples=30)
def test_restart_sequences_never_modify_other_services(targets: list[str]) -> None:
    simulator = Simulator(default_world())
    identity_before = simulator.world.services["identity-api"].model_copy(deep=True)
    for index, service_id in enumerate(targets):
        simulator.execute(
            "operator",
            "restart_service",
            {"service_id": service_id, "idempotency_key": f"restart-{index}"},
        )
    assert simulator.world.services["identity-api"] == identity_before
    assert simulator.state_hash == simulator.compute_state_hash(simulator.world)
