"""Compact spatial CNN + recurrent memory, predicting bounded actions directly."""

import cv2
import numpy as np
import torch
from torch import nn

WIDTH, HEIGHT = 160, 96


def marker_plane(rgb):
    """Expose the public green marker cue without extracting a route or action."""
    red, green, blue = np.moveaxis(np.asarray(rgb, dtype=np.int16), -1, 0)
    return (
        (green * 4 > red * 5)
        & (green * 5 > blue * 6)
        & (green - red > 20)
        & (green > 60)
    ).astype(np.uint8) * 255


def image_input(rgb, hint, first=False, input_version="rgb_hint_v1"):
    image = cv2.resize(rgb, (WIDTH, HEIGHT), interpolation=cv2.INTER_AREA)
    cue = np.zeros((HEIGHT, WIDTH), np.uint8)
    if input_version == "rgb_marker_v2" and hint.kind == "marker":
        cue = marker_plane(image)
    elif first and hint.kind == "point":
        u, v = hint.point_px
        cv2.circle(
            cue,
            (round(u * WIDTH / rgb.shape[1]), round(v * HEIGHT / rgb.shape[0])),
            5,
            255,
            -1,
        )
    elif first and hint.kind == "region":
        x0, y0, x1, y1 = hint.region_px
        cv2.rectangle(
            cue,
            (round(x0 * WIDTH / rgb.shape[1]), round(y0 * HEIGHT / rgb.shape[0])),
            (round(x1 * WIDTH / rgb.shape[1]), round(y1 * HEIGHT / rgb.shape[0])),
            255,
            -1,
        )
    return np.dstack((image, cue))


def context_input(limits, previous, dt):
    return np.array(
        [
            previous[0] / limits["max_steering_rad"],
            previous[1] / min(1.0, limits["max_speed_mps"]),
            limits["wheelbase_m"] / 0.32,
            limits["max_steering_rad"] / 0.52,
            dt * 10,
        ],
        np.float32,
    )


class RecurrentDriver(nn.Module):
    def __init__(self):
        super().__init__()
        channels = (4, 12, 20, 32, 40)
        layers = []
        for source, target in zip(channels[:-1], channels[1:]):
            layers += [
                nn.Conv2d(
                    source,
                    target,
                    5 if source == 4 else 3,
                    stride=2,
                    padding=2 if source == 4 else 1,
                ),
                nn.SiLU(),
            ]
        self.encoder = nn.Sequential(
            *layers,
            nn.Flatten(),
            nn.Linear(40 * 6 * 10, 128),
            nn.LayerNorm(128),
            nn.SiLU(),
        )
        self.memory = nn.GRU(133, 96, batch_first=True)
        self.head = nn.Sequential(nn.Linear(96, 64), nn.SiLU(), nn.Linear(64, 3))

    def forward(self, images, context, hidden=None):
        batch, time = images.shape[:2]
        encoded = self.encoder(images.reshape(-1, 4, HEIGHT, WIDTH)).reshape(
            batch, time, 128
        )
        sequence, hidden = self.memory(torch.cat([encoded, context], dim=-1), hidden)
        raw = self.head(sequence)
        actions = torch.stack(
            [torch.tanh(raw[..., 0]), torch.sigmoid(raw[..., 1])], dim=-1
        )
        return actions, raw[..., 2], hidden
