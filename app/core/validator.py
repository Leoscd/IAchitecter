import json
from pathlib import Path

import jsonschema

from app.core.errors import ValidationError

_schema_cache: dict[str, dict] = {}


def load_schema(schema_name: str) -> dict:
    if schema_name not in _schema_cache:
        schema_path = Path(__file__).parent.parent / "schemas" / f"{schema_name}.json"
        with open(schema_path) as f:
            _schema_cache[schema_name] = json.load(f)
    return _schema_cache[schema_name]


def validate_input(data: dict, schema_name: str) -> None:
    schema = load_schema(schema_name)
    try:
        jsonschema.validate(instance=data, schema=schema)
    except jsonschema.ValidationError as exc:
        raise ValidationError(f"Schema '{schema_name}' rechazó el input: {exc.message}") from exc
