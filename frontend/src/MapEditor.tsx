import { useEffect, useRef, useState, type PointerEvent } from "react";
import { api, fmt, post, type Point, type Preview, type Scene } from "./types";

type Design = NonNullable<Scene["design"]>;
type Draft = Pick<
  Scene,
  "name" | "seed" | "vehicle" | "camera" | "appearance"
> & { design: Design };
type SavedMap = { id: string; scene: Scene };
const defaultDesign: Design = {
  waypoints: [
    [0, 0],
    [6, 0],
    [6, 4],
    [0, 4],
  ],
  radius_m: 1,
};
const pointsText = (points: Point[]) =>
  points.map(([x, y]) => `${x},${-y}`).join(" ");

function NumberField({
  label,
  value,
  onChange,
  min,
  max,
  step = 0.01,
  ariaLabel,
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  ariaLabel?: string;
}) {
  return (
    <label>
      {label}
      <input
        aria-label={ariaLabel || label}
        type="number"
        min={min}
        max={max}
        step={step}
        value={Number(value.toFixed(3))}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </label>
  );
}

export function MapEditor({
  base,
  onApply,
  attempt,
  busy,
}: {
  base: Scene;
  onApply: (preview: Preview) => void;
  attempt: (operation: () => Promise<unknown>) => Promise<void>;
  busy: boolean;
}) {
  const [draft, setDraft] = useState<Draft>(() => ({
    name: base.design ? base.name : "我的地图",
    seed: base.seed,
    vehicle: base.vehicle,
    camera: base.camera,
    appearance: base.appearance,
    design: base.design || defaultDesign,
  }));
  const [preview, setPreview] = useState<Preview | null>(null);
  const [validation, setValidation] = useState("");
  const [pending, setPending] = useState(true);
  const [saved, setSaved] = useState<SavedMap[]>([]);
  const [message, setMessage] = useState("");
  const [view, setView] = useState([-3, -9, 16, 13]);
  const drag = useRef<number | null>(null);
  const builtDraft = useRef<Draft | null>(null);
  const { design, vehicle, camera, appearance } = draft;
  const minimum = vehicle.wheelbase_m / Math.tan(vehicle.max_steering_rad);
  const refresh = () => api<SavedMap[]>("/maps").then(setSaved);
  useEffect(() => {
    void refresh().catch((e) => setValidation(String(e)));
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setPending(true);
    setMessage("");
    const timer = window.setTimeout(() => {
      api<Preview>("/maps/build", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
        signal: controller.signal,
      })
        .then((data) => {
          builtDraft.current = draft;
          setPreview(data);
          setValidation("");
        })
        .catch((e) => {
          if (e.name !== "AbortError") {
            setValidation(e.message);
            setPreview(null);
          }
        })
        .finally(() => {
          if (!controller.signal.aborted) setPending(false);
        });
    }, 350);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [draft]);
  const editDesign = (patch: Partial<Design>) =>
    setDraft((old) => ({ ...old, design: { ...old.design, ...patch } }));
  const changePoint = (index: number, point: Point) =>
    setDraft((old) => ({
      ...old,
      design: {
        ...old.design,
        waypoints: old.design.waypoints.map((p, i) =>
          i === index ? point : p,
        ),
      },
    }));
  const coordinate = (e: PointerEvent<SVGSVGElement>): Point => {
    const matrix = e.currentTarget.getScreenCTM();
    if (!matrix) return [0, 0];
    const p = new DOMPoint(e.clientX, e.clientY).matrixTransform(
      matrix.inverse(),
    );
    const snap = (v: number) =>
      Math.max(-35, Math.min(35, Math.round(v * 10) / 10));
    return [snap(p.x), snap(-p.y)];
  };
  const fit = (points: Point[]) => {
    const xs = points.map((p) => p[0]),
      ys = points.map((p) => -p[1]);
    setView([
      Math.min(...xs) - 3,
      Math.min(...ys) - 3,
      Math.max(8, Math.max(...xs) - Math.min(...xs) + 6),
      Math.max(6, Math.max(...ys) - Math.min(...ys) + 6),
    ]);
  };
  const load = (scene: Scene) => {
    if (!scene.design)
      throw new Error("此 JSON 没有控制点设计，请使用编辑器导出的地图");
    setDraft({
      name: scene.name,
      seed: scene.seed,
      vehicle: scene.vehicle,
      camera: scene.camera,
      appearance: scene.appearance,
      design: scene.design,
    });
    fit(scene.design.waypoints);
  };
  const valid =
    !!preview?.scene && builtDraft.current === draft && !pending && !validation;
  return (
    <div className="map-editor-layout">
      <section className="panel editor-canvas-panel">
        <div className="panel-title">
          <h2>绘制路线</h2>
          <span>点击添加 · 拖动控制点 · 网格 1 m</span>
        </div>
        <div className="editor-actions">
          <button onClick={() => fit(design.waypoints)}>适配地图</button>
          <button
            disabled={design.waypoints.length <= 2}
            onClick={() =>
              editDesign({ waypoints: design.waypoints.slice(0, -1) })
            }
          >
            撤回末点
          </button>
          <button
            onClick={() => {
              editDesign(defaultDesign);
              fit(defaultDesign.waypoints);
            }}
          >
            恢复示例
          </button>
          <label className="compact-upload">
            导入 JSON
            <input
              aria-label="导入地图"
              type="file"
              accept=".json"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file)
                  void attempt(async () => {
                    if (file.size > 2 * 1024 ** 2)
                      throw new Error("地图 JSON 超过 2 MiB");
                    load(JSON.parse(await file.text()) as Scene);
                  });
                e.target.value = "";
              }}
            />
          </label>
        </div>
        <svg
          className="editor-canvas"
          aria-label="地图控制点画布"
          viewBox={view.join(" ")}
          onPointerDown={(e) => {
            if (design.waypoints.length < 60)
              editDesign({ waypoints: [...design.waypoints, coordinate(e)] });
          }}
          onPointerMove={(e) => {
            if (drag.current !== null) changePoint(drag.current, coordinate(e));
          }}
          onPointerUp={() => {
            drag.current = null;
          }}
          onPointerCancel={() => {
            drag.current = null;
          }}
        >
          <defs>
            <pattern
              id="editor-grid"
              width="1"
              height="1"
              patternUnits="userSpaceOnUse"
            >
              <path
                d="M1 0H0V1"
                fill="none"
                stroke="#ccd8d2"
                strokeWidth=".014"
              />
            </pattern>
          </defs>
          <rect
            x={view[0]}
            y={view[1]}
            width={view[2]}
            height={view[3]}
            fill="url(#editor-grid)"
          />
          <polyline
            points={pointsText(design.waypoints)}
            stroke="#9ba9a6"
            strokeWidth=".025"
            strokeDasharray=".12 .1"
            fill="none"
          />
          {preview?.scene && (
            <polyline
              points={pointsText(preview.scene.target_path)}
              fill="none"
              stroke={pending ? "#aabbb2" : "#197f6e"}
              strokeWidth=".09"
            />
          )}
          {preview?.scene && (
            <g
              transform={`translate(${preview.scene.initial_pose.x_m} ${-preview.scene.initial_pose.y_m}) rotate(${(-preview.scene.initial_pose.yaw_rad * 180) / Math.PI})`}
            >
              <rect
                x="-.1"
                y={-vehicle.width_m / 2}
                width={vehicle.length_m}
                height={vehicle.width_m}
                rx=".035"
                fill="#dda847"
              />
              <path
                d="M.1 -.08L.28 0 .1 .08"
                fill="none"
                stroke="#263c43"
                strokeWidth=".025"
              />
            </g>
          )}
          {design.waypoints.map(([x, y], index) => (
            <g key={index} transform={`translate(${x} ${-y})`}>
              <circle
                r=".15"
                className="control-point"
                fill={index === 0 ? "#20a87e" : "#fff"}
                stroke="#247d6d"
                strokeWidth=".035"
                aria-label={`控制点 ${index + 1}`}
                onPointerDown={(e) => {
                  e.stopPropagation();
                  drag.current = index;
                  (
                    e.currentTarget.ownerSVGElement as SVGSVGElement
                  ).setPointerCapture(e.pointerId);
                }}
              />
              <text x=".21" y="-.21" fontSize=".25" pointerEvents="none">
                {index + 1}
              </text>
            </g>
          ))}
        </svg>
        <div
          className={"editor-validation " + (validation ? "invalid" : "")}
          role="status"
        >
          {pending
            ? "正在检查几何约束…"
            : validation ||
              "路径检查通过：转弯半径、路段间距与起点视野满足要求。"}
        </div>
        <div className="editor-stats">
          <span>
            路线长度<strong>{fmt(preview?.geometry?.length_m)} m</strong>
          </span>
          <span>
            车辆最小半径<strong>{fmt(minimum, 3)} m</strong>
          </span>
          <span>
            路线最小半径
            <strong>
              {preview?.geometry?.minimum_path_radius_m == null
                ? "直线 / 待生成"
                : `${fmt(preview.geometry.minimum_path_radius_m, 3)} m`}
            </strong>
          </span>
        </div>
        <div className="editor-actions">
          <button
            className="primary"
            disabled={!valid || busy}
            onClick={() => preview && onApply(preview)}
          >
            应用到实验
          </button>
          <button
            disabled={!valid || busy}
            onClick={() =>
              attempt(async () => {
                await post("/maps", preview!.scene);
                await refresh();
                setMessage("地图已保存，下次打开仍可加载。");
              })
            }
          >
            保存地图
          </button>
          <button
            disabled={!valid}
            onClick={() => {
              const url = URL.createObjectURL(
                new Blob([JSON.stringify(preview!.scene, null, 2)], {
                  type: "application/json",
                }),
              );
              const a = document.createElement("a");
              a.href = url;
              a.download = "pathlab-map.json";
              a.click();
              URL.revokeObjectURL(url);
            }}
          >
            导出 JSON
          </button>
          <small>{message}</small>
        </div>
        {preview?.image && (
          <details className="editor-camera">
            <summary>起点摄像头预览</summary>
            <img
              alt="自定义地图摄像头预览"
              src={`data:image/png;base64,${preview.image}`}
            />
          </details>
        )}
      </section>
      <section className="panel padded-panel editor-options">
        <label>
          地图名称
          <input
            aria-label="地图名称"
            value={draft.name}
            maxLength={80}
            onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          />
        </label>
        <label>
          圆角半径 / m
          <input
            aria-label="圆角半径"
            type="number"
            min={(minimum * 1.02).toFixed(3)}
            max="10"
            step=".05"
            value={design.radius_m}
            onChange={(e) => editDesign({ radius_m: Number(e.target.value) })}
          />
          <small>至少 {(minimum * 1.02).toFixed(3)} m，含 2% 采样余量</small>
        </label>
        <details open>
          <summary>车辆与相机</summary>
          <div className="form-grid">
            <NumberField
              label="轴距 / m"
              ariaLabel="编辑轴距"
              value={vehicle.wheelbase_m}
              min={0.06}
              max={2}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  vehicle: { ...vehicle, wheelbase_m: value },
                })
              }
            />
            <NumberField
              label="最大转角 / °"
              ariaLabel="编辑最大转角"
              value={(vehicle.max_steering_rad * 180) / Math.PI}
              min={5}
              max={57}
              step={1}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  vehicle: {
                    ...vehicle,
                    max_steering_rad: (value * Math.PI) / 180,
                  },
                })
              }
            />
            <NumberField
              label="车宽 / m"
              ariaLabel="编辑车宽"
              value={vehicle.width_m}
              min={0.1}
              max={3}
              onChange={(value) =>
                setDraft({ ...draft, vehicle: { ...vehicle, width_m: value } })
              }
            />
            <NumberField
              label="相机高度 / m"
              value={camera.height_m}
              min={0.1}
              max={3}
              step={0.05}
              onChange={(value) =>
                setDraft({ ...draft, camera: { ...camera, height_m: value } })
              }
            />
            <NumberField
              label="相机俯角 / °"
              value={(camera.pitch_down_rad * 180) / Math.PI}
              min={9}
              max={74}
              step={1}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  camera: {
                    ...camera,
                    pitch_down_rad: (value * Math.PI) / 180,
                  },
                })
              }
            />
            <NumberField
              label="水平视场 / °"
              value={camera.horizontal_fov_deg}
              min={30}
              max={120}
              step={1}
              onChange={(value) =>
                setDraft({
                  ...draft,
                  camera: { ...camera, horizontal_fov_deg: value },
                })
              }
            />
          </div>
        </details>
        <details open>
          <summary>地面与线条</summary>
          <label>
            地面材质
            <select
              aria-label="地面材质"
              value={appearance.surface}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  appearance: {
                    ...appearance,
                    surface: e.target.value as Scene["appearance"]["surface"],
                  },
                })
              }
            >
              <option value="concrete">混凝土地坪</option>
              <option value="mat">实验地垫</option>
              <option value="plain">纯色地面</option>
            </select>
          </label>
          <NumberField
            label="线宽 / m"
            value={appearance.line_width_m}
            min={0.02}
            max={0.2}
            onChange={(value) =>
              setDraft({
                ...draft,
                appearance: { ...appearance, line_width_m: value },
              })
            }
          />
          <NumberField
            label="材质随机种子"
            value={draft.seed}
            min={0}
            max={4294967295}
            step={1}
            onChange={(value) => setDraft({ ...draft, seed: value })}
          />
          <label>
            材质强度
            <input
              aria-label="材质强度"
              type="range"
              min="0"
              max="1"
              step=".05"
              value={appearance.texture_strength}
              onChange={(e) =>
                setDraft({
                  ...draft,
                  appearance: {
                    ...appearance,
                    texture_strength: Number(e.target.value),
                  },
                })
              }
            />
          </label>
        </details>
        <details>
          <summary>控制点坐标 · {design.waypoints.length} 个</summary>
          <div className="waypoint-list">
            {design.waypoints.map((p, i) => (
              <div className="waypoint-row" key={i}>
                <span>{i + 1}</span>
                {[0, 1].map((axis) => (
                  <input
                    key={axis}
                    aria-label={`点 ${i + 1} ${axis ? "y" : "x"}`}
                    type="number"
                    min="-35"
                    max="35"
                    step=".1"
                    value={p[axis]}
                    onChange={(e) =>
                      changePoint(
                        i,
                        (axis
                          ? [p[0], Number(e.target.value)]
                          : [Number(e.target.value), p[1]]) as Point,
                      )
                    }
                  />
                ))}
                <button
                  aria-label={`删除控制点 ${i + 1}`}
                  disabled={design.waypoints.length <= 2}
                  onClick={() =>
                    editDesign({
                      waypoints: design.waypoints.filter(
                        (_, index) => index !== i,
                      ),
                    })
                  }
                >
                  ×
                </button>
              </div>
            ))}
          </div>
        </details>
        <details open>
          <summary>已保存地图 · {saved.length}</summary>
          {saved.map((map) => (
            <div className="saved-map" key={map.id}>
              <span>{map.scene.name}</span>
              <button onClick={() => attempt(async () => load(map.scene))}>
                加载
              </button>
              <button
                className="danger-button"
                aria-label={`删除地图 ${map.scene.name}`}
                onClick={() => {
                  if (
                    window.confirm(
                      `删除地图“${map.scene.name}”？已有运行记录不受影响。`,
                    )
                  )
                    void attempt(async () => {
                      await api(`/maps/${map.id}`, { method: "DELETE" });
                      await refresh();
                    });
                }}
              >
                ×
              </button>
            </div>
          ))}
          {!saved.length && (
            <p className="field-note">保存地图后可在此加载。</p>
          )}
        </details>
      </section>
    </div>
  );
}
