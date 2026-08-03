from pathlib import Path
import yaml
from b2b_saas_platform_analytics.schema import TABLE_SCHEMAS
ROOT = Path(__file__).resolve().parents[1]

def test_contract_catalog_matches_schema_registry():
    catalog = yaml.safe_load((ROOT / "contracts/catalog.yaml").read_text(encoding="utf-8"))
    listed = set(catalog["tables"] if isinstance(catalog["tables"], list) else catalog["tables"].keys())
    assert listed == set(TABLE_SCHEMAS)

def test_every_table_has_contract_file():
    for table in TABLE_SCHEMAS:
        assert (ROOT / "contracts" / f"{table}.yaml").exists()
