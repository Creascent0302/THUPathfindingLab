"""Local CPU collection, behavior cloning and optional DAgger data aggregation."""

import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

from pathlab.storage import write_json
from .model import RecurrentDriver


class Sequences(Dataset):
    def __init__(self, folders, split, length=12, acquisition_weight=1):
        self.episodes, self.windows, self.length, self.split = [], [], length, split
        self.acquisition_weight = acquisition_weight
        self.environments = set()
        identities = {}
        for folder in folders:
            manifest = json.loads((Path(folder) / "manifest.json").read_text())
            for item in manifest["episodes"]:
                identity = (item["family"], item["seed"])
                if identity in identities and identities[identity] != item["split"]:
                    raise ValueError("同一完整场景不能跨训练 / 验证集合")
                identities[identity] = item["split"]
                if not (
                    item["split"] == "development"
                    and 0 <= item["seed"] < 100
                    or item["split"] == "validation"
                    and 201 <= item["seed"] <= 204
                ):
                    raise ValueError(
                        "训练数据须遵守保留集约定：开发 0–99，验证 201–204；测试场景禁止进入训练"
                    )
                if item["split"] != split or item["frames"] < length:
                    continue
                scene = item.get("scene", {})
                self.environments.add(
                    (
                        item.get(
                            "motion_model",
                            scene.get("vehicle", {}).get(
                                "motion_model", "kinematic_v1"
                            ),
                        ),
                        str(
                            item.get("render_version", scene.get("render_version", "2"))
                        ),
                    )
                )
                with np.load(Path(folder) / item["file"], allow_pickle=False) as data:
                    episode = {
                        key: data[key]
                        for key in ("images", "context", "actions", "visible")
                    }
                if not all(
                    np.isfinite(episode[k]).all()
                    for k in ("context", "actions", "visible")
                ):
                    raise ValueError(f"数据包含非法数值：{item['file']}")
                count = len(episode["images"])
                if (
                    episode["images"].shape != (count, 96, 160, 4)
                    or episode["context"].shape != (count, 5)
                    or episode["actions"].shape != (count, 2)
                    or episode["visible"].shape != (count,)
                ):
                    raise ValueError(f"数据形状与模型不匹配：{item['file']}")
                index = len(self.episodes)
                self.episodes.append(episode)
                self.windows.extend(
                    (index, start)
                    for start in range(
                        0, len(episode["images"]) - length + 1, max(1, length // 2)
                    )
                )
        if not self.windows:
            raise ValueError(f"没有 {split} 序列数据")

    def __len__(self):
        return len(self.windows)

    def __getitem__(self, index):
        episode, start = self.windows[index]
        data = {
            k: v[start : start + self.length].copy()
            for k, v in self.episodes[episode].items()
        }
        if self.split == "development" and random.random() < 0.5:
            data["images"] = data["images"][:, :, ::-1].copy()
            data["actions"][:, 0] *= -1
            data["context"][:, 0] *= -1
        image = (
            torch.from_numpy(data["images"].transpose(0, 3, 1, 2).copy()).float() / 255
        )
        return (
            image,
            torch.from_numpy(data["context"]),
            torch.from_numpy(data["actions"]),
            torch.from_numpy(data["visible"]),
            torch.from_numpy(
                np.where(
                    np.arange(start, start + self.length) < 35,
                    self.acquisition_weight,
                    1,
                ).astype(np.float32)
            ),
        )


def fit(args):
    torch.set_num_threads(args.threads)
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    random.seed(args.seed)
    training = Sequences(
        args.data, "development", args.sequence_length, args.acquisition_weight
    )
    validation = Sequences(
        args.data, "validation", args.sequence_length, args.acquisition_weight
    )
    loaders = [
        DataLoader(data, batch_size=args.batch_size, shuffle=i == 0, num_workers=0)
        for i, data in enumerate((training, validation))
    ]
    model = RecurrentDriver()
    if args.resume:
        model.load_state_dict(
            torch.load(args.resume, map_location="cpu", weights_only=True)["model"]
        )
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=0.0001)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
        optimizer, args.epochs, eta_min=args.lr * 0.15
    )
    best, history, start = float("inf"), [], time.perf_counter()
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    plan = vars(args).copy()
    plan.update(
        torch_version=str(torch.__version__),
        parameters=sum(p.numel() for p in model.parameters()),
        training_frames=sum(len(e["images"]) for e in training.episodes),
        validation_frames=sum(len(e["images"]) for e in validation.episodes),
        training_episodes=len(training.episodes),
        validation_episodes=len(validation.episodes),
        device="cpu",
        trained_environments=[
            {"motion_model": motion, "render_version": render}
            for motion, render in sorted(training.environments)
        ],
        resume_sha256=hashlib.sha256(Path(args.resume).read_bytes()).hexdigest()
        if args.resume
        else None,
        data_manifests_sha256={
            str(folder): hashlib.sha256(
                (Path(folder) / "manifest.json").read_bytes()
            ).hexdigest()
            for folder in args.data
        },
        source_sha256={
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        },
    )
    write_json(destination.with_suffix(".plan.json"), plan)
    for epoch in range(args.epochs):
        summary = {"epoch": epoch + 1}
        for split, loader in zip(("train", "validation"), loaders):
            model.train(split == "train")
            totals = np.zeros(5)
            for images, context, labels, visible, phase_weight in loader:
                with torch.set_grad_enabled(split == "train"):
                    actions, logits, _ = model(images, context)
                    # Two burn-in frames initialize the recurrent state without loss.
                    actions, labels, logits, visible = (
                        actions[:, 2:],
                        labels[:, 2:],
                        logits[:, 2:],
                        visible[:, 2:],
                    )
                    weights = (1 + 3 * labels[:, :, 0].abs()) * phase_weight[:, 2:]
                    steering = (
                        (actions[:, :, 0] - labels[:, :, 0]) ** 2 * weights
                    ).mean()
                    speed = ((actions[:, :, 1] - labels[:, :, 1]) ** 2).mean()
                    visibility = nn.functional.binary_cross_entropy_with_logits(
                        logits, visible
                    )
                    loss = 5 * steering + 2 * speed + 0.15 * visibility
                    if split == "train":
                        optimizer.zero_grad(set_to_none=True)
                        loss.backward()
                        nn.utils.clip_grad_norm_(model.parameters(), 5)
                        optimizer.step()
                count = labels.shape[0]
                totals += [
                    float(loss.detach()) * count,
                    float((actions[:, :, 0] - labels[:, :, 0]).abs().mean().detach())
                    * count,
                    float((actions[:, :, 1] - labels[:, :, 1]).abs().mean().detach())
                    * count,
                    float(((logits.sigmoid() - visible) ** 2).mean().detach()) * count,
                    count,
                ]
            summary[split] = dict(
                zip(
                    (
                        "loss",
                        "steering_normalized_mae",
                        "speed_mae",
                        "visibility_brier",
                    ),
                    (totals[:4] / totals[4]).tolist(),
                )
            )
        scheduler.step()
        summary["elapsed_s"] = time.perf_counter() - start
        history.append(summary)
        if summary["validation"]["loss"] < best:
            best = summary["validation"]["loss"]
            temporary = destination.with_suffix(".pt.tmp")
            torch.save(
                {
                    "format_version": 1,
                    "architecture": "cnn_gru_v1",
                    "model_id": f"cpu-bc-seed{args.seed}-epoch{epoch + 1}",
                    "trained_environments": plan["trained_environments"],
                    "resume_sha256": plan["resume_sha256"],
                    "control_interval_s": 0.1,
                    "supported_hints": ["marker"],
                    "marker_rgb": [34, 160, 94],
                    "model": model.state_dict(),
                    "epoch": epoch + 1,
                    "validation": summary["validation"],
                },
                temporary,
            )
            temporary.replace(destination)
        write_json(
            destination.with_suffix(".training.json"),
            {
                "plan": plan,
                "epochs": history,
                "best_validation_loss": best,
                "checkpoint_sha256": hashlib.sha256(
                    destination.read_bytes()
                ).hexdigest(),
            },
        )
        print(json.dumps(summary), flush=True)


def average_checkpoints(args):
    """Uniform parameter averaging of compatible, already trained policies."""
    destination = Path(args.output)
    if len(args.checkpoints) < 2 or destination.resolve() in [
        Path(p).resolve() for p in args.checkpoints
    ]:
        raise ValueError("至少提供两个训练权重，输出不能覆盖输入权重")
    checkpoints = [
        torch.load(p, map_location="cpu", weights_only=True) for p in args.checkpoints
    ]
    weights = np.asarray(
        args.weights if args.weights is not None else [1] * len(checkpoints),
        dtype=float,
    )
    if (
        weights.shape != (len(checkpoints),)
        or not np.isfinite(weights).all()
        or np.any(weights < 0)
        or weights.sum() <= 0
    ):
        raise ValueError("平均权重须与模型一一对应，非负、有限且总和为正")
    weights /= weights.sum()
    metadata = {
        k: checkpoints[0][k]
        for k in (
            "format_version",
            "architecture",
            "control_interval_s",
            "supported_hints",
            "marker_rgb",
        )
    }
    for checkpoint in checkpoints:
        if any(checkpoint.get(k) != v for k, v in metadata.items()):
            raise ValueError("待平均模型的架构、控制周期或提示约定不一致")
        RecurrentDriver().load_state_dict(checkpoint["model"])
    model = {
        name: sum(
            float(weight) * c["model"][name] for weight, c in zip(weights, checkpoints)
        )
        for name in checkpoints[0]["model"]
    }
    sources = [
        {
            "path": p,
            "sha256": hashlib.sha256(Path(p).read_bytes()).hexdigest(),
            "model_id": c["model_id"],
            "epoch": c.get("epoch"),
        }
        for p, c in zip(args.checkpoints, checkpoints)
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            **metadata,
            "model_id": "cpu-mean-cnn-gru-v1",
            "model": model,
            "averaging_sources": sources,
            "averaging_weights": weights.tolist(),
        },
        destination,
    )
    plan = {
        "method": "weighted_parameter_average",
        "sources": sources,
        "weights": weights.tolist(),
        "output": str(destination),
        "checkpoint_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
    }
    write_json(destination.with_suffix(".plan.json"), plan)
    write_json(destination.with_suffix(".training.json"), plan)
    print("已平均真实训练权重；须通过独立闭环验证后再发布：", destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect")
    collect.add_argument("--data", default="artifacts/learning/data")
    collect.add_argument("--episodes-per-family", type=int, default=8)
    collect.add_argument("--validation-seeds", type=int, default=2)
    collect.add_argument("--jobs", type=int, default=4)
    collect.add_argument("--checkpoint", default=None)
    collect.add_argument("--beta", type=float, default=0.2)
    train = commands.add_parser("fit")
    train.add_argument("--data", nargs="+", default=["artifacts/learning/data"])
    train.add_argument("--output", default="algorithms/learning/weights/driver.pt")
    train.add_argument("--epochs", type=int, default=20)
    train.add_argument("--batch-size", type=int, default=32)
    train.add_argument("--sequence-length", type=int, default=12)
    train.add_argument("--threads", type=int, default=4)
    train.add_argument("--lr", type=float, default=0.0005)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--resume")
    train.add_argument(
        "--acquisition-weight",
        type=float,
        default=1,
        help="前 3.5 s 接入阶段的转向损失权重，验证阶段使用相同权重",
    )
    average = commands.add_parser(
        "average", help="平均同架构、同初始化微调模型的参数，推理仍为单个网络"
    )
    average.add_argument("--checkpoints", nargs="+", required=True)
    average.add_argument("--output", required=True)
    average.add_argument(
        "--weights",
        nargs="+",
        type=float,
        help="可选非负权重；默认等权。必须用独立验证集选择",
    )
    args = parser.parse_args()
    if args.command == "collect":
        if (
            not 1 <= args.episodes_per_family <= 100
            or not 1 <= args.validation_seeds <= 4
        ):
            parser.error("训练每族 1–100 场景，验证 1–4 场景；测试种子禁止用于采集")
        if not 0 <= args.beta <= 1 or args.jobs < 1:
            parser.error("beta 须在 0..1，jobs 须为正整数")
        from .data import collect as collect_data

        collect_data(args)
    elif args.command == "average":
        average_checkpoints(args)
    else:
        if (
            min(args.epochs, args.batch_size, args.threads) < 1
            or args.sequence_length < 4
            or args.lr <= 0
            or args.acquisition_weight < 1
        ):
            parser.error(
                "epochs、batch-size、threads、lr 须为正数，sequence-length 至少为 4"
            )
        fit(args)


if __name__ == "__main__":
    main()
