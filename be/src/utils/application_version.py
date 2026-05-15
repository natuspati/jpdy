import tomllib
from pathlib import Path


def get_version() -> str:
    toml_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    with open(toml_path, "rb") as f:
        data = tomllib.load(f)
    return data["project"]["version"]
