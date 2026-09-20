import { useState } from "react";
import type { DistractorDesign, Point } from "./types";

export function DistractorEditor({
  lines,
  selected,
  onSelect,
  onChange,
}: {
  lines: DistractorDesign[];
  selected: number;
  onSelect: (index: number) => void;
  onChange: (lines: DistractorDesign[]) => void;
}) {
  const [pointIndex, setPointIndex] = useState(0);
  const active = lines[selected];
  const index = Math.min(
    pointIndex,
    Math.max(0, (active?.waypoints.length || 1) - 1),
  );
  const point = active?.waypoints[index];
  const edit = (patch: Partial<DistractorDesign>) =>
    onChange(
      lines.map((line, i) => (i === selected ? { ...line, ...patch } : line)),
    );
  return (
    <div className="distractor-editor">
      <h3>独立干扰线 · {lines.length} 条</h3>
      <p className="field-note">
        点击“新增干扰线”，再在画布依次点按。每条线独立绘制，不与目标路线连接；起终点不设标记。线条交叉或过近会显示检查结果。
      </p>
      <div className="editor-actions">
        <button
          disabled={lines.length >= 20}
          onClick={() => {
            onSelect(lines.length);
            setPointIndex(0);
            onChange([...lines, { waypoints: [], interpolation: "polyline" }]);
          }}
        >
          新增干扰线
        </button>
        <button
          disabled={!active}
          onClick={() => {
            onChange(lines.filter((_, i) => i !== selected));
            onSelect(Math.max(0, selected - 1));
          }}
        >
          删除此干扰线
        </button>
      </div>
      {active && (
        <>
          <label>
            当前干扰线
            <select
              aria-label="当前干扰线"
              value={selected}
              onChange={(event) => {
                onSelect(Number(event.target.value));
                setPointIndex(0);
              }}
            >
              {lines.map((line, i) => (
                <option value={i} key={i}>
                  干扰线 {i + 1} · {line.waypoints.length} 点
                </option>
              ))}
            </select>
          </label>
          <label>
            线条形状
            <select
              aria-label="干扰线形状"
              value={active.interpolation}
              onChange={(event) =>
                edit({
                  interpolation: event.target
                    .value as DistractorDesign["interpolation"],
                })
              }
            >
              <option value="polyline">直线 / 折线</option>
              <option value="smooth">圆滑曲线</option>
            </select>
          </label>
          <p className="field-note">
            圆滑曲线保留首尾点，平滑中间折角；干扰线不受车辆转弯半径约束。
          </p>
          {point && (
            <>
              <label>
                干扰控制点
                <select
                  aria-label="干扰控制点"
                  value={index}
                  onChange={(event) =>
                    setPointIndex(Number(event.target.value))
                  }
                >
                  {active.waypoints.map((_, i) => (
                    <option value={i} key={i}>
                      {i + 1}
                    </option>
                  ))}
                </select>
              </label>
              <div className="form-grid">
                {[0, 1].map((axis) => (
                  <label key={axis}>
                    {axis ? "Y" : "X"} / m
                    <input
                      aria-label={`干扰点 ${axis ? "Y" : "X"}`}
                      type="number"
                      min={-40}
                      max={40}
                      step=".1"
                      value={point[axis]}
                      onChange={(event) =>
                        edit({
                          waypoints: active.waypoints.map((p, i) =>
                            i === index
                              ? ((axis
                                  ? [p[0], Number(event.target.value)]
                                  : [
                                      Number(event.target.value),
                                      p[1],
                                    ]) as Point)
                              : p,
                          ),
                        })
                      }
                    />
                  </label>
                ))}
              </div>
              <button
                onClick={() =>
                  edit({
                    waypoints: active.waypoints.filter((_, i) => i !== index),
                  })
                }
              >
                删除此干扰控制点
              </button>
            </>
          )}
        </>
      )}
    </div>
  );
}
