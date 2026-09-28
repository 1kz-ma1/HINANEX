from pathlib import Path

from pydantic import BaseModel


def write_model_json(model: BaseModel, output_path: str | Path) -> Path:
    """Write a Pydantic model as UTF-8 JSON and return the path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(model.model_dump_json(indent=2), encoding="utf-8")
    return path
