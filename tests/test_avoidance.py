"""Behavioral safety checks for opt-in avoidance and bounded private scoring."""

import math

import numpy as np
import pytest

from algorithms.avoidance import AvoidingPursuit
from algorithms.modular.algorithm import TemporalPursuit
from algorithms.modular.obstacles import (
    DetourPlanner,
    Obstacle,
    ObstacleCamera,
    ObstacleMemory,
    path_curvature,
)
from algorithms.modular.vision import BirdEye
from pathlab.config import Pose, SceneObject
from pathlab.evaluation import Evaluator
from pathlab.map_editor import MapRequest, build_scene
from pathlab.config import MapDesign
from pathlab.sdk import Observation
from pathlab.simulation import Renderer, VehicleState


def obstacle_scene(*, distractor=False, roadside=False):
    scene = build_scene(MapRequest(design=MapDesign(waypoints=[(0, 0), (9, 0)])))
    scene.initial_pose = Pose()
    scene.objects = [
        SceneObject(
            kind="box",
            x_m=3,
            y_m=2 if roadside else 0,
            length_m=0.4,
            width_m=0.35,
            height_m=0.45,
            color_rgb=(162, 124, 83),
        )
    ]
    if distractor:
        scene.distractors = [[(0, 0.65), (9, 0.65)]]
    return scene


def oracle_detour(scene, *, offset=0.65, start=1, end=5):
    evaluator = Evaluator(scene)
    for index, x in enumerate(np.arange(0, 9, 0.025)):
        phase = np.clip((x - start) / (end - start), 0, 1)
        y = offset * math.sin(math.pi * phase) ** 2
        slope = offset * math.pi / (end - start) * math.sin(2 * math.pi * phase)
        evaluator.update(
            VehicleState(x_m=x, y_m=y, yaw_rad=math.atan(slope)),
            (index + 1) * scene.dt_s,
        )
        if evaluator.done_reason:
            break
    return evaluator


def test_detour_around_blockage_must_rejoin_original_route():
    evaluator = oracle_detour(obstacle_scene())
    assert evaluator.done_reason == "success"
    assert evaluator.collisions == evaluator.switches == []


def test_detour_permission_never_allows_following_neighboring_line():
    evaluator = oracle_detour(obstacle_scene(distractor=True))
    assert evaluator.done_reason == "illegal_switch"
    assert evaluator.progress < 4


def test_roadside_object_cannot_excuse_arbitrary_offroad_driving():
    evaluator = oracle_detour(obstacle_scene(roadside=True))
    assert evaluator.avoidance_zones == []
    assert evaluator.done_reason == "deviation"


def test_collision_is_still_terminal_inside_detour_zone():
    evaluator = oracle_detour(obstacle_scene(), offset=0)
    assert evaluator.done_reason == "collision"


def test_original_line_follower_and_avoidance_have_separate_instances():
    scene = build_scene(MapRequest(design=MapDesign(waypoints=[(0, 0), (9, 0)])))
    renderer = Renderer(scene)
    obs = Observation.from_rgb(
        renderer.render(scene.initial_pose, 0),
        episode_id="separate",
        frame_id=0,
        timestamp_s=0,
        dt_s=scene.dt_s,
        calibration=renderer.camera.calibration(),
        task_hint=scene.task_hint,
    )
    baseline, avoiding = TemporalPursuit(), AvoidingPursuit()
    for policy in (baseline, avoiding):
        policy.initialize({}, {"vehicle_limits": scene.vehicle.model_dump()})
        policy.reset(obs, obs.task_hint)
    assert not hasattr(baseline.tracker, "obstacles")
    assert hasattr(avoiding.tracker, "obstacles")
    first, second = baseline.step(obs), avoiding.step(obs)
    assert "avoidance_active" not in first.debug
    assert not second.debug["avoidance_active"]
    assert second.debug["observed_obstacles"] == []
    assert first.action == second.action


@pytest.mark.parametrize(
    "kind,color", [("cone", (232, 108, 38)), ("box", (162, 124, 83))]
)
def test_rgb_ground_contact_localizes_solid_without_scene_metadata(kind, color):
    scene = obstacle_scene()
    scene.objects[0] = SceneObject(kind=kind, x_m=3, color_rgb=color)
    renderer = Renderer(scene)
    camera, memory = BirdEye(renderer.camera.calibration()), ObstacleMemory()
    for frame in range(5):
        if frame:
            memory.advance(np.array([0.05, 0]), 0)
        memory.observe(
            renderer.render(Pose(x_m=frame * 0.05), frame),
            camera,
            scene.task_hint,
            0.05,
        )
    assert len(memory.items) == 1
    assert np.linalg.norm(memory.items[0].center - [2.8, 0]) < 0.2


def test_neighbor_memory_survives_leaving_camera_and_transforms_with_motion():
    planner = DetourPlanner(obstacle_scene().vehicle.model_dump())
    planner.road_memory = np.array([[2.0, -0.55], [3.0, -0.55]])
    planner.advance(np.array([0.2, 0.1]), math.pi / 2)
    np.testing.assert_allclose(planner.road_memory, [[-0.65, -1.8], [-0.65, -2.8]])


def test_visibility_probe_respects_turning_radius_and_neighboring_line():
    from algorithms.modular.obstacles import Obstacle

    limits = obstacle_scene().vehicle.model_dump()
    planner = DetourPlanner(limits)
    route = np.c_[np.linspace(0.5, 4, 80), np.zeros(80)]
    neighbor = route + [0, -0.55]
    planner.road_memory = neighbor
    blocker = Obstacle(np.array([3.0, 0]), 0.25)
    path = planner.peek_path(route, [(None, route)], [blocker], blocker)
    assert path is not None and path[-1, 1] > 0
    assert (
        path_curvature(path).max()
        < math.tan(limits["max_steering_rad"]) / limits["wheelbase_m"]
    )
    planner.limits = {**limits, "max_steering_rad": 0.1}
    assert planner.peek_path(route, [(None, route)], [blocker], blocker) is None


def test_plan_cannot_release_identity_using_only_predicted_continuation():
    from algorithms.modular.obstacles import Obstacle

    planner = DetourPlanner(obstacle_scene().vehicle.model_dump())
    planner.reference = planner.path = np.c_[np.linspace(0, 2, 45), np.zeros(45)]
    planner.blocking = Obstacle(np.array([-0.5, 0]), 0.2)
    _, active = planner.command_path(planner.reference, [], [], 0.05)
    assert active and planner.reference is not None
    planner.rejoin_observed = True
    _, active = planner.command_path(planner.reference, [], [], 0.05)
    assert not active and planner.reference is None


def test_roadside_cone_does_not_trigger_detour_on_a_clear_lane():
    from algorithms.modular.obstacles import Obstacle

    planner = DetourPlanner(obstacle_scene().vehicle.model_dump())
    path = np.c_[np.linspace(0, 5, 100), np.zeros(100)]
    _, active = planner.command_path(
        path, [], [Obstacle(np.array([2.86, 0.38]), 0.226)], 0.05
    )
    assert not active


def test_cone_white_band_does_not_create_a_faraway_phantom_obstacle():
    scene = obstacle_scene()
    scene.objects = [SceneObject(kind="cone", x_m=2, y_m=0.9)]
    renderer, memory = Renderer(scene), ObstacleMemory()
    memory.observe(
        renderer.render(Pose(), 0),
        BirdEye(renderer.camera.calibration()),
        scene.task_hint,
        0.05,
    )
    assert len(memory.items) == 1
    assert np.linalg.norm(memory.items[0].center - [2, 0.9]) < 0.2


def test_timestamp_error_cannot_be_overridden_by_an_active_detour():
    scene = obstacle_scene()
    renderer = Renderer(scene)
    obs = Observation.from_rgb(
        renderer.render(Pose(), 0),
        episode_id="time-order",
        frame_id=0,
        timestamp_s=1,
        dt_s=0.05,
        calibration=renderer.camera.calibration(),
        task_hint=scene.task_hint,
    )
    policy = AvoidingPursuit()
    policy.initialize({}, {"vehicle_limits": scene.vehicle.model_dump()})
    policy.reset(obs, obs.task_hint)
    policy.tracker.planner.path = np.array([[0, 0], [1, 0], [2, 0]])
    result = policy.step(obs.model_copy(update={"timestamp_s": 0}))
    assert result.status == "ERROR"
    assert result.action is None


def test_upright_cone_cannot_supply_a_ground_plane_road_continuation():
    scene = obstacle_scene()
    scene.objects[0] = SceneObject(kind="cone", x_m=3, color_rgb=(232, 108, 38))
    renderer = Renderer(scene)
    rgb = renderer.render(Pose(), 0)
    camera = ObstacleCamera(renderer.camera.calibration())
    memory = ObstacleMemory()
    memory.observe(rgb, camera, scene.task_hint, scene.dt_s)
    camera.image_boxes = memory.image_boxes
    components, _, _ = camera.extract(rgb, scene.task_hint)
    assert len(memory.items) == 1 and components
    # The visible part of this straight line stays straight; the cone's
    # projected rubber base and band contours cannot become branches.
    points = np.vstack([metric for _, metric in components])
    assert np.max(np.abs(points[:, 1])) < 0.08
    assert points[:, 0].min() < 1 and 2.4 < points[:, 0].max() < 3


def test_visible_stale_road_projection_is_removed_but_blind_neighbor_survives():
    scene = obstacle_scene()
    planner = DetourPlanner(scene.vehicle.model_dump())
    camera = BirdEye(Renderer(scene).camera.calibration())
    ghost, blind = np.array([2.0, 0.4]), np.array([0.2, -0.4])
    planner.road_memory = np.array([ghost, blind])
    observed = np.c_[np.linspace(1, 3, 30), np.zeros(30)]
    planner.remember_roads([(None, observed)], camera)
    assert np.min(np.linalg.norm(planner.road_memory - ghost, axis=1)) > 0.3
    assert np.min(np.linalg.norm(planner.road_memory - blind, axis=1)) < 1e-8


def test_own_recent_blind_curve_is_not_an_unrelated_neighbor():
    planner = DetourPlanner(obstacle_scene().vehicle.model_dump())
    near_curve = np.array([[0.2, 0.15], [0.3, 0.19], [0.4, 0.2]])
    neighbor = near_curve + [0, 0.45]
    planner.remember_target(near_curve, 0.05)
    planner.road_memory = np.vstack([near_curve, neighbor])
    reference = np.c_[np.linspace(0.6, 3, 30), np.zeros(30)]
    other = planner.other_roads(reference)
    np.testing.assert_allclose(other, neighbor)


def test_curved_approach_can_find_a_tangent_aligned_side_view():
    limits = obstacle_scene().vehicle.model_dump()
    planner = DetourPlanner(limits)
    angle = 0.5
    tangent = np.array([math.cos(angle), math.sin(angle)])
    normal = np.array([-tangent[1], tangent[0]])
    route = np.linspace(0.7, 1.7, 40)[:, None] * tangent - 0.15 * normal
    blocker = Obstacle(2.0 * tangent - 0.15 * normal, 0.24)
    planner.road_memory = route - 0.55 * normal
    path = planner.peek_path(route, [], [blocker], blocker)
    assert path is not None
    assert np.min(np.linalg.norm(path - blocker.center, axis=1)) > blocker.radius + 0.3
    assert (
        path_curvature(path).max()
        < math.tan(limits["max_steering_rad"]) / limits["wheelbase_m"]
    )
    end_heading = path[-1] - path[-2]
    assert end_heading @ tangent / np.linalg.norm(end_heading) > 0.98


def test_temporarily_lost_continuation_does_not_discard_locked_identity(monkeypatch):
    planner = DetourPlanner(obstacle_scene().vehicle.model_dump())
    planner.path = np.c_[np.linspace(0, 2, 30), np.zeros(30)]
    planner.reference = planner.path + [0, -0.6]
    saved_path, saved_reference = planner.path.copy(), planner.reference.copy()
    planner.peeking = planner.peek_attempted = True
    planner.blocking = Obstacle(np.array([0.8, -0.6]), 0.25)
    observed = np.c_[np.linspace(0, 4, 60), np.full(60, -0.6)]
    responses = iter([observed, None])
    monkeypatch.setattr(planner, "extend", lambda *args: next(responses))
    _, active = planner.command_path(observed, [], [planner.blocking], 0.05)
    assert active and planner.peeking
    np.testing.assert_array_equal(planner.path, saved_path)
    np.testing.assert_array_equal(planner.reference, saved_reference)
