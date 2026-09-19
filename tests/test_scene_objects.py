"""Image formation and editable metric clutter, including legacy replay contracts."""

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from pathlab.api import create_app
from pathlab.config import (
    Appearance,
    MapDesign,
    ObjectScatter,
    Pose,
    Scene,
    SceneObject,
)
from pathlab.map_editor import MapRequest, build_scene
from pathlab.scene_objects import object_footprint, scatter_objects
from pathlab.scenarios import generate
from pathlab.simulation import Camera, Renderer


def scene_with(*objects):
    scene = generate("straight", 7)
    scene.objects = list(objects)
    scene.initial_pose = Pose()
    scene.appearance = Appearance(
        surface="plain",
        texture_strength=0,
        shadow=0,
        noise_std=0,
        object_shadows=False,
        marker_enabled=False,
    )
    return scene


def image(scene, pose=None):
    return Renderer(scene).render(pose or scene.initial_pose, 0)


def test_solid_occludes_line_in_actual_rgb_and_object_order_does_not_matter():
    near = SceneObject(
        kind="box",
        x_m=2,
        y_m=0,
        length_m=0.6,
        width_m=0.7,
        height_m=0.8,
        color_rgb=(180, 60, 60),
    )
    far = SceneObject(
        kind="box",
        x_m=3,
        y_m=0,
        length_m=0.6,
        width_m=0.7,
        height_m=0.8,
        color_rgb=(60, 80, 210),
    )
    scene = scene_with(near, far)
    plain, rendered = image(scene_with()), image(scene)
    pixel, visible = Camera(scene.camera).project(np.array([[2.05, 0]]))
    x, y = np.rint(pixel[0]).astype(int)
    assert visible[0] and plain[y, x].max() < 90
    assert rendered[y, x, 0] > rendered[y, x, 1] * 2
    np.testing.assert_array_equal(rendered, image(scene_with(far, near)))


def test_object_projection_tracks_translation_yaw_height_and_size():
    prop = SceneObject(kind="cylinder", x_m=2.5, y_m=0.4, height_m=0.6)
    scene = scene_with(prop)
    reference = image(scene)
    for pose in [Pose(x_m=0.5), Pose(y_m=0.3), Pose(yaw_rad=0.2)]:
        assert np.count_nonzero(reference != image(scene, pose)) > 1000
    resized = scene.model_copy(deep=True)
    resized.objects[0].height_m = 1
    assert np.count_nonzero(reference != image(resized)) > 1000
    raised = scene.model_copy(deep=True)
    raised.camera.height_m = 0.8
    assert np.count_nonzero(reference != image(raised)) > 1000


def test_near_plane_clipping_and_objects_behind_camera_are_well_defined():
    # Keep the same raster extent while adding a solid behind the camera.
    anchors = [SceneObject(kind="box", x_m=1, y_m=side * 2) for side in [-1, 1]]
    empty = scene_with(*anchors)
    behind = scene_with(*anchors, SceneObject(kind="box", x_m=1))
    empty.initial_pose = behind.initial_pose = Pose(x_m=3)
    np.testing.assert_array_equal(image(empty), image(behind))
    clipping = scene_with(
        SceneObject(kind="barrier", x_m=0.22, height_m=1, length_m=0.8)
    )
    result = image(clipping)
    assert result.shape == (360, 640, 3) and result.dtype == np.uint8
    assert np.count_nonzero(result != image(empty)) > 1000


def test_render_and_shadow_replay_are_deterministic_and_editable():
    scene = generate("bend", 19)
    before = image(scene)
    restored = Scene.model_validate_json(scene.model_dump_json())
    np.testing.assert_array_equal(before, image(restored))
    restored.appearance.object_shadows = False
    assert np.count_nonzero(before != image(restored)) > 200
    restored = Scene.model_validate_json(scene.model_dump_json())
    restored.appearance.sun_azimuth_rad = 1.2
    assert np.count_nonzero(before != image(restored)) > 200


@pytest.mark.parametrize("version", ["1", "2"])
def test_legacy_pixels_ignore_new_objects_and_missing_motion_uses_legacy(version):
    scene = scene_with(SceneObject(kind="box", x_m=2))
    scene.render_version = version
    baseline = scene.model_copy(update={"objects": []})
    np.testing.assert_array_equal(image(scene), image(baseline))
    raw = scene.model_dump()
    raw["vehicle"].pop("motion_model")
    assert Scene.model_validate(raw).vehicle.motion_model == "kinematic_v1"
    raw.pop("vehicle")
    assert Scene.model_validate(raw).vehicle.motion_model == "kinematic_v1"
    if version == "1":
        raw.pop("render_version")
        assert Scene.model_validate(raw).render_version == "1"
    assert generate("straight").vehicle.motion_model == "inertial_v2"


def test_scatter_is_repeatable_has_clear_corridor_and_handles_short_paths():
    for family in ["straight", "hairpin", "repeated"]:
        scene = generate(family, 9)
        first = scatter_objects(
            scene.model_copy(update={"objects": []}), ObjectScatter(count=12)
        )
        second = scatter_objects(
            scene.model_copy(update={"objects": []}), ObjectScatter(count=12)
        )
        assert [obj.model_dump() for obj in first] == [
            obj.model_dump() for obj in second
        ]
        path = np.asarray(scene.target_path)
        for obj in first:
            radius = math.hypot(obj.length_m, obj.width_m) / 2
            assert (
                np.linalg.norm(path - [obj.x_m, obj.y_m], axis=1).min() >= radius + 0.65
            )
    short = scene_with()
    short.target_path = [(0, 0), (0.1, 0), (0.2, 0)]
    assert len(scatter_objects(short, ObjectScatter(count=2))) == 2


def test_footprints_use_world_metric_rotation_and_disable_removes_pixels():
    obj = SceneObject(
        kind="barrier", x_m=3, y_m=2, yaw_rad=math.pi / 2, length_m=1, width_m=0.2
    )
    polygon = object_footprint(obj)
    np.testing.assert_allclose(polygon.mean(axis=0), [3, 2])
    np.testing.assert_allclose(np.ptp(polygon, axis=0), [0.2, 1], atol=1e-12)
    obj = SceneObject(kind="cone", x_m=2, enabled=False)
    np.testing.assert_array_equal(image(scene_with(obj)), image(scene_with()))
    assert len(object_footprint(SceneObject(kind="cylinder"))) == 16


def test_new_geometry_is_not_part_of_public_observation():
    from pathlab.sdk import Observation

    scene = generate("straight")
    renderer = Renderer(scene)
    obs = Observation.from_rgb(
        renderer.render(scene.initial_pose, 0),
        episode_id="test",
        frame_id=0,
        timestamp_s=0,
        dt_s=0.05,
        task_hint=scene.task_hint,
        calibration=renderer.camera.calibration(),
    )
    assert "objects" not in obs.model_dump()
    np.testing.assert_array_equal(obs.rgb(), renderer.render(scene.initial_pose, 0))


def test_custom_object_build_save_and_load_api_preserves_pixels(tmp_path):
    request = MapRequest(
        name="物件试验",
        design=MapDesign(waypoints=[(0, 0), (6, 0), (6, 4)], radius_m=1),
        objects=[SceneObject(kind="box", x_m=2, y_m=1, height_m=0.7)],
        scatter=ObjectScatter(count=3),
    )
    with TestClient(create_app(tmp_path)) as client:
        result = client.post("/api/maps/build", json=request.model_dump())
        assert result.status_code == 200, result.text
        built = result.json()
        assert built["scene"]["render_version"] == "3"
        assert len(built["scene"]["objects"]) == 4
        saved = client.post("/api/maps", json=built["scene"])
        assert saved.status_code == 201
        loaded = client.get("/api/maps").json()[0]["scene"]
        assert loaded == built["scene"]
        rebuilt_request = {
            key: loaded[key]
            for key in [
                "name",
                "seed",
                "design",
                "vehicle",
                "camera",
                "appearance",
                "objects",
            ]
        }
        rebuilt = client.post("/api/maps/build", json=rebuilt_request).json()
        assert rebuilt["image"] == built["image"]
        invalid = {
            **rebuilt_request,
            "objects": [{**loaded["objects"][0], "height_m": -1}],
        }
        assert client.post("/api/maps/build", json=invalid).status_code == 422


def test_object_limits_are_validated_before_rendering():
    with pytest.raises(ValidationError):
        SceneObject(height_m=float("nan"))
    with pytest.raises(ValidationError):
        SceneObject(color_rgb=(999, 1, 1))
    request = MapRequest(
        design=MapDesign(waypoints=[(0, 0), (6, 0)]),
        objects=[SceneObject(x_m=3, y_m=2)] * 80,
        scatter=ObjectScatter(count=1),
    )
    with pytest.raises(ValueError, match="80"):
        build_scene(request)
