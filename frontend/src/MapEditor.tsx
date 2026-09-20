import { useEffect, useMemo, useRef, useState, type PointerEvent } from "react";
import { api, fmt, post, type Point, type Preview, type Scene } from "./types";
import {
  SceneObjectEditor,
  createSceneObject,
  objectNames,
} from "./SceneObjectEditor";
import { DistractorEditor } from "./DistractorEditor";
import { VehicleSettings } from "./VehicleSettings";
import { matchesShape, usePersistentState } from "./usePersistentState";
import type { SavedMap, SceneObject } from "./types";

type Design = NonNullable<Scene["design"]>;
type Draft = Pick<
  Scene,
  "name" | "seed" | "vehicle" | "camera" | "appearance"
> & { design: Design; objects: SceneObject[]; source_scene?: Scene };
const defaultDesign: Design = {
  waypoints: [
    [0, 0],
    [6, 0],
    [6, 4],
    [0, 4],
  ],
  radius_m: 1,
  distractors: [],
};
const sceneDesign = (scene: Scene): Design => ({
  ...(scene.design || defaultDesign),
  distractors:
    scene.design?.distractors ??
    scene.distractors.map((waypoints) => ({
      waypoints,
      interpolation: "polyline" as const,
    })),
});
const pointsText = (points: Point[]) =>
  points.map(([x, y]) => `${x},${-y}`).join(" ");

function mapBounds(points: Point[]) {
  if (!points.length) return [-3, -9, 16, 13];
  const xs = points.map((p) => p[0]),
    ys = points.map((p) => -p[1]);
  return [
    Math.min(...xs) - 3,
    Math.min(...ys) - 3,
    Math.max(8, Math.max(...xs) - Math.min(...xs) + 6),
    Math.max(6, Math.max(...ys) - Math.min(...ys) + 6),
  ];
}

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
  onMapsChange,
}: {
  base: Scene;
  onApply: (preview: Preview) => void;
  attempt: (operation: () => Promise<unknown>) => Promise<void>;
  busy: boolean;
  onMapsChange: (maps: SavedMap[]) => void;
}) {
  const initialDraft = (): Draft => ({
    name: base.design ? base.name : "我的地图",
    seed: base.seed,
    vehicle: base.vehicle,
    camera: base.camera,
    appearance: base.appearance,
    design: base.design ? sceneDesign(base) : defaultDesign,
    objects: base.design ? base.objects || [] : [],
    source_scene: base.design ? base : undefined,
  });
  const [draft, setDraft, storageError] = usePersistentState<Draft>(
    "pathlab.map-draft.v1",
    initialDraft,
    (value) => {
      const shape = {
        ...initialDraft(),
        source_scene: undefined,
        design: {
          waypoints: [[0, 0]],
          radius_m: 1,
          distractors: [{ waypoints: [[0, 0]], interpolation: "polyline" }],
        },
        objects: [createSceneObject("cone", [0, 0])],
      };
      if (!matchesShape(value, shape)) throw new Error("Invalid map draft");
      return value as Draft;
    },
  );
  const [mode, setMode] = useState<"target" | "distractor" | "object">(
    "target",
  );
  const [selectedLine, setSelectedLine] = useState(0);
  const [selectedObject, setSelectedObject] = useState(0);
  const [objectKind, setObjectKind] = useState<SceneObject["kind"]>("cone");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [validation, setValidation] = useState("");
  const [pending, setPending] = useState(true);
  const [saved, setSaved] = useState<SavedMap[]>([]);
  const [message, setMessage] = useState("");
  const [view, setView] = useState(() =>
    mapBounds([
      ...draft.design.waypoints,
      ...(draft.design.distractors || []).flatMap((line) => line.waypoints),
      ...draft.objects.map((obj): Point => [obj.x_m, obj.y_m]),
    ]),
  );
  const drag = useRef<number | null>(null);
  const objectDrag = useRef<number | null>(null);
  const lineDrag = useRef<[number, number] | null>(null);
  const builtDraft = useRef<Draft | null>(null);
  const { design, vehicle, camera, appearance } = draft;
  const lines = design.distractors || [];
  const vehicleScene = useMemo(() => ({ ...base, ...draft }), [base, draft]);
  const minimum = vehicle.wheelbase_m / Math.tan(vehicle.max_steering_rad);
  const refresh = () =>
    api<SavedMap[]>("/maps").then((maps) => {
      setSaved(maps);
      onMapsChange(maps);
    });
  useEffect(() => {
    void refresh().catch((e) => setValidation(String(e)));
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setPending(true);
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
  const changeLinePoint = (
    lineIndex: number,
    pointIndex: number,
    point: Point,
  ) =>
    setDraft((old) => ({
      ...old,
      design: {
        ...old.design,
        distractors: (old.design.distractors || []).map((line, i) =>
          i === lineIndex
            ? {
                ...line,
                waypoints: line.waypoints.map((p, j) =>
                  j === pointIndex ? point : p,
                ),
              }
            : line,
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
    setView(mapBounds(points));
  };
  const load = async (scene: Scene) => {
    if (!scene.design)
      throw new Error("此 JSON 没有控制点设计，请使用编辑器导出的地图");
    const normalized = await post<Preview>("/maps/build", {
      name: scene.name,
      seed: scene.seed,
      design: sceneDesign(scene),
      source_scene: scene,
      objects: scene.objects || [],
    });
    if (!normalized.scene) throw new Error("无法读取地图场景");
    setDraft({
      name: scene.name,
      seed: scene.seed,
      vehicle: normalized.scene.vehicle,
      camera: normalized.scene.camera,
      appearance: normalized.scene.appearance,
      design: sceneDesign(scene),
      objects: scene.objects || [],
      source_scene: scene,
    });
    setSelectedLine(0);
    setSelectedObject(0);
    fit([
      ...scene.design.waypoints,
      ...scene.distractors.flat(),
      ...(scene.objects || []).map((obj): Point => [obj.x_m, obj.y_m]),
    ]);
  };
  const valid =
    !!preview?.scene && builtDraft.current === draft && !pending && !validation;
  return (
    <div className="map-editor-layout">
      <section className="panel editor-canvas-panel">
        <div className="panel-title">
          <h2>地图分层编辑</h2>
          <span>点击放置 · 拖动调整 · 网格 1 m</span>
        </div>
        <div className="editor-mode-tabs" aria-label="地图编辑模式">
          {(
            [
              ["target", "目标路线"],
              ["distractor", "干扰线"],
              ["object", "障碍物"],
            ] as const
          ).map(([value, label]) => (
            <button
              key={value}
              aria-pressed={mode === value}
              onClick={() => setMode(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <p className="editor-mode-hint">
          {mode === "target"
            ? "正在编辑目标路线：点按追加目标控制点，拖动绿色控制点调整路线。"
            : mode === "distractor"
              ? `正在编辑干扰线：${lines[selectedLine] ? `点按追加到干扰线 ${selectedLine + 1}，拖动紫色控制点调整。` : "请先点击右侧“新增干扰线”，再点按画布。"}`
              : `正在编辑障碍物：点按画布放置${objectNames[objectKind]}，点选或拖动物件调整；右侧可更改类型和尺寸。`}
        </p>
        {draft.source_scene?.render_version !== "3" && draft.source_scene && (
          <p className="editor-upgrade-note">
            旧地图将保存为场景版本
            3，使障碍物具有真实投影和遮挡。未修改的路线、车辆、相机和初始位置保持原值；原文件不变。
          </p>
        )}
        <div className="editor-actions">
          <button
            onClick={() =>
              fit([
                ...design.waypoints,
                ...lines.flatMap((line) => line.waypoints),
                ...draft.objects.map((obj): Point => [obj.x_m, obj.y_m]),
              ])
            }
          >
            适配地图
          </button>
          <button
            disabled={
              mode === "object" ||
              (mode === "target"
                ? design.waypoints.length <= 2
                : !lines[selectedLine]?.waypoints.length)
            }
            onClick={() =>
              mode === "target"
                ? editDesign({ waypoints: design.waypoints.slice(0, -1) })
                : editDesign({
                    distractors: lines.map((line, i) =>
                      i === selectedLine
                        ? { ...line, waypoints: line.waypoints.slice(0, -1) }
                        : line,
                    ),
                  })
            }
          >
            撤回末点
          </button>
          <button
            onClick={() => {
              editDesign({
                waypoints: defaultDesign.waypoints,
                radius_m: defaultDesign.radius_m,
              });
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
                    await load(JSON.parse(await file.text()) as Scene);
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
            if (mode === "object" && draft.objects.length < 80) {
              setSelectedObject(draft.objects.length);
              setDraft({
                ...draft,
                objects: [
                  ...draft.objects,
                  createSceneObject(objectKind, coordinate(e)),
                ],
              });
            } else if (mode === "distractor" && lines[selectedLine]) {
              editDesign({
                distractors: lines.map((line, i) =>
                  i === selectedLine
                    ? {
                        ...line,
                        waypoints: [...line.waypoints, coordinate(e)],
                      }
                    : line,
                ),
              });
            } else if (mode === "target" && design.waypoints.length < 60)
              editDesign({ waypoints: [...design.waypoints, coordinate(e)] });
          }}
          onPointerMove={(e) => {
            if (drag.current !== null) changePoint(drag.current, coordinate(e));
            if (lineDrag.current !== null)
              changeLinePoint(...lineDrag.current, coordinate(e));
            if (objectDrag.current !== null) {
              const [x_m, y_m] = coordinate(e);
              setDraft((old) => ({
                ...old,
                objects: old.objects.map((obj, index) =>
                  index === objectDrag.current ? { ...obj, x_m, y_m } : obj,
                ),
              }));
            }
          }}
          onPointerUp={() => {
            drag.current = null;
            objectDrag.current = null;
            lineDrag.current = null;
          }}
          onPointerCancel={() => {
            drag.current = null;
            objectDrag.current = null;
            lineDrag.current = null;
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
          {lines.map((line, lineIndex) => (
            <g key={`line-${lineIndex}`}>
              <polyline
                points={pointsText(
                  preview?.scene?.distractors[lineIndex] || line.waypoints,
                )}
                fill="none"
                stroke={
                  lineIndex === selectedLine && mode === "distractor"
                    ? "#9852bf"
                    : "#665c73"
                }
                strokeWidth=".065"
                pointerEvents="none"
              />
              {mode === "distractor" &&
                line.waypoints.map(
                  ([x, y], pointIndex) =>
                    (pointIndex %
                      Math.max(1, Math.ceil(line.waypoints.length / 80)) ===
                      0 ||
                      pointIndex === line.waypoints.length - 1) && (
                      <circle
                        key={pointIndex}
                        cx={x}
                        cy={-y}
                        r=".12"
                        fill={lineIndex === selectedLine ? "#ead9f4" : "#fff"}
                        stroke="#8b4fac"
                        strokeWidth=".03"
                        className="control-point"
                        aria-label={`干扰线 ${lineIndex + 1} 控制点 ${pointIndex + 1}`}
                        onPointerDown={(event) => {
                          event.stopPropagation();
                          setSelectedLine(lineIndex);
                          lineDrag.current = [lineIndex, pointIndex];
                          event.currentTarget.ownerSVGElement?.setPointerCapture(
                            event.pointerId,
                          );
                        }}
                      />
                    ),
                )}
            </g>
          ))}
          {preview?.scene && (
            <g
              transform={`translate(${preview.scene.initial_pose.x_m} ${-preview.scene.initial_pose.y_m}) rotate(${(-preview.scene.initial_pose.yaw_rad * 180) / Math.PI})`}
            >
              <rect
                x={(vehicle.wheelbase_m - vehicle.length_m) / 2}
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
          {mode === "target" &&
            design.waypoints.map(([x, y], index) => (
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
          {draft.objects.map(
            (obj, index) =>
              obj.enabled && (
                <g
                  key={`object-${index}`}
                  transform={`translate(${obj.x_m} ${-obj.y_m}) rotate(${(-obj.yaw_rad * 180) / Math.PI})`}
                  className="object-map-handle"
                  aria-label={`场景物件 ${index + 1} ${objectNames[obj.kind]}`}
                  onPointerDown={(event) => {
                    event.stopPropagation();
                    setMode("object");
                    setSelectedObject(index);
                    objectDrag.current = index;
                    event.currentTarget.ownerSVGElement?.setPointerCapture(
                      event.pointerId,
                    );
                  }}
                >
                  {obj.kind === "cylinder" ? (
                    <ellipse
                      rx={obj.length_m / 2}
                      ry={obj.width_m / 2}
                      fill={`rgb(${obj.color_rgb.join(",")})`}
                    />
                  ) : (
                    <rect
                      x={-obj.length_m / 2}
                      y={-obj.width_m / 2}
                      width={obj.length_m}
                      height={obj.width_m}
                      rx=".025"
                      fill={`rgb(${obj.color_rgb.join(",")})`}
                    />
                  )}
                  <text
                    x="0"
                    y=".07"
                    textAnchor="middle"
                    fontSize=".18"
                    pointerEvents="none"
                  >
                    {index + 1}
                  </text>
                </g>
              ),
          )}
        </svg>
        <div
          className={"editor-validation " + (validation ? "invalid" : "")}
          role="status"
          aria-label="地图几何检查"
        >
          {pending
            ? "正在检查几何约束…"
            : validation ||
              "路径几何检查通过：半径、间距与相机范围符合要求。物件遮挡与碰撞在运行时评估。"}
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
                const saved = await post<SavedMap>("/maps", preview!.scene);
                setDraft((current) => ({ ...current, name: saved.scene.name }));
                await refresh();
                setMessage(
                  `已保存为「${saved.scene.name}」，可在主页场景选择中直接加载。`,
                );
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
        <p
          className={storageError ? "editor-validation invalid" : "field-note"}
          role="status"
          aria-label="地图草稿保存状态"
        >
          {storageError ||
            "草稿自动保存在此浏览器，刷新或切换页面后可继续编辑。点击「保存地图」可保存到服务器，供批量评测或其他浏览器加载。"}
        </p>
        {preview?.image && (
          <details className="editor-camera" open>
            <summary>起点摄像头预览</summary>
            <img
              alt="自定义地图摄像头预览"
              src={`data:image/png;base64,${preview.image}`}
            />
          </details>
        )}
      </section>
      <section className="panel padded-panel editor-options">
        {mode === "distractor" && (
          <DistractorEditor
            lines={lines}
            selected={selectedLine}
            onSelect={setSelectedLine}
            onChange={(distractors) => editDesign({ distractors })}
          />
        )}
        {mode === "object" && (
          <SceneObjectEditor
            objects={draft.objects}
            origin={design.waypoints[0]}
            busy={pending || busy}
            selected={selectedObject}
            onSelect={setSelectedObject}
            kind={objectKind}
            onKindChange={setObjectKind}
            onChange={(objects) => setDraft({ ...draft, objects })}
            onScatter={(scatter) =>
              void attempt(async () => {
                const result = await post<Preview>("/maps/build", {
                  ...draft,
                  objects: [],
                  scatter,
                });
                const objects = result.scene?.objects || [];
                setDraft({ ...draft, objects });
                fit([
                  ...design.waypoints,
                  ...lines.flatMap((line) => line.waypoints),
                  ...objects.map((obj): Point => [obj.x_m, obj.y_m]),
                ]);
              })
            }
          />
        )}
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
          <label>
            场景亮度
            <input
              aria-label="场景亮度"
              type="range"
              min=".4"
              max="1.3"
              step=".05"
              value={Number(appearance.illumination ?? 1)}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  appearance: {
                    ...appearance,
                    illumination: Number(event.target.value),
                  },
                })
              }
            />
          </label>
          <label>
            阴影方位 / °
            <input
              aria-label="阴影方位"
              type="range"
              min="-180"
              max="180"
              step="5"
              value={Math.round(
                ((appearance.sun_azimuth_rad ?? -0.8) * 180) / Math.PI,
              )}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  appearance: {
                    ...appearance,
                    sun_azimuth_rad:
                      (Number(event.target.value) * Math.PI) / 180,
                  },
                })
              }
            />
          </label>
          <label className="object-toggle">
            <input
              type="checkbox"
              checked={appearance.object_shadows ?? true}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  appearance: {
                    ...appearance,
                    object_shadows: event.target.checked,
                  },
                })
              }
            />
            物件投影阴影
          </label>
        </details>
        <VehicleSettings
          scene={vehicleScene}
          disabled={busy}
          apply={(scene) =>
            setDraft((current) => ({ ...current, vehicle: scene.vehicle }))
          }
        />
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
              <span>
                {map.scene.name}
                <small>
                  #{map.id.slice(0, 8)} ·{" "}
                  {map.scene.design?.waypoints.length ?? 0} 个控制点
                </small>
              </span>
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
