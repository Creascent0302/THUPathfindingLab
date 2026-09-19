import { WorldView } from "./WorldView";
import { useRef, useState } from "react";
import type { PointerEvent } from "react";
import {
  fmt,
  type Calibration,
  type Frame,
  type Hint,
  type History,
  type Point,
  type Scene,
} from "./types";

function linePoints(points: Point[]) {
  return points.map((p) => p.join(",")).join(" ");
}
function project(points: Point[], calibration: Calibration): Point[] {
  const h = calibration.ground_to_image;
  return points.flatMap(([x, y]) => {
    const z = h[2][0] * x + h[2][1] * y + h[2][2];
    return z > 0
      ? [
          [
            (h[0][0] * x + h[0][1] * y + h[0][2]) / z,
            (h[1][0] * x + h[1][1] * y + h[1][2]) / z,
          ] as Point,
        ]
      : [];
  });
}

export function CameraPanel({
  image,
  frame,
  calibration,
  overlay,
  hint,
  hintMode,
  onHint,
}: {
  image: string | null;
  frame: Frame | null;
  calibration: Calibration | null;
  overlay?: boolean;
  hint: Hint | null;
  hintMode?: "point" | "region" | null;
  onHint?: (hint: Hint) => void;
}) {
  const [dimensions, setDimensions] = useState<Point>([640, 360]);
  const [drag, setDrag] = useState<[Point, Point] | null>(null);
  const start = useRef<Point | null>(null);
  const size: Point = calibration
    ? [calibration.width, calibration.height]
    : dimensions;
  const coord = (e: PointerEvent<SVGSVGElement>): Point => {
    // Invert the SVG transform, including any aspect-ratio letterboxing.
    const transform = e.currentTarget.getScreenCTM();
    if (!transform) return [0, 0];
    const point = new DOMPoint(e.clientX, e.clientY).matrixTransform(
      transform.inverse(),
    );
    return [
      Math.max(0, Math.min(size[0] - 1, point.x)),
      Math.max(0, Math.min(size[1] - 1, point.y)),
    ];
  };
  const rect = hint?.region_px;
  const predicted =
    frame?.output?.local_path_m && calibration
      ? project(frame.output.local_path_m, calibration)
      : null;
  return (
    <section className="panel camera-panel">
      <div className="panel-title">
        <h2>{overlay ? "算法叠加画面" : "前向摄像头"}</h2>
        <span>{overlay ? "仅展示算法实际输出" : "RGB · 算法公开输入"}</span>
      </div>
      <div className={"camera " + (hintMode ? "picking" : "")}>
        {image ? (
          <img
            src={"data:image/png;base64," + image}
            alt={overlay ? "算法叠加图像" : "原始摄像头图像"}
            onLoad={(e) =>
              setDimensions([
                e.currentTarget.naturalWidth,
                e.currentTarget.naturalHeight,
              ])
            }
          />
        ) : (
          <div className="camera-empty">选择场景或上传素材</div>
        )}
        <svg
          viewBox={`0 0 ${size[0]} ${size[1]}`}
          onPointerDown={(e) => {
            if (!hintMode) return;
            e.currentTarget.setPointerCapture(e.pointerId);
            start.current = coord(e);
            setDrag([coord(e), coord(e)]);
          }}
          onPointerMove={(e) => {
            if (start.current) setDrag([start.current, coord(e)]);
          }}
          onPointerUp={(e) => {
            if (!start.current || !onHint) return;
            const a = start.current,
              b = coord(e);
            if (hintMode === "point")
              onHint({ kind: "point", point_px: b, direction: "unspecified" });
            else if (Math.abs(a[0] - b[0]) > 5 && Math.abs(a[1] - b[1]) > 5)
              onHint({
                kind: "region",
                region_px: [
                  Math.min(a[0], b[0]),
                  Math.min(a[1], b[1]),
                  Math.max(a[0], b[0]),
                  Math.max(a[1], b[1]),
                ],
                direction: "unspecified",
              });
            start.current = null;
            setDrag(null);
          }}
        >
          {overlay &&
            frame?.output?.candidates_px?.map((line, index) => (
              <polyline
                key={index}
                points={linePoints(line)}
                fill="none"
                stroke="#ffbd4e"
                strokeWidth="3"
              />
            ))}
          {overlay && frame?.output?.centerline_px && (
            <polyline
              points={linePoints(frame.output.centerline_px)}
              fill="none"
              stroke="#27e3c1"
              strokeWidth="4"
            />
          )}
          {overlay && predicted && (
            <polyline
              points={linePoints(predicted)}
              fill="none"
              stroke="#c38fff"
              strokeWidth="4"
              strokeDasharray="9 5"
            />
          )}
          {hint?.point_px && (
            <g stroke="#fa6e55" strokeWidth="2">
              <circle
                cx={hint.point_px[0]}
                cy={hint.point_px[1]}
                r="9"
                fill="none"
              />
              <path
                d={`M${hint.point_px[0] - 15},${hint.point_px[1]}h30 M${hint.point_px[0]},${hint.point_px[1] - 15}v30`}
              />
            </g>
          )}
          {rect && (
            <rect
              x={rect[0]}
              y={rect[1]}
              width={rect[2] - rect[0]}
              height={rect[3] - rect[1]}
              fill="#fa6e5530"
              stroke="#fa6e55"
              strokeWidth="2"
            />
          )}
          {drag && hintMode === "region" && (
            <rect
              x={Math.min(drag[0][0], drag[1][0])}
              y={Math.min(drag[0][1], drag[1][1])}
              width={Math.abs(drag[0][0] - drag[1][0])}
              height={Math.abs(drag[0][1] - drag[1][1])}
              fill="#fa6e5530"
              stroke="#fa6e55"
            />
          )}
        </svg>
        <div className="camera-label">
          {size[0]} × {size[1]}{" "}
          {frame ? ` / 帧 ${frame.frame_id}` : " / 首帧预览"}
        </div>
      </div>
      <div className="panel-foot">
        {overlay ? (
          <>
            <i className="dot amber" /> 候选线 <i className="dot teal" /> 目标线{" "}
            <i className="dot purple" /> 局部路径{" "}
            {!frame?.output?.centerline_px && !predicted && (
              <span className="muted"> · 目标/路径不提供</span>
            )}
          </>
        ) : hintMode ? (
          "在图中点击目标线，或拖动框选起点区域。"
        ) : (
          "画面由当前车辆姿态渲染；模拟地图不会传给算法。"
        )}
      </div>
    </section>
  );
}

export function MapPanel({
  scene,
  frame,
  history,
}: {
  scene: Scene | null;
  frame: Frame | null;
  history: History[];
}) {
  const [viewMode, setViewMode] = useState<"model" | "map">("model");
  if (!scene)
    return (
      <section className="panel">
        <div className="panel-title">
          <h2>场景俯视图</h2>
        </div>
        <div className="empty">
          录制素材没有地图真值
          <br />
          不提供车辆轨迹或米制误差
        </div>
      </section>
    );
  const all = [
    ...scene.target_path,
    ...scene.distractors.flat(),
    [scene.initial_pose.x_m, scene.initial_pose.y_m] as Point,
    ...history.flatMap((r) =>
      r.pose ? [[r.pose.x_m, r.pose.y_m] as Point] : [],
    ),
  ];
  const xs = all.map((p) => p[0]),
    ys = all.map((p) => -p[1]);
  const minX = Math.min(...xs) - 1,
    minY = Math.min(...ys) - 1,
    w = Math.max(...xs) - minX + 1,
    h = Math.max(...ys) - minY + 1;
  const view = (p: Point[]) => p.map(([x, y]) => `${x},${-y}`).join(" ");
  const pose = frame?.pose || scene.initial_pose;
  const origin = frame?.pose_before || pose;
  const prediction = frame?.output?.local_path_m?.map(
    ([x, y]) =>
      [
        origin.x_m +
          x * Math.cos(origin.yaw_rad) -
          y * Math.sin(origin.yaw_rad),
        origin.y_m +
          x * Math.sin(origin.yaw_rad) +
          y * Math.cos(origin.yaw_rad),
      ] as Point,
  );
  return (
    <section className="panel map-panel">
      <div className="panel-title">
        <h2>场景模型</h2>
        <div className="view-toggle">
          <button
            className={viewMode === "model" ? "chosen" : ""}
            onClick={() => setViewMode("model")}
          >
            立体视图
          </button>
          <button
            className={viewMode === "map" ? "chosen" : ""}
            onClick={() => setViewMode("map")}
          >
            俯视图
          </button>
        </div>
      </div>
      {viewMode === "model" ? (
        <WorldView scene={scene} frame={frame} history={history} />
      ) : (
        <svg
          className="map"
          viewBox={`${minX} ${minY} ${w} ${h}`}
          aria-label="地图与实际轨迹"
        >
          <defs>
            <pattern
              id="grid"
              width="1"
              height="1"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M1 0H0V1"
                fill="none"
                stroke="#dfe5df"
                strokeWidth=".018"
              />
            </pattern>
          </defs>
          <rect x={minX} y={minY} width={w} height={h} fill="url(#grid)" />
          {scene.distractors.map((p, i) => (
            <polyline
              key={i}
              points={view(p)}
              fill="none"
              stroke="#a8afa9"
              strokeWidth=".075"
            />
          ))}
          <polyline
            points={view(scene.target_path)}
            fill="none"
            stroke="#364951"
            strokeWidth=".065"
          />
          <polyline
            points={view(
              history.flatMap((r) =>
                r.pose ? [[r.pose.x_m, r.pose.y_m] as Point] : [],
              ),
            )}
            fill="none"
            stroke="#16a68e"
            strokeWidth=".06"
          />
          {prediction && (
            <polyline
              points={view(prediction)}
              fill="none"
              stroke="#9d6de1"
              strokeWidth=".065"
              strokeDasharray=".15 .08"
            />
          )}
          {[
            scene.target_path[0],
            scene.target_path[scene.target_path.length - 1],
          ].map(([x, y], i) => (
            <g key={i}>
              <circle cx={x} cy={-y} r=".14" fill={i ? "#eaa344" : "#26a475"} />
              <text
                x={x}
                y={-y - 0.27}
                textAnchor="middle"
                fontSize=".23"
                fill="#56636a"
              >
                {i ? "终点" : "起点 →"}
              </text>
            </g>
          ))}
          <g
            transform={`translate(${pose.x_m} ${-pose.y_m}) rotate(${(-pose.yaw_rad * 180) / Math.PI})`}
          >
            <rect
              x={-0.1}
              y={-scene.vehicle.width_m / 2}
              width={scene.vehicle.length_m}
              height={scene.vehicle.width_m}
              rx=".04"
              fill="#f2b550"
              stroke="#715c36"
              strokeWidth=".025"
            />
            <path
              d="M.09 -.065L.23 0 .09 .065"
              fill="none"
              stroke="#263840"
              strokeWidth=".035"
            />
            {[-1, 1].map((sign) => (
              <g key={sign}>
                <rect
                  x="-.055"
                  y={(sign * scene.vehicle.track_width_m) / 2 - 0.027}
                  width=".11"
                  height=".054"
                  fill="#263840"
                />
                <g
                  transform={`translate(${scene.vehicle.wheelbase_m} ${(sign * scene.vehicle.track_width_m) / 2}) rotate(${(-(pose.steering_angle_rad || 0) * 180) / Math.PI})`}
                >
                  <rect
                    x="-.055"
                    y="-.027"
                    width=".11"
                    height=".054"
                    fill="#263840"
                  />
                </g>
              </g>
            ))}
          </g>
        </svg>
      )}
      <div className="panel-foot">
        <i className="dot charcoal" />
        目标 <i className="dot gray" />
        干扰 <i className="dot teal" />
        最近 240 帧实际轨迹 <span className="muted"> / 网格 1 m</span>
      </div>
    </section>
  );
}

export function Charts({ history }: { history: History[] }) {
  const series = [
    {
      name: "横向偏差",
      unit: "m",
      color: "#d18c38",
      values: history.map((r) => r.evaluation?.lateral_error_m ?? null),
    },
    {
      name: "实际速度",
      unit: "m/s",
      color: "#168b78",
      values: history.map((r) => r.applied?.actual.speed_mps ?? null),
    },
    {
      name: "实际转角",
      unit: "rad",
      color: "#9070b9",
      values: history.map((r) => r.applied?.actual.steering_angle_rad ?? null),
    },
  ];
  return (
    <section className="panel">
      <div className="panel-title">
        <h2>运动与误差</h2>
        <span>最近 240 帧 · 仿真时间</span>
      </div>
      <div className="charts">
        {series.map((s) => {
          const valid = s.values.filter((v): v is number => v !== null);
          const max = Math.max(...valid, 0.05),
            min = Math.min(...valid, 0),
            range = Math.max(max - min, 0.01);
          // Null values split segments, so missing truth never becomes a fabricated zero.
          const segments: string[][] = [[]];
          s.values.forEach((v, i) => {
            if (v === null) {
              if (segments[segments.length - 1].length) segments.push([]);
            } else
              segments[segments.length - 1].push(
                `${8 + (i / Math.max(1, s.values.length - 1)) * 290},${65 - ((v - min) / range) * 50}`,
              );
          });
          return (
            <div className="chart" key={s.name}>
              <div>
                <span>{s.name}</span>
                <strong>
                  {fmt(s.values[s.values.length - 1])} <small>{s.unit}</small>
                </strong>
              </div>
              {valid.length ? (
                <svg viewBox="0 0 310 85">
                  <path
                    d="M8 15H298M8 65H298"
                    stroke="#e6e9e4"
                    strokeDasharray="3 3"
                  />
                  {segments.map((points, i) => (
                    <polyline
                      key={i}
                      points={points.join(" ")}
                      fill="none"
                      stroke={s.color}
                      strokeWidth="2"
                    />
                  ))}
                  <text x="8" y="80" fontSize="9" fill="#87908b">
                    {fmt(history[0]?.timestamp_s, 1)} s
                  </text>
                  <text
                    x="298"
                    y="80"
                    textAnchor="end"
                    fontSize="9"
                    fill="#87908b"
                  >
                    {fmt(history[history.length - 1]?.timestamp_s, 1)} s
                  </text>
                </svg>
              ) : (
                <div className="chart-unavailable">不提供</div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}
