"""Learning-data integrity and real episode-start supervision regressions."""

import json

import numpy as np
import pytest


def test_marker_input_is_versioned_and_preserves_legacy_preprocessing():
    pytest.importorskip("torch")
    from algorithms.learning.model import image_input
    from pathlab.sdk import TaskHint

    rgb = np.full((96, 160, 3), 210, np.uint8)
    rgb[30:40, 70:90] = [34, 160, 94]
    rgb[60:70, 70:90] = [39, 48, 57]
    legacy = image_input(rgb, TaskHint())
    marked = image_input(rgb, TaskHint(), input_version="rgb_marker_v2")
    np.testing.assert_array_equal(legacy[..., :3], marked[..., :3])
    assert not legacy[..., 3].any()
    assert (marked[30:40, 70:90, 3] == 255).all()
    assert not marked[60:70, :, 3].any()


def test_episode_start_is_supervised_but_cropped_sequences_warm_up(tmp_path):
    pytest.importorskip("torch")
    from algorithms.learning.train import Sequences

    count = 16
    np.savez(
        tmp_path / "example.npz",
        images=np.zeros((count, 96, 160, 4), np.uint8),
        context=np.zeros((count, 5), np.float32),
        actions=np.zeros((count, 2), np.float32),
        visible=np.ones(count, np.float32),
    )
    (tmp_path / "manifest.json").write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "family": "complex_coil_inertial_v2",
                        "seed": 0,
                        "split": "development",
                        "file": "example.npz",
                        "frames": count,
                    }
                ]
            }
        )
    )
    data = Sequences([tmp_path], "development", length=8, acquisition_weight=3)
    assert data[0][-1].tolist() == [3] * 8
    assert data[1][-1].tolist() == [0, 0] + [3] * 6


def test_custom_collection_refuses_test_cases(tmp_path, monkeypatch):
    pytest.importorskip("torch")
    from algorithms.learning import custom_data
    from pathlab.scenarios import generate

    source = tmp_path / "held-out.json"
    source.write_text(generate("straight", 6001, split="test").model_dump_json())
    monkeypatch.setattr(
        "sys.argv",
        [
            "custom_data",
            "--data",
            str(tmp_path / "data"),
            "--scene-files",
            str(source),
        ],
    )
    with pytest.raises(ValueError, match="保留测试场景"):
        custom_data.main()


@pytest.mark.parametrize("kind", ["coil", "parallel_curve"])
@pytest.mark.parametrize("motion", ["kinematic_v1", "inertial_v2"])
def test_complex_geometry_is_deterministic_and_independent(kind, motion):
    pytest.importorskip("torch")
    from algorithms.learning.custom_data import custom_scene
    from pathlab.scenarios import validate_scene

    first = custom_scene(kind, 201, motion, "validation")
    repeat = custom_scene(kind, 201, motion, "validation")
    other = custom_scene(kind, 202, motion, "validation")
    assert first.model_dump() == repeat.model_dump()
    assert first.target_path != other.target_path
    assert first.vehicle.motion_model == motion
    assert validate_scene(first) == []
    if kind == "parallel_curve":
        assert first.distractors
    else:
        assert len(first.target_path) > 700
