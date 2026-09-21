import json
from pathlib import Path


def load_config():
    # Locate the repository root.
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "config.json"

    with config_path.open(encoding="utf-8") as f:
        config = json.load(f)

    # Resolve relative paths from the repository root.
    for name, value in config["paths"].items():
        path = Path(value).expanduser()
        if not path.is_absolute():
            path = project_root / path
        config["paths"][name] = path.resolve()

    return config