import { useState } from "react";
import type { Frame, History, Point, Scene, SceneObject } from "./types";

type Vec3 = [number, number, number];
type Face = { points: Vec3[]; color: string };
const rgb = (color: number[]) => `rgb(${color.join(",")})`;

function objectFaces(obj: SceneObject): Face[] {
  const result: Face[] = [];
  const transform = ([x, y, z]: Vec3): Vec3 => [
    obj.x_m + x * Math.cos(obj.yaw_rad) - y * Math.sin(obj.yaw_rad),
    obj.y_m + x * Math.sin(obj.yaw_rad) + y * Math.cos(obj.yaw_rad),
    z,
  ];
  const add = (vertices: Vec3[], color: number[], shade = 1) =>
    result.push({
      points: vertices.map(transform),
      color: rgb(color.map((channel) => Math.round(channel * shade))),
    });
  const box = (
    x: number,
    z: number,
    length: number,
    width: number,
    height: number,
    color: number[],
  ) => {
    const vertices: Vec3[] = [];
    for (const dz of [-1, 1])
      for (const [dx, dy] of [
        [-1, -1],
        [1, -1],
        [1, 1],
        [-1, 1],
      ])
        vertices.push([
          x + (dx * length) / 2,
          (dy * width) / 2,
          z + (dz * height) / 2,
        ]);
    [
      [0, 1, 5, 4],
      [1, 2, 6, 5],
      [2, 3, 7, 6],
      [3, 0, 4, 7],
      [4, 5, 6, 7],
    ].forEach((indices, index) =>
      add(
        indices.map((i) => vertices[i]),
        color,
        [0.78, 0.88, 0.73, 0.8, 1][index],
      ),
    );
  };
  const {
    length_m: length,
    width_m: width,
    height_m: height,
    color_rgb: color,
  } = obj;
  const dark = [50, 54, 54],
    white = [226, 224, 211];
  if (obj.kind === "box") {
    box(0, height / 2, length, width, height, color);
    box(0, height + 0.0005, length * 0.16, width, 0.001, [192, 158, 108]);
  } else if (obj.kind === "barrier") {
    for (const side of [-1, 1]) {
      box(
        side * length * 0.35,
        height * 0.05,
        length * 0.2,
        width,
        height * 0.1,
        dark,
      );
      box(
        side * length * 0.35,
        height * 0.42,
        length * 0.07,
        width * 0.3,
        height * 0.7,
        dark,
      );
    }
    box(0, height * 0.68, length, width * 0.4, height * 0.64, color);
    for (const x of [-0.3, 0, 0.3])
      box(
        x * length,
        height * 0.68,
        length * 0.1,
        width * 0.405,
        height * 0.63,
        white,
      );
  } else {
    const cone = obj.kind === "cone";
    if (cone) box(0, height * 0.04, length, width, height * 0.08, dark);
    const levels = cone
      ? [
          [0.08, 0.87],
          [0.38, 0.61],
          [0.56, 0.46],
          [0.98, 0.06],
        ]
      : [
          [0, 1],
          [0.36, 1],
          [0.52, 1],
          [1, 1],
        ];
    const rings = levels.map(([z, radius]) =>
      Array.from(
        { length: 16 },
        (_, index): Vec3 => [
          ((Math.cos((index * Math.PI) / 8) * length) / 2) * radius,
          ((Math.sin((index * Math.PI) / 8) * width) / 2) * radius,
          z * height,
        ],
      ),
    );
    rings.slice(0, -1).forEach((lower, level) =>
      lower.forEach((point, index) => {
        const next = (index + 1) % 16;
        add(
          [point, lower[next], rings[level + 1][next], rings[level + 1][index]],
          level === 1 ? white : color,
          0.76 + 0.2 * Math.cos((index * Math.PI) / 8),
        );
      }),
    );
    add(rings[rings.length - 1], color);
  }
  return result;
}

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
  const objects =
    scene.render_version === "3"
      ? (scene.objects || []).filter((obj) => obj.enabled)
      : [];
  const objectGeometry = objects.flatMap(objectFaces);
  const geometry = [
    ...scene.target_path,
    ...scene.distractors.flat(),
    [pose.x_m, pose.y_m],
    ...objectGeometry.flatMap((face) => face.points),
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
  const corners = [
    ...floor.map(project),
    project([pose.x_m, pose.y_m, 0.8]),
    ...objectGeometry.flatMap((face) => face.points.map(project)),
  ];
  const bx = Math.min(...corners.map((p) => p[0])) - 0.5,
    by = Math.min(...corners.map((p) => p[1])) - 0.5;
  const width = Math.max(...corners.map((p) => p[0])) - bx + 0.5,
    height = Math.max(...corners.map((p) => p[1])) - by + 0.5;
  const faces: Face[] = [...objectGeometry];
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
    [v.wheelbase_m / 2, 0, 0.17],
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
        {scene.appearance.object_shadows !== false &&
          objects.map((obj, index) => {
            const azimuth = scene.appearance.sun_azimuth_rad ?? -0.8;
            const distance =
              obj.height_m /
              Math.tan(scene.appearance.sun_elevation_rad ?? 0.9);
            const direction = Math.atan2(
              -Math.sin(azimuth),
              -Math.cos(azimuth),
            );
            return (
              <polygon
                key={`shadow-${index}`}
                points={points(
                  Array.from({ length: 20 }, (_, i) => {
                    const theta = (i * Math.PI) / 10;
                    const length =
                      (Math.hypot(obj.length_m, obj.width_m) + distance) / 2;
                    const width = Math.max(obj.width_m, obj.length_m) / 2;
                    return [
                      obj.x_m -
                        (Math.cos(azimuth) * distance) / 2 +
                        Math.cos(theta) * length * Math.cos(direction) -
                        Math.sin(theta) * width * Math.sin(direction),
                      obj.y_m -
                        (Math.sin(azimuth) * distance) / 2 +
                        Math.cos(theta) * length * Math.sin(direction) +
                        Math.sin(theta) * width * Math.cos(direction),
                      0.002,
                    ];
                  }),
                )}
                fill="#293c3b"
                opacity=".16"
              />
            );
          })}
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
              [(v.wheelbase_m - v.length_m) / 2 - 0.04, -v.width_m * 0.7, 0],
              [(v.wheelbase_m + v.length_m) / 2 + 0.04, -v.width_m * 0.7, 0],
              [(v.wheelbase_m + v.length_m) / 2 + 0.04, v.width_m * 0.7, 0],
              [(v.wheelbase_m - v.length_m) / 2 - 0.04, v.width_m * 0.7, 0],
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
        {Math.hypot(pose.velocity_x_mps || 0, pose.velocity_y_mps || 0) >
          0.03 && (
          <g>
            <defs>
              <marker
                id="world-velocity-arrow"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="5"
                markerHeight="5"
                orient="auto-start-reverse"
              >
                <path d="M0 0L10 5 0 10Z" fill="#168a9a" />
              </marker>
            </defs>
            <polyline
              points={points([
                [pose.x_m, pose.y_m, 0.55],
                [
                  pose.x_m + (pose.velocity_x_mps || 0) * 0.8,
                  pose.y_m + (pose.velocity_y_mps || 0) * 0.8,
                  0.55,
                ],
              ])}
              fill="none"
              stroke="#168a9a"
              strokeWidth=".035"
              markerEnd="url(#world-velocity-arrow)"
            />
          </g>
        )}
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
        <span className="world-legend">
          {objects.length} 个物件 · 青色箭头表示实际速度
        </span>
      </label>
    </>
  );
}
