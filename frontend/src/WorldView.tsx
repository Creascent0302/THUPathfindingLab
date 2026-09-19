import { useState } from "react";
import type { Frame, History, Point, Scene } from "./types";

type Vec3 = [number, number, number];
type Face = { points: Vec3[]; color: string };
const rgb = (color: number[]) => `rgb(${color.join(",")})`;

/** Orthographic scene model shares exact metric geometry with the simulator. */
export function WorldView({
  scene,
  frame,
  history,
}: {
  scene: Scene;
  frame: Frame | null;
  history: History[];
}) {
  const [azimuth, setAzimuth] = useState(-35);
  const angle = (azimuth * Math.PI) / 180,
    c = Math.cos(angle),
    s = Math.sin(angle);
  const project = ([x, y, z = 0]: number[]) => [
    x * c - y * s,
    -(x * s + y * c) * 0.62 - z * 0.79,
  ];
  const points = (path: number[][]) =>
    path.map((p) => project(p).join(",")).join(" ");
  const pose = frame?.pose || scene.initial_pose;
  const geometry = [
    ...scene.target_path,
    ...scene.distractors.flat(),
    [pose.x_m, pose.y_m],
  ];
  const xs = geometry.map((p) => p[0]),
    ys = geometry.map((p) => p[1]);
  const x0 = Math.min(...xs) - 1.4,
    x1 = Math.max(...xs) + 1.4;
  const y0 = Math.min(...ys) - 1.4,
    y1 = Math.max(...ys) + 1.4;
  const floor = [
    [x0, y0],
    [x1, y0],
    [x1, y1],
    [x0, y1],
  ];
  const corners = [...floor.map(project), project([pose.x_m, pose.y_m, 0.8])];
  const bx = Math.min(...corners.map((p) => p[0])) - 0.5,
    by = Math.min(...corners.map((p) => p[1])) - 0.5;
  const width = Math.max(...corners.map((p) => p[0])) - bx + 0.5,
    height = Math.max(...corners.map((p) => p[1])) - by + 0.5;
  const faces: Face[] = [];
  const local = ([x, y, z]: Vec3): Vec3 => [
    pose.x_m + x * Math.cos(pose.yaw_rad) - y * Math.sin(pose.yaw_rad),
    pose.y_m + x * Math.sin(pose.yaw_rad) + y * Math.cos(pose.yaw_rad),
    z,
  ];
  const box = (center: Vec3, size: Vec3, colors: string[], yaw = 0) => {
    const vertices: Vec3[] = [];
    for (const z of [-1, 1])
      for (const [x, y] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ]) {
        const dx = (x * size[0]) / 2,
          dy = (y * size[1]) / 2;
        vertices.push(
          local([
            center[0] + dx * Math.cos(yaw) - dy * Math.sin(yaw),
            center[1] + dx * Math.sin(yaw) + dy * Math.cos(yaw),
            center[2] + (z * size[2]) / 2,
          ]),
        );
      }
    [
      [0, 1, 5, 4],
      [1, 2, 6, 5],
      [2, 3, 7, 6],
      [3, 0, 4, 7],
      [4, 5, 6, 7],
    ].forEach((indices, i) =>
      faces.push({
        points: indices.map((index) => vertices[index]),
        color: colors[i % (colors.length - 1)] || colors[0],
      }),
    );
    faces[faces.length - 1].color = colors[colors.length - 1];
  };
  const v = scene.vehicle,
    steering = pose.steering_angle_rad || 0;
  for (const side of [-1, 1])
    for (const axle of [0, v.wheelbase_m]) {
      const turn =
        axle && Math.abs(steering) > 0.0001
          ? Math.atan(
              v.wheelbase_m /
                (v.wheelbase_m / Math.tan(steering) -
                  (side * v.track_width_m) / 2),
            )
          : 0;
      box(
        [axle, (side * v.track_width_m) / 2, 0.075],
        [0.15, 0.065, 0.15],
        ["#283238", "#151e23", "#4c585d"],
        turn,
      );
    }
  box(
    [v.length_m / 2 - 0.1, 0, 0.17],
    [v.length_m, v.width_m * 0.86, 0.12],
    ["#b77924", "#d09533", "#f0bc58"],
  );
  box(
    [v.wheelbase_m * 0.35, 0, 0.265],
    [0.18, v.width_m * 0.66, 0.075],
    ["#365462", "#233e4d", "#5b7985"],
  );
  box(
    [v.wheelbase_m * 0.63, 0, 0.34],
    [0.026, 0.026, 0.23],
    ["#48565d", "#34464c", "#71858c"],
  );
  box(
    [v.wheelbase_m * 0.63, 0, 0.465],
    [0.08, 0.105, 0.065],
    ["#2a414a", "#142832", "#67818c"],
  );
  const depth = (face: Face) =>
    face.points.reduce((sum, [x, y, z]) => sum + x * s + y * c - z * 0.8, 0) /
    face.points.length;
  faces.sort((a, b) => depth(b) - depth(a));
  const start = scene.target_path[0],
    end = scene.target_path[scene.target_path.length - 1];
  const ring = (p: Point) =>
    Array.from({ length: 33 }, (_, i) => [
      p[0] + Math.cos((i * Math.PI) / 16) * 0.16,
      p[1] + Math.sin((i * Math.PI) / 16) * 0.16,
    ]);
  return (
    <>
      <svg
        className="world-view"
        viewBox={`${bx} ${by} ${width} ${height}`}
        aria-label="立体场景与四轮车模型"
      >
        <polygon
          points={points(floor.map(([x, y]) => [x + 0.12, y - 0.12, -0.12]))}
          fill="#bec8c1"
        />
        <polygon
          points={points(floor)}
          fill={rgb(scene.appearance.ground_rgb)}
          stroke="#aebeb3"
          strokeWidth=".025"
        />
        {scene.appearance.surface !== "plain" && (
          <g stroke="#b5c1b6" strokeOpacity=".45" strokeWidth=".012">
            {Array.from(
              { length: Math.max(0, Math.floor(x1) - Math.ceil(x0) + 1) },
              (_, i) => (
                <polyline
                  key={`x${i}`}
                  points={points([
                    [Math.ceil(x0) + i, y0],
                    [Math.ceil(x0) + i, y1],
                  ])}
                />
              ),
            )}
            {Array.from(
              { length: Math.max(0, Math.floor(y1) - Math.ceil(y0) + 1) },
              (_, i) => (
                <polyline
                  key={`y${i}`}
                  points={points([
                    [x0, Math.ceil(y0) + i],
                    [x1, Math.ceil(y0) + i],
                  ])}
                />
              ),
            )}
          </g>
        )}
        {[scene.target_path, ...scene.distractors].map((path, i) => (
          <polyline
            key={i}
            points={points(path)}
            fill="none"
            stroke={rgb(scene.appearance.line_rgb)}
            strokeWidth={scene.appearance.line_width_m}
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        <polyline
          points={points(ring(start))}
          fill="none"
          stroke="#259c69"
          strokeWidth=".045"
        />
        <polyline
          points={points(ring(end))}
          fill="none"
          stroke="#dd993d"
          strokeWidth=".04"
        />
        <polyline
          points={points(
            history.flatMap((row) =>
              row.pose ? [[row.pose.x_m, row.pose.y_m, 0.014]] : [],
            ),
          )}
          fill="none"
          stroke="#0b9f8a"
          strokeWidth=".04"
        />
        <polygon
          points={points(
            [
              [-0.16, -v.width_m * 0.7, 0],
              [v.length_m, -v.width_m * 0.7, 0],
              [v.length_m, v.width_m * 0.7, 0],
              [-0.16, v.width_m * 0.7, 0],
            ].map((p) => local(p as Vec3)),
          )}
          fill="#263a3a"
          opacity=".16"
        />
        {faces.map((face, i) => (
          <polygon
            key={i}
            points={points(face.points)}
            fill={face.color}
            stroke="#1c303920"
            strokeWidth=".008"
          />
        ))}
        {[start, end].map((p, i) => {
          const [x, y] = project([p[0], p[1], 0.32]);
          return (
            <text
              key={i}
              x={x}
              y={y}
              fontSize=".2"
              textAnchor="middle"
              fill="#45645c"
            >
              {i ? "终点" : "起点"}
            </text>
          );
        })}
      </svg>
      <label className="view-angle">
        视角
        <input
          aria-label="场景观察角度"
          type="range"
          min="-180"
          max="180"
          value={azimuth}
          onChange={(e) => setAzimuth(Number(e.target.value))}
        />
        <span>{azimuth}°</span>
      </label>
    </>
  );
}
