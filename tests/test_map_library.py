import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from pathlab.api import create_app
from pathlab.map_library import normalize_names, unique_name
from pathlab.scenarios import generate
from pathlab.storage import write_json


def test_windows_style_suffixes_and_length():
    assert unique_name("0920", {"0920"}) == "0920(1)"
    assert unique_name("0920", {"0920", "0920(1)"}) == "0920(2)"
    assert unique_name("0920(1)", {"0920", "0920(1)"}) == "0920(2)"
    assert unique_name("Map", {"map"}) == "Map(1)"
    name = "图" * 80
    assert len(unique_name(name, {name})) == 80
    assert unique_name("0920", {"0920", "0920(2)"}) == "0920(1)"


def test_existing_duplicates_keep_ids_geometry_and_reserved_suffixes(tmp_path):
    folder = tmp_path / "maps"
    folder.mkdir()
    scene = generate("straight").model_dump(mode="json")
    for i, name in enumerate(["0920", "0920", "0920(1)"]):
        write_json(folder / f"{i:032x}.json", {**scene, "name": name})
    changes = normalize_names(tmp_path)
    assert len(changes) == 1 and changes[0]["name"] == "0920(2)"
    assert normalize_names(tmp_path) == []
    for path in folder.glob("*.json"):
        restored = json.loads(path.read_text())
        assert {**restored, "name": scene["name"]} == scene


def test_concurrent_save_returns_unique_names_and_restart_preserves_them(tmp_path):
    scene = generate("straight").model_dump()
    scene["name"] = "0920"
    with TestClient(create_app(tmp_path)) as client:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(
                pool.map(lambda _: client.post("/api/maps", json=scene), range(4))
            )
        assert all(result.status_code == 201 for result in results)
        names = {result.json()["scene"]["name"] for result in results}
        assert names == {"0920", "0920(1)", "0920(2)", "0920(3)"}
        ids = {result.json()["id"] for result in results}
    with TestClient(create_app(tmp_path)) as client:
        saved = client.get("/api/maps").json()
        assert {item["id"] for item in saved} == ids
        assert {item["scene"]["name"] for item in saved} == names


def test_challenge_install_is_valid_repeatable_and_preserves_user_maps(tmp_path):
    from scripts.install_challenges import install

    maps = tmp_path / "maps"
    maps.mkdir()
    user = generate("straight").model_dump()
    user["name"] = "0920挑战·套圈占道"
    destination = maps / "user.json"
    write_json(destination, user)
    original = destination.read_bytes()
    result = install(tmp_path)
    assert len(result) == 5
    assert all(row["status"] == "installed" for row in result)
    assert any(row["name"] == user["name"] + "(1)" for row in result)
    assert destination.read_bytes() == original
    assert all(row["status"] == "already_installed" for row in install(tmp_path))
    assert len(list(maps.glob("*.json"))) == 6
