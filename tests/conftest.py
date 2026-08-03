from __future__ import annotations
import sys
from pathlib import Path
import pytest
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data_generator" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
from b2b_saas_platform_analytics.config import load_config
from b2b_saas_platform_analytics.generator import generate_dataset

@pytest.fixture(scope="session")
def sample_config():
    return load_config(ROOT / "config/profiles/smoke.yaml", ROOT / "config/scenarios/baseline.yaml")

@pytest.fixture(scope="session")
def generated_dataset(sample_config):
    return generate_dataset(sample_config)
