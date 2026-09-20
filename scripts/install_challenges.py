"""Install the frozen 0920 challenge set without overwriting any saved map."""

# ruff: noqa: E402

import argparse
import hashlib
import json
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pathlab.config import Scene
from pathlab.map_library import normalize_names, read_maps, unique_name
from pathlab.scenarios import validate_scene
from pathlab.storage import write_json

CATALOG = ROOT / "artifacts/algorithms/0920-hard/catalog.json"


def install(root: Path) -> list[dict]:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    # Validate the entire input set before changing the user's map library.
    scenes = []
    for entry in catalog:
        source = CATALOG.parent / "scenes" / entry["file"]
        scene = Scene.model_validate_json(source.read_text(encoding="utf-8"))
        errors = validate_scene(scene)
        if errors:
            raise ValueError(f"{source.name}: {'; '.join(errors)}")
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        identity = uuid.uuid5(uuid.NAMESPACE_URL, f"pathlab:0920:{digest}").hex
        scenes.append((identity, scene))
    (root / "maps").mkdir(parents=True, exist_ok=True)
    normalize_names(root)
    occupied = {item["scene"]["name"] for item in read_maps(root)}
    installed = []
    for identity, scene in scenes:
        destination = root / "maps" / f"{identity}.json"
        if destination.exists():
            installed.append({"id": identity, "status": "already_installed"})
            continue
        scene.name = unique_name(scene.name, occupied)
        write_json(destination, scene.model_dump())
        occupied.add(scene.name)
        installed.append({"id": identity, "name": scene.name, "status": "installed"})
    return installed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT / "artifacts")
    print(json.dumps(install(parser.parse_args().root), ensure_ascii=False, indent=2))
