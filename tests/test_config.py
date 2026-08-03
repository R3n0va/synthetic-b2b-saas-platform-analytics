from pathlib import Path
from b2b_saas_platform_analytics.config import deep_merge, load_config
ROOT = Path(__file__).resolve().parents[1]

def test_deep_merge_preserves_nested_values():
    result = deep_merge({"a": {"b": 1, "c": 2}}, {"a": {"b": 3}})
    assert result == {"a": {"b": 3, "c": 2}}

def test_sample_config_inherits_default():
    config = load_config(ROOT / "config/profiles/smoke.yaml")
    assert config["project"]["seed"] == 20260803
    assert config["volumes"]["accounts"] == 250
    assert "geography" in config and "pricing" in config
