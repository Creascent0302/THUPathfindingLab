"""Bounded local media import; frames are canonical PNGs, sorted naturally."""

from __future__ import annotations

import json
from pathlib import Path
import re
import uuid

import cv2
import numpy as np

from .storage import write_json

MAX_UPLOAD_BYTES = 32 * 1024 * 1024
MAX_SOURCE_FRAMES = 600


def natural_key(name: str):
    return [
        int(part) if part.isdigit() else part.lower()
        for part in re.split(r"(\d+)", name)
    ]


def import_media(root: Path, files: list[tuple[str, bytes]], fps: float) -> dict:
    if (
        not files
        or len(files) > MAX_SOURCE_FRAMES
        or sum(len(data) for _, data in files) > MAX_UPLOAD_BYTES
    ):
        raise ValueError("最多 600 个文件，单次上传合计不超过 32 MiB")
    if not 1 <= fps <= 120:
        raise ValueError("帧率必须在 1..120")
    source_id = uuid.uuid4().hex
    directory = root / "uploads" / source_id
    directory.mkdir(parents=True)
    frames, total = [], 0

    def save(bgr, label, timestamp):
        nonlocal total
        if bgr is None or bgr.ndim != 3 or min(bgr.shape[:2]) < 16:
            raise ValueError(f"无法读取图像：{label}")
        if bgr.shape[0] * bgr.shape[1] > 24_000_000:
            raise ValueError("原图超过 2400 万像素")
        scale = min(1.0, 1280 / bgr.shape[1], 720 / bgr.shape[0])
        if scale < 1:
            bgr = cv2.resize(
                bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
            )
        ok, data = cv2.imencode(".png", bgr)
        if not ok:
            raise ValueError("图像编码失败")
        total += len(data)
        if total > 128 * 1024 * 1024:
            raise ValueError("解码后的帧数据超过 128 MiB，请缩短素材")
        index = len(frames)
        (directory / f"{index:06d}.png").write_bytes(data.tobytes())
        frames.append(
            {
                "index": index,
                "name": label,
                "timestamp_s": timestamp,
                "width": bgr.shape[1],
                "height": bgr.shape[0],
            }
        )

    capture = None
    try:
        suffix = Path(files[0][0]).suffix.lower()
        video = len(files) == 1 and suffix in {".mp4", ".avi", ".mov", ".mkv", ".webm"}
        if video:
            video_path = directory / ("source" + suffix)
            video_path.write_bytes(files[0][1])
            capture = cv2.VideoCapture(str(video_path))
            if not capture.isOpened():
                raise ValueError("视频解码失败，建议使用 MP4/H.264 或 AVI/MJPEG")
            video_fps = capture.get(cv2.CAP_PROP_FPS)
            if np.isfinite(video_fps) and 1 <= video_fps <= 120:
                fps = float(video_fps)
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if len(frames) >= MAX_SOURCE_FRAMES:
                    raise ValueError("视频超过 600 帧，请先裁剪；不会静默截断")
                save(frame, f"video:{len(frames)}", len(frames) / fps)
            capture.release()
            video_path.unlink()
        else:
            for name, raw in sorted(files, key=lambda item: natural_key(item[0])):
                if Path(name).suffix.lower() not in {
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".bmp",
                    ".webp",
                }:
                    raise ValueError("图像仅支持 PNG/JPEG/BMP/WebP；序列请多选图片")
                save(
                    cv2.imdecode(np.frombuffer(raw, np.uint8), cv2.IMREAD_COLOR),
                    Path(name).name,
                    len(frames) / fps,
                )
        if not frames:
            raise ValueError("素材没有可解码的帧")
        result = {
            "id": source_id,
            "frames": frames,
            "frame_count": len(frames),
            "fps": fps,
            "calibration": None,
            "note": "无真值与标定的录制素材；动作不会改变后续画面，米制指标不提供。",
        }
        write_json(directory / "source.json", result)
        return result
    except Exception:
        # This directory was created by this import, so cleanup cannot touch user files.
        for file in directory.iterdir():
            file.unlink()
        directory.rmdir()
        raise
    finally:
        if capture is not None:
            capture.release()


def read_source(root: Path, source_id: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", source_id):
        raise ValueError("非法素材 id")
    return json.loads(
        (root / "uploads" / source_id / "source.json").read_text(encoding="utf-8")
    )
