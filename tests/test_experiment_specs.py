from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT_FILES = sorted((ROOT / "experiments").glob("exp_*/experiment.yaml"))


def test_four_experiment_specifications_are_present():
    assert len(EXPERIMENT_FILES) == 4


@pytest.mark.parametrize("path", EXPERIMENT_FILES, ids=lambda path: path.parent.name)
def test_experiment_specification_is_decision_ready(path):
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(payload) >= {
        "experiment_id",
        "name",
        "unit",
        "hypothesis",
        "primary_metric",
        "guardrails",
        "segments",
        "decision_rule",
    }
    assert payload["hypothesis"].strip()
    assert payload["guardrails"]
    assert payload["decision_rule"].strip()
