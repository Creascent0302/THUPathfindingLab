"""Replay the frozen v1 policies without replacing installed v2 source files."""

from concurrent.futures import ProcessPoolExecutor
import hashlib
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def replay(job):
    for name, filename in (
        ("algorithms.modular.obstacles", "obstacles.py"),
        ("algorithms.avoidance", "avoidance.py"),
    ):
        spec = importlib.util.spec_from_file_location(
            name, HERE / "baseline-code" / filename
        )
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    from scripts.evaluate_algorithms import evaluate

    return evaluate(job)


if __name__ == "__main__":
    from pathlab.config import Scene
    from pathlab.evaluation import EVALUATOR_VERSION, THRESHOLDS
    from pathlab.storage import environment, write_json
    from scripts.evaluate_algorithms import write_report

    output = ROOT / "artifacts/challenge-search/avoidance-v1-user"
    scene_file = HERE / "scenes/user-close-obstacles.json"
    scene = Scene.model_validate_json(scene_file.read_text())
    algorithms = ["temporal_pursuit_avoidance", "temporal_mpc_avoidance"]
    code = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted((ROOT / "algorithms").rglob("*.py"))
    }
    for key, filename in (
        ("algorithms/modular/obstacles.py", "obstacles.py"),
        ("algorithms/avoidance.py", "avoidance.py"),
    ):
        code[key] = hashlib.sha256(
            (HERE / "baseline-code" / filename).read_bytes()
        ).hexdigest()
    plan = dict(
        algorithms=algorithms,
        algorithm_version="1.0",
        steps=1500,
        seeds=[scene.seed],
        split="development",
        suite="core",
        evaluator_version=EVALUATOR_VERSION,
        thresholds=THRESHOLDS,
        code_sha256=code,
        platform_sha256={
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT / "pathlab").glob("*.py"))
        },
        scene_sources=[
            dict(
                file=str(scene_file.relative_to(ROOT)),
                sha256=hashlib.sha256(scene_file.read_bytes()).hexdigest(),
            )
        ],
        environment=environment(),
    )
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "plan.json", plan)
    jobs = [
        (
            name,
            "00-user-close-obstacles",
            scene.seed,
            1500,
            None,
            {},
            "development",
            "core",
            str(output),
            str(scene_file),
        )
        for name in algorithms
    ]
    with ProcessPoolExecutor(max_workers=2) as pool:
        reports = list(pool.map(replay, jobs))
    write_report(output, plan, reports)
