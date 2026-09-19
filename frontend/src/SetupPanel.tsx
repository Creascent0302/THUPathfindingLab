import {
  api,
  post,
  type Algorithm,
  type Capability,
  type Hint,
  type Mode,
  type Preview,
  type Scene,
} from "./types";

export type Setup = {
  mode: Mode;
  family: string;
  seed: number;
  algorithm: string;
  execution: Capability;
  parameters: string;
  hint: Hint | null;
  hintMode: "point" | "region" | null;
  source: { id: string; frame_count: number } | null;
  preview: Preview;
  customScene: Scene | null;
  sceneText: string;
  maxSteps: number;
  timeout: number;
  recordImages: boolean;
  stress: boolean;
  delay: number;
  drop: number;
};
export const initialSetup: Setup = {
  mode: "simulation",
  family: "straight",
  seed: 7,
  algorithm: "manual",
  execution: "action",
  parameters: "{}",
  hint: null,
  hintMode: null,
  source: null,
  preview: { image: null, scene: null, calibration: null },
  customScene: null,
  sceneText: "",
  maxSteps: 4000,
  timeout: 1,
  recordImages: false,
  stress: false,
  delay: 0,
  drop: 0,
};

export function SetupPanel({
  settings,
  updateSettings,
  catalog,
  active,
  busy,
  attempt,
  clearView,
  changeMode,
}: {
  settings: Setup;
  updateSettings: (patch: Partial<Setup>) => void;
  catalog: { algorithms: Algorithm[]; families: Record<string, string> };
  active: boolean;
  busy: boolean;
  attempt: (operation: () => Promise<unknown>) => Promise<void>;
  clearView: () => void;
  changeMode: (mode: Mode) => void;
}) {
  const {
    mode,
    family,
    seed,
    algorithm,
    execution,
    parameters,
    hint,
    hintMode,
    source,
    sceneText,
    maxSteps,
    timeout,
    recordImages,
    stress,
    delay,
    drop,
  } = settings;
  const plugin = catalog.algorithms.find((a) => a.id === algorithm);
  return (
    <div className="sidebar-section">
      <h3>实验配置</h3>
      <label>
        输入来源
        <select
          aria-label="输入来源"
          disabled={active}
          value={mode}
          onChange={(e) => changeMode(e.target.value as Mode)}
        >
          <option value="simulation">闭环仿真</option>
          <option value="image">单帧图像</option>
          <option value="sequence">视频 / 图像序列</option>
        </select>
      </label>
      {mode === "simulation" ? (
        <>
          <label>
            场景
            <select
              aria-label="场景"
              disabled={active}
              value={family}
              onChange={(e) => {
                updateSettings({ family: e.target.value });
                clearView();
              }}
            >
              {settings.customScene && (
                <option value="custom">
                  自定义 · {settings.customScene.name}
                </option>
              )}
              {Object.entries(catalog.families).map(([id, title]) => (
                <option key={id} value={id}>
                  {title}
                </option>
              ))}
            </select>
          </label>
          <label>
            随机种子
            <input
              aria-label="随机种子"
              type="number"
              min="0"
              max="4294967295"
              disabled={active || family === "custom"}
              value={seed}
              onChange={(e) => {
                updateSettings({ seed: Number(e.target.value) });
                clearView();
              }}
            />
          </label>
        </>
      ) : (
        <label className="upload">
          {busy ? "正在导入…" : "选择素材"}
          <input
            aria-label="上传素材"
            type="file"
            accept="image/*,video/*"
            multiple={mode === "sequence"}
            disabled={active || busy}
            onChange={(e) => {
              const files = e.target.files;
              if (!files?.length) return;
              void attempt(async () => {
                const form = new FormData();
                Array.from(files).forEach((file) => form.append("files", file));
                form.append("fps", "20");
                const result = await api<{
                  id: string;
                  frame_count: number;
                }>("/sources", { method: "POST", body: form });
                updateSettings({ source: result });
                clearView();
                updateSettings({
                  preview: await api<Preview>(`/sources/${result.id}/preview`),
                });
              });
            }}
          />
          <small>
            {source
              ? `已导入 ${source.frame_count} 帧`
              : "最多 32 MiB / 600 帧，序列按文件名自然排序"}
          </small>
        </label>
      )}
      <label>
        算法 / 操作方式
        <select
          aria-label="算法"
          disabled={active}
          value={algorithm}
          onChange={(e) => {
            updateSettings({ algorithm: e.target.value });
            const p = catalog.algorithms.find((a) => a.id === e.target.value);
            updateSettings({ execution: p?.capabilities[0] || "action" });
            updateSettings({ parameters: "{}" });
            clearView();
          }}
        >
          {catalog.algorithms
            .filter((a) => mode === "simulation" || a.id !== "manual")
            .map((a) => (
              <option
                key={a.id}
                value={a.id}
                disabled={a.available === false}
                title={a.unavailable_reason || undefined}
              >
                {a.name}
                {a.available === false ? "（不可用）" : ""}
              </option>
            ))}
        </select>
      </label>
      <p className="field-note">{plugin?.description}</p>
      {catalog.algorithms
        .filter((a) => a.available === false)
        .map((a) => (
          <p className="field-note" key={a.id}>
            {a.name}：{a.unavailable_reason}
          </p>
        ))}
      <label>
        执行依据
        <select
          disabled={active}
          value={execution}
          onChange={(e) =>
            updateSettings({ execution: e.target.value as Capability })
          }
        >
          {(plugin?.capabilities || ["action"]).map((c) => (
            <option key={c} value={c}>
              {c === "action"
                ? "直接动作 action"
                : c === "path"
                  ? "局部路径 path"
                  : "仅感知 perception"}
            </option>
          ))}
        </select>
      </label>
      <details>
        <summary>参数与初始化提示</summary>
        <label>
          算法参数 JSON
          <textarea
            aria-label="算法参数"
            disabled={active}
            value={parameters}
            onChange={(e) => updateSettings({ parameters: e.target.value })}
            rows={5}
          />
        </label>
        <div className="mini-buttons">
          <button
            disabled={active}
            className={hintMode === "point" ? "chosen" : ""}
            onClick={() => updateSettings({ hintMode: "point" })}
          >
            点击目标
          </button>
          <button
            disabled={active}
            className={hintMode === "region" ? "chosen" : ""}
            onClick={() => updateSettings({ hintMode: "region" })}
          >
            框选起点
          </button>
          <button
            disabled={active}
            onClick={() => {
              updateSettings({ hint: null });
              updateSettings({ hintMode: null });
            }}
          >
            默认提示
          </button>
        </div>
        <small className="field-note">
          {hint
            ? JSON.stringify(hint)
            : mode === "simulation"
              ? "绿色起点圆环 + 行进箭头"
              : "无默认提示；可在首帧手动指定"}
        </small>
      </details>
      <details>
        <summary>时限与压力测试</summary>
        <label>
          最大步数
          <input
            disabled={active}
            type="number"
            min="1"
            max="6000"
            value={maxSteps}
            onChange={(e) =>
              updateSettings({ maxSteps: Number(e.target.value) })
            }
          />
        </label>
        <label>
          推理硬超时 / s
          <input
            disabled={active}
            type="number"
            min=".05"
            max="10"
            step=".05"
            value={timeout}
            onChange={(e) =>
              updateSettings({ timeout: Number(e.target.value) })
            }
          />
        </label>
        <label className="check">
          <input
            type="checkbox"
            disabled={active}
            checked={recordImages}
            onChange={(e) => updateSettings({ recordImages: e.target.checked })}
          />
          额外保存图像（最多 128 MiB）
        </label>
        <label className="check">
          <input
            type="checkbox"
            disabled={active}
            checked={stress}
            onChange={(e) => updateSettings({ stress: e.target.checked })}
          />
          启用延迟与掉帧压力测试
        </label>
        {stress && (
          <>
            <label>
              延迟帧数
              <input
                type="number"
                min="0"
                max="30"
                disabled={active}
                value={delay}
                onChange={(e) =>
                  updateSettings({ delay: Number(e.target.value) })
                }
              />
            </label>
            <label>
              掉帧概率
              <input
                type="number"
                min="0"
                max=".95"
                step=".05"
                disabled={active}
                value={drop}
                onChange={(e) =>
                  updateSettings({ drop: Number(e.target.value) })
                }
              />
            </label>
            <p className="field-note">动作超过 0.4 s 未更新会制动。</p>
          </>
        )}
      </details>
      {mode === "simulation" && (
        <details>
          <summary>车辆、相机与场景 JSON</summary>
          <textarea
            aria-label="场景 JSON"
            className="scene-editor"
            value={sceneText}
            disabled={active}
            onChange={(e) => updateSettings({ sceneText: e.target.value })}
            rows={12}
          />
          <button
            disabled={active || busy}
            onClick={() =>
              attempt(async () => {
                const parsed = JSON.parse(sceneText) as Scene;
                const data = await post<Preview>("/preview", parsed);
                updateSettings({ customScene: parsed });
                updateSettings({ preview: data });
                clearView();
                updateSettings({ hint: parsed.task_hint });
              })
            }
          >
            校验并应用
          </button>
          <small className="field-note">
            几何、初始位姿、车体、相机、外观均可配置。核心场景须通过合法性检查。
          </small>
        </details>
      )}
    </div>
  );
}
