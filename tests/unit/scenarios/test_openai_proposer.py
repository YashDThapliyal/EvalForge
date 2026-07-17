from __future__ import annotations

from evalforge.scenarios.manual import build_manual_scenario
from evalforge.scenarios.openai_proposer import OpenAIScenarioProposer


class FakeResponses:
    def __init__(self, output: str):
        self.output = output
        self.kwargs: dict[str, object] = {}

    def create(self, **kwargs: object) -> dict[str, object]:
        self.kwargs = kwargs
        return {"output_text": self.output}


class FakeClient:
    def __init__(self, output: str):
        self.responses = FakeResponses(output)


def test_live_proposer_requests_schema_constrained_data_only_output() -> None:
    scenario = build_manual_scenario("bad_deployment", 0)
    client = FakeClient(scenario.model_dump_json())
    proposed = OpenAIScenarioProposer(client=client, model="fake").propose(2, 7)
    assert proposed == scenario
    text = client.responses.kwargs["text"]
    assert isinstance(text, dict)
    assert text["format"]["type"] == "json_schema"  # type: ignore[index]
    assert "schema" in text["format"]  # type: ignore[operator]
    assert "failure" not in str(client.responses.kwargs["input"]).lower()
