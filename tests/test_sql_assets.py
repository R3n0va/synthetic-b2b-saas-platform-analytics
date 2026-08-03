from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def test_required_sql_layers_exist():
    for directory in ["00_admin", "02_core", "03_marts", "04_analytics", "05_quality"]:
        files = list((ROOT / "sql" / directory).glob("*.sql"))
        assert files, directory

def test_sql_assets_do_not_use_container_specific_paths():
    content = "\n".join(path.read_text(encoding="utf-8").lower() for path in (ROOT / "sql").rglob("*.sql"))
    assert "docker" not in content
    assert "/var/lib/postgresql" not in content
