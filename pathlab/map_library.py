"""Stable map identities and human-readable, collision-free display names."""

import json
from pathlib import Path
import re

from .storage import write_json


def unique_name(requested: str, occupied: set[str]) -> str:
    name = requested.strip()[:80] or "我的地图"
    keys = {item.casefold() for item in occupied}
    if name.casefold() not in keys:
        return name
    stem = re.sub(r"\(\d+\)$", "", name).rstrip() or "我的地图"
    index = 1
    while True:
        suffix = f"({index})"
        candidate = stem[: 80 - len(suffix)].rstrip() + suffix
        if candidate.casefold() not in keys:
            return candidate
        index += 1


def read_maps(root: Path) -> list[dict]:
    return [
        {"id": path.stem, "scene": json.loads(path.read_text(encoding="utf-8"))}
        for path in sorted((root / "maps").glob("*.json"))
    ]


def normalize_names(root: Path) -> list[dict]:
    """One-time repair on startup; preserve IDs, geometry and existing suffixes."""
    paths = sorted(
        (root / "maps").glob("*.json"), key=lambda p: (p.stat().st_mtime_ns, p.name)
    )
    scenes = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in paths]
    occupied = {scene["name"].strip()[:80] or "我的地图" for _, scene in scenes}
    seen, changes = set(), []
    for path, scene in scenes:
        name = scene["name"].strip()[:80] or "我的地图"
        if name.casefold() in seen:
            name = unique_name(name, occupied)
        if name != scene["name"]:
            changes.append({"id": path.stem, "old_name": scene["name"], "name": name})
            write_json(path, {**scene, "name": name})
        seen.add(name.casefold())
        occupied.add(name)
    return changes
