import { useState } from "react";
import type { ObjectScatter, Point, SceneObject } from "./types";

export const objectNames: Record<SceneObject["kind"], string> = {
  cone: "交通锥",
  box: "纸箱",
  barrier: "隔离栏",
  cylinder: "圆桶",
};
const presets: Record<
  SceneObject["kind"],
  [number, number, number, [number, number, number]]
> = {
  cone: [0.35, 0.35, 0.5, [232, 108, 38]],
  box: [0.5, 0.42, 0.46, [162, 124, 83]],
  barrier: [0.85, 0.3, 0.55, [230, 179, 52]],
  cylinder: [0.4, 0.4, 0.65, [67, 124, 158]],
};

export function createSceneObject(
  kind: SceneObject["kind"],
  [x_m, y_m]: Point,
): SceneObject {
  const [length_m, width_m, height_m, color_rgb] = presets[kind];
  return {
    kind,
    x_m,
    y_m,
    yaw_rad: 0,
    length_m,
    width_m,
    height_m,
    color_rgb,
    enabled: true,
    collidable: true,
  };
}

export function SceneObjectEditor({
  objects,
  onChange,
  onScatter,
  origin,
  busy,
  selected,
  onSelect,
  kind,
  onKindChange,
}: {
  objects: SceneObject[];
  onChange: (objects: SceneObject[]) => void;
  onScatter: (options: ObjectScatter) => void;
  origin: Point;
  busy: boolean;
  selected: number;
  onSelect: (index: number) => void;
  kind: SceneObject["kind"];
  onKindChange: (kind: SceneObject["kind"]) => void;
}) {
  const [scatter, setScatter] = useState<ObjectScatter>({
    count: 12,
    kinds: ["cone", "box", "barrier", "cylinder"],
    clearance_m: 0.65,
    spread_m: 2.5,
    scale: 1,
  });
  const active = objects[Math.min(selected, objects.length - 1)];
  const activeIndex = objects.indexOf(active);
  const edit = (patch: Partial<SceneObject>) =>
    onChange(
      objects.map((item, index) =>
        index === activeIndex ? { ...item, ...patch } : item,
      ),
    );
  const add = () => {
    onChange([
      ...objects,
      createSceneObject(kind, [origin[0] + 1, origin[1] + 1.5]),
    ]);
    onSelect(objects.length);
  };
  return (
    <details open className="scene-object-editor">
      <summary>
        场景物件 · {objects.filter((item) => item.enabled).length} 个启用
      </summary>
      <p className="field-note">
        选择类型后点按画布放置，拖动物件调整位置。物件具有真实尺寸、投影和遮挡；自动布置避开路线。
      </p>
      <div className="form-grid">
        <label>
          自动数量
          <input
            aria-label="自动物件数量"
            type="number"
            min="0"
            max="60"
            value={scatter.count}
            onChange={(event) =>
              setScatter({ ...scatter, count: Number(event.target.value) })
            }
          />
        </label>
        <label>
          整体尺寸倍率
          <input
            aria-label="物件尺寸倍率"
            type="number"
            min=".4"
            max="2"
            step=".1"
            value={scatter.scale}
            onChange={(event) =>
              setScatter({ ...scatter, scale: Number(event.target.value) })
            }
          />
        </label>
        <label>
          路线净距 / m
          <input
            aria-label="物件路线净距"
            type="number"
            min=".25"
            max="5"
            step=".1"
            value={scatter.clearance_m}
            onChange={(event) =>
              setScatter({
                ...scatter,
                clearance_m: Number(event.target.value),
              })
            }
          />
        </label>
        <label>
          散布宽度 / m
          <input
            aria-label="物件散布范围"
            type="number"
            min=".5"
            max="8"
            step=".5"
            value={scatter.spread_m}
            onChange={(event) =>
              setScatter({ ...scatter, spread_m: Number(event.target.value) })
            }
          />
        </label>
      </div>
      <div className="object-kinds">
        {Object.entries(objectNames).map(([value, label]) => (
          <label key={value}>
            <input
              type="checkbox"
              checked={scatter.kinds.includes(value as SceneObject["kind"])}
              onChange={(event) =>
                setScatter({
                  ...scatter,
                  kinds: event.target.checked
                    ? [...scatter.kinds, value as SceneObject["kind"]]
                    : scatter.kinds.filter((item) => item !== value),
                })
              }
            />
            {label}
          </label>
        ))}
      </div>
      <div className="editor-actions">
        <button
          disabled={busy || !scatter.kinds.length}
          onClick={() => onScatter(scatter)}
        >
          重新自动布置
        </button>
        <button
          disabled={!objects.length}
          onClick={() =>
            onChange(
              objects.map((item) => ({
                ...item,
                enabled: !objects.some((obj) => obj.enabled),
              })),
            )
          }
        >
          {objects.some((item) => item.enabled) ? "全部隐藏" : "全部显示"}
        </button>
        <button disabled={!objects.length} onClick={() => onChange([])}>
          清空物件
        </button>
      </div>
      <div className="object-add-row">
        <select
          aria-label="添加物件类型"
          value={kind}
          onChange={(event) =>
            onKindChange(event.target.value as SceneObject["kind"])
          }
        >
          {Object.entries(objectNames).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button disabled={objects.length >= 80} onClick={add}>
          添加物件
        </button>
      </div>
      {active && (
        <>
          <label>
            编辑物件
            <select
              aria-label="当前编辑物件"
              value={activeIndex}
              onChange={(event) => onSelect(Number(event.target.value))}
            >
              {objects.map((item, index) => (
                <option key={index} value={index}>
                  {index + 1}. {objectNames[item.kind]}
                  {item.enabled ? "" : " · 已隐藏"}
                </option>
              ))}
            </select>
          </label>
          <div className="form-grid">
            {(["x_m", "y_m", "length_m", "width_m", "height_m"] as const).map(
              (key, index) => (
                <label key={key}>
                  {
                    [
                      "位置 X / m",
                      "位置 Y / m",
                      "长度 / m",
                      "宽度 / m",
                      "高度 / m",
                    ][index]
                  }
                  <input
                    aria-label={`物件${["X", "Y", "长度", "宽度", "高度"][index]}`}
                    type="number"
                    min={index < 2 ? -40 : 0.08}
                    max={index < 2 ? 40 : 3}
                    step=".05"
                    value={Number(active[key].toFixed(3))}
                    onChange={(event) =>
                      edit({ [key]: Number(event.target.value) })
                    }
                  />
                </label>
              ),
            )}
            <label>
              朝向 / °
              <input
                aria-label="物件朝向"
                type="number"
                min="-180"
                max="180"
                step="5"
                value={Math.round((active.yaw_rad * 180) / Math.PI)}
                onChange={(event) =>
                  edit({
                    yaw_rad: (Number(event.target.value) * Math.PI) / 180,
                  })
                }
              />
            </label>
            <label>
              颜色
              <input
                aria-label="物件颜色"
                type="color"
                value={
                  "#" +
                  active.color_rgb
                    .map((channel) => channel.toString(16).padStart(2, "0"))
                    .join("")
                }
                onChange={(event) =>
                  edit({
                    color_rgb: [1, 3, 5].map((start) =>
                      parseInt(event.target.value.slice(start, start + 2), 16),
                    ) as [number, number, number],
                  })
                }
              />
            </label>
          </div>
          <div className="object-kinds">
            <label>
              <input
                type="checkbox"
                checked={active.enabled}
                onChange={(event) => edit({ enabled: event.target.checked })}
              />
              显示物件
            </label>
            <label>
              <input
                type="checkbox"
                checked={active.collidable}
                onChange={(event) => edit({ collidable: event.target.checked })}
              />
              检测碰撞
            </label>
          </div>
          <button
            className="danger-button"
            onClick={() =>
              onChange(objects.filter((_, index) => index !== activeIndex))
            }
          >
            删除此物件
          </button>
        </>
      )}
    </details>
  );
}
