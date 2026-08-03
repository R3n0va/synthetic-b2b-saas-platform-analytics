from __future__ import annotations

from pathlib import Path

import yaml

from .schema import TABLE_SCHEMAS


def write_contracts(output_dir: str | Path) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    catalog = {"version": 1, "tables": {}}
    for table_name, schema in TABLE_SCHEMAS.items():
        payload = {
            "table": table_name,
            "grain": "One row per " + " and ".join(schema.get("primary_key", ["record"])),
            "primary_key": schema.get("primary_key", []),
            "foreign_keys": schema.get("foreign_keys", []),
            "columns": [
                {"name": column, "type": logical_type, "nullable": column not in schema.get("primary_key", [])}
                for column, logical_type in schema["columns"].items()
            ],
        }
        (output / f"{table_name}.yaml").write_text(
            yaml.safe_dump(payload, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
        )
        catalog["tables"][table_name] = {"contract": f"{table_name}.yaml"}
    (output / "catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8", newline="\n"
    )
