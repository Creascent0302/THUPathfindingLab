"""Saved-case evaluation preserves the user's physical and visual problem."""

from scripts.evaluate_algorithms import evaluation_scene
from pathlab.scenarios import generate


def test_saved_scene_preserves_geometry_camera_and_legacy_physics(tmp_path):
    scene = generate("parallel", 37)
    scene.vehicle.motion_model = "kinematic_v1"
    scene.render_version = "2"
    scene.camera.pitch_down_rad = 0.52
    scene.camera.width, scene.camera.height = 640, 360
    original = scene.model_dump_json()
    source = tmp_path / "saved.json"
    source.write_text(original)
    case = evaluation_scene("custom", 6001, "test", "core", source)
    expected = scene.model_copy(update={"seed": 6001, "split": "test"})
    assert case == expected
    assert source.read_text() == original
