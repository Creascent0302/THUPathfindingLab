import { useEffect, useState } from "react";
import { CameraPanel, Charts, MapPanel } from "./Panels";
import { useLiveStream, useManualDrive } from "./useRunControls";
import { ResultsPage } from "./Pages";
import { BenchmarkPanel } from "./BenchmarkPanel";
import { MapEditor } from "./MapEditor";
import { SubmissionPanel } from "./SubmissionPanel";
import {
  SetupPanel,
  initialSetup,
  restoreSetup,
  storedSetup,
  type Setup,
} from "./SetupPanel";
import { usePersistentState } from "./usePersistentState";
import "./evaluation-status.css";
import {
  api,
  fmt,
  post,
  reasonLabel,
  stateLabel,
  terminal,
  type Algorithm,
  type Config,
  type Evaluation,
  type Manifest,
  type Mode,
  type Preview,
  type Snapshot,
  type SavedMap,
} from "./types";

const emptyPreview: Preview = { image: null, scene: null, calibration: null };
type Tab = "lab" | "results" | "benchmarks" | "editor" | "submissions";

function RouteAssessment({
  evaluation,
  hasTruth,
}: {
  evaluation: Evaluation | null;
  hasTruth: boolean;
}) {
  const acquired = evaluation?.phase === "tracking";
  const wrongBranch = evaluation?.route_identity === "wrong_branch";
  const reason = evaluation?.reason;
  const identity = evaluation?.route_identity;
  const tone =
    reason && reason !== "success"
      ? "failed"
      : evaluation && (!acquired || identity === "unconfirmed" || wrongBranch)
        ? "pending"
        : evaluation
          ? "confirmed"
          : "idle";
  const title = reason
    ? reasonLabel[reason] || reason
    : !evaluation
      ? hasTruth
        ? "等待首帧评测"
        : "无路径真值评测"
      : !acquired
        ? "尚未合法接入起点"
        : wrongBranch
          ? "已接入 · 疑似跟随错误道路"
          : identity === "avoiding"
            ? "已接入 · 障碍物附近合法绕行"
            : identity === "unconfirmed"
              ? "已接入 · 当前偏离有序参考段"
              : identity === "confirmed"
                ? "已合法接入 · 有序跟踪"
                : "已接入（记录当时判定）";
  const alternative = wrongBranch ? evaluation?.other_route : null;
  return (
    <section className={`route-assessment ${tone}`} aria-label="当前帧路径评测">
      <div className="route-assessment-heading">
        <span>当前帧路径评测</span>
        <strong>{title}</strong>
        <small>算法自报 TRACK 不等于合法沿线行驶。</small>
      </div>
      {evaluation && (
        <div className="route-assessment-evidence">
          <span>
            有序参考距离 <b>{fmt(evaluation.lateral_error_m)} m</b>
          </span>
          <span>
            有效弧长 <b>{fmt(evaluation.progress_m)} m</b>
          </span>
          {evaluation.reference_window_m && (
            <span>
              当前参考段{" "}
              <b>
                {evaluation.reference_window_m.map((arc) => fmt(arc)).join("–")}{" "}
                m
              </b>
            </span>
          )}
          {!acquired && evaluation.entry_distance_m != null && (
            <span>
              距起点 <b>{fmt(evaluation.entry_distance_m)} m</b>
            </span>
          )}
          {alternative && (
            <span className="route-alternative">
              邻近
              {alternative.kind === "target_nonlocal"
                ? `目标路线其他段（弧长 ${fmt(alternative.arc_m)} m）`
                : `干扰线 ${(alternative.index ?? 0) + 1}`}
              ：距离 {fmt(alternative.distance_m)} m，错线证据持续{" "}
              {fmt(evaluation.wrong_route_duration_s)} s
            </span>
          )}
          {identity === undefined && (
            <span>该历史帧未保存道路身份明细，按原始评测显示。</span>
          )}
        </div>
      )}
    </section>
  );
}

export default function App() {
  const [catalog, setCatalog] = useState<{
    algorithms: Algorithm[];
    families: Record<string, string>;
  }>({ algorithms: [], families: {} });
  const [tab, setTab, tabStorageError] = usePersistentState<Tab>(
    "pathlab.tab.v1",
    () => "lab",
    (value) => {
      if (
        typeof value !== "string" ||
        !["lab", "results", "benchmarks", "editor", "submissions"].includes(
          value,
        )
      )
        throw new Error("Invalid tab");
      return value as Tab;
    },
  );
  const [settings, setSettings, setupStorageError] = usePersistentState<Setup>(
    "pathlab.setup.v1",
    () => initialSetup,
    restoreSetup,
    storedSetup,
  );
  const updateSettings = (patch: Partial<Setup>) =>
    setSettings((state) => ({
      ...state,
      ...patch,
      ...(patch.savedMapId === undefined &&
      (patch.customScene !== undefined || patch.family !== undefined)
        ? { savedMapId: null }
        : {}),
    }));
  const [savedMaps, setSavedMaps] = useState<SavedMap[]>([]);
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
    preview,
    customScene,
    maxSteps,
    timeout,
    recordImages,
    stress,
    delay,
    drop,
  } = settings;
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [liveId, setLiveId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<Manifest[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [replayId, setReplayId] = useState<string | null>(null);
  const [replayFrame, setReplayFrame] = useState(0);
  const [replayCount, setReplayCount] = useState(0);
  const [playing, setPlaying] = useState(false);
  const scene = snapshot ? snapshot.scene : preview.scene;
  const displayAlgorithm = snapshot?.config.algorithm ?? algorithm;
  const active = !!liveId && !terminal(snapshot?.state);
  const frame = snapshot?.frame || null;
  const algorithmStatus =
    frame?.output?.status ??
    (frame
      ? frame.interventions.includes("safety_braking")
        ? "安全制动"
        : "无新算法输出"
      : "UNINITIALIZED");
  const currentHint = snapshot
    ? snapshot.config.task_hint
    : hint || preview.scene?.task_hint || null;
  const speedLimit = scene?.vehicle.max_speed_mps || 1.5;
  const steerLimit = scene?.vehicle.max_steering_rad || 0.52;

  const connected = useLiveStream(liveId, setSnapshot);
  const [action, setAction] = useManualDrive(
    liveId,
    active,
    snapshot?.config.algorithm,
    tab,
    speedLimit,
    steerLimit,
  );

  const attempt = async (operation: () => Promise<unknown>) => {
    setError("");
    setBusy(true);
    try {
      await operation();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    api<typeof catalog>("/catalog")
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const refresh = () =>
      api<SavedMap[]>("/maps", { signal: controller.signal })
        .then((maps) => {
          setSavedMaps(maps);
          setSettings((current) =>
            current.savedMapId &&
            !maps.some((map) => map.id === current.savedMapId)
              ? { ...current, savedMapId: null }
              : current,
          );
        })
        .catch((e) => {
          if (e.name !== "AbortError") setError(String(e));
        });
    void refresh();
    window.addEventListener("focus", refresh);
    return () => {
      controller.abort();
      window.removeEventListener("focus", refresh);
    };
  }, [tab]);
  useEffect(() => {
    if (mode !== "simulation" || family === "custom") return;
    const controller = new AbortController();
    const timer = window.setTimeout(
      () =>
        api<Preview>(`/scenes/${family}?seed=${seed}`, {
          signal: controller.signal,
        })
          .then((data) => {
            updateSettings({ preview: data });
            updateSettings({ customScene: null });
            updateSettings({ sceneText: JSON.stringify(data.scene, null, 2) });
            updateSettings({ hint: null });
          })
          .catch((e) => {
            if (e.name !== "AbortError") setError(String(e));
          }),
      250,
    );
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [family, seed, mode]);
  useEffect(() => {
    const controller = new AbortController();
    const request =
      mode === "simulation"
        ? family === "custom" && customScene
          ? api<Preview>("/preview", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(customScene),
              signal: controller.signal,
            })
          : null
        : source
          ? api<Preview>(`/sources/${source.id}/preview`, {
              signal: controller.signal,
            })
          : null;
    request
      ?.then((data) => updateSettings({ preview: data }))
      .catch((e) => {
        if (e.name !== "AbortError") setError(String(e));
      });
    return () => controller.abort();
  }, [mode, family, customScene, source]);
  useEffect(() => {
    if (tab === "results")
      api<Manifest[]>("/results")
        .then(setResults)
        .catch((e) => setError(String(e)));
  }, [tab]);
  useEffect(() => {
    if (!replayId) return;
    const controller = new AbortController();
    api<Snapshot>(`/results/${replayId}/frames/${replayFrame}`, {
      signal: controller.signal,
    })
      .then(setSnapshot)
      .catch((e) => {
        if (e.name !== "AbortError") setError(String(e));
      });
    return () => controller.abort();
  }, [replayId, replayFrame]);
  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(
      () =>
        setReplayFrame((i) => {
          if (i >= replayCount - 1) {
            setPlaying(false);
            return i;
          }
          return i + 1;
        }),
      200,
    );
    return () => clearInterval(timer);
  }, [playing, replayCount]);

  const clearView = () => {
    setSnapshot(null);
    setLiveId(null);
    setReplayId(null);
    setPlaying(false);
  };
  const changeMode = (value: Mode) => {
    updateSettings({ mode: value });
    setSnapshot(null);
    setLiveId(null);
    setReplayId(null);
    updateSettings({ preview: emptyPreview });
    updateSettings({ hint: null });
    const id = value === "simulation" ? "manual" : "image_probe";
    updateSettings({ algorithm: id });
    updateSettings({
      execution: value === "simulation" ? "action" : "perception",
    });
  };
  const stopCurrent = async () => {
    if (liveId && active)
      await post(`/runs/${liveId}/control`, { command: "stop" });
    setLiveId(null);
    setAction({ steering_angle_rad: 0, speed_mps: 0 });
  };
  const create = async (resume: boolean) => {
    const parsed = JSON.parse(parameters);
    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object")
      throw new Error("算法参数必须是 JSON 对象");
    if (mode !== "simulation" && !source)
      throw new Error("请先上传图片、视频或图像序列");
    await stopCurrent();
    setReplayId(null);
    setPlaying(false);
    const config: Config = {
      mode,
      family,
      seed,
      algorithm,
      execution,
      source_id: source?.id || null,
      parameters: parsed,
      task_hint: hint,
      scene: customScene,
      max_steps: maxSteps,
      timeout_s: timeout,
      record_images: recordImages,
      realtime: true,
      stress: {
        mode: stress ? "stress" : "deterministic",
        delay_frames: delay,
        drop_probability: drop,
        action_ttl_s: 0.4,
      },
    };
    const data = await post<Snapshot>("/runs", config);
    setSnapshot(data);
    setLiveId(data.id);
    updateSettings({ hintMode: null });
    if (resume) await post(`/runs/${data.id}/control`, { command: "resume" });
    return data.id;
  };
  const control = (command: string) =>
    attempt(async () => {
      if (liveId) await post(`/runs/${liveId}/control`, { command });
    });
  const openReplay = (manifest: Manifest) =>
    attempt(async () => {
      await stopCurrent();
      const data = await api<{ frames: unknown[] }>(
        `/results/${manifest.episode_id}`,
      );
      if (!data.frames.length)
        throw new Error("该运行没有已保存帧，请查看失败原因");
      setReplayId(manifest.episode_id);
      setReplayCount(data.frames.length);
      setReplayFrame(0);
      setTab("lab");
      setPlaying(false);
    });

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-symbol">↝</div>
          <div>
            寻迹实验室<small>PATHFINDING LAB</small>
          </div>
        </div>
        <p className="course">
          智能交通创新实践 <span>课程实验平台</span>
        </p>
        <nav>
          {(
            [
              ["lab", "01", "实验工作台"],
              ["results", "02", "运行记录与对比"],
              ["benchmarks", "03", "批量评测"],
              ["editor", "04", "自定义地图"],
              ["submissions", "05", "算法提交"],
            ] as const
          ).map(([key, n, title]) => (
            <button
              key={key}
              aria-label={title}
              disabled={active && (key === "editor" || key === "submissions")}
              title={
                active && (key === "editor" || key === "submissions")
                  ? "请先停止当前实验"
                  : undefined
              }
              className={tab === key ? "selected" : ""}
              onClick={() => {
                setTab(key);
                if (active && key !== "lab") {
                  void control("pause");
                  setAction({ steering_angle_rad: 0, speed_mps: 0 });
                }
              }}
            >
              <span>{n}</span>
              {title}
            </button>
          ))}
        </nav>
        {tab === "lab" && (
          <SetupPanel
            savedMaps={savedMaps}
            selectScene={(selection) => {
              if (!selection.startsWith("map:")) {
                clearView();
                updateSettings({
                  family: selection,
                  customScene: null,
                  preview: emptyPreview,
                  hint: null,
                });
                return;
              }
              const map = savedMaps.find(
                (item) => item.id === selection.slice(4),
              );
              if (!map) return;
              void attempt(async () => {
                const data = await post<Preview>("/preview", map.scene);
                clearView();
                updateSettings({
                  family: "custom",
                  savedMapId: map.id,
                  customScene: data.scene,
                  preview: data,
                  sceneText: JSON.stringify(data.scene, null, 2),
                  seed: map.scene.seed,
                  hint: null,
                });
              });
            }}
            settings={settings}
            updateSettings={updateSettings}
            catalog={catalog}
            active={active}
            busy={busy}
            attempt={attempt}
            changeMode={changeMode}
            clearView={clearView}
          />
        )}
        <div className="sidebar-bottom">
          <span className="status-dot" />
          本地 CPU 实验环境<small>协议 v1.0 · 平台 v0.1</small>
        </div>
      </aside>

      <main>
        <header>
          <div className="eyebrow">
            INTELLIGENT TRANSPORTATION / EXPERIMENT 01
          </div>
          <div className="page-title">
            <div>
              <h1>
                {tab === "lab"
                  ? "视觉寻迹实验工作台"
                  : tab === "results"
                    ? "每一次运行，都有记录"
                    : tab === "benchmarks"
                      ? "同一组测试，比较不同方法"
                      : tab === "editor"
                        ? "绘制你的实验路线"
                        : "提交代码，开始实验"}
              </h1>
              <p>
                {tab === "lab"
                  ? "观察图像，控制车辆，验证完整的运动反馈链路。"
                  : tab === "results"
                    ? "保存原始输出、执行动作与失败原因，使用相同条件比较实验。"
                    : tab === "benchmarks"
                      ? "冻结实验条件、批量执行，用成功率与可解释评分评估算法。"
                      : tab === "editor"
                        ? "调整路线、车辆与材质，生成满足转弯约束的实验地图。"
                        : "上传算法压缩包，平台自动完成解压与登记。"}
              </p>
            </div>
            <span className="version-badge">视觉寻迹 · 仿真与测评</span>
          </div>
        </header>
        {(setupStorageError || tabStorageError) && (
          <div className="error-banner" role="alert">
            {setupStorageError || tabStorageError}
          </div>
        )}
        {error && (
          <div className="error-banner" role="alert">
            <strong>操作未完成</strong> {error}
            <button aria-label="关闭错误" onClick={() => setError("")}>
              ×
            </button>
          </div>
        )}

        {tab === "lab" && (
          <>
            <div className="toolbar">
              <div className="buttons">
                <button
                  className="primary"
                  disabled={busy}
                  onClick={() =>
                    active
                      ? control(snapshot?.paused ? "resume" : "pause")
                      : attempt(() => create(true))
                  }
                >
                  {active
                    ? snapshot?.paused
                      ? "▶ 继续运行"
                      : "Ⅱ 暂停"
                    : "▶ 启动实验"}
                </button>
                <button
                  disabled={
                    busy ||
                    (!!snapshot && terminal(snapshot.state) && !replayId)
                  }
                  onClick={() =>
                    replayId
                      ? setReplayFrame((i) => Math.min(replayCount - 1, i + 1))
                      : active
                        ? control("step")
                        : attempt(async () => {
                            const id = await create(false);
                            if (id)
                              await post(`/runs/${id}/control`, {
                                command: "step",
                              });
                          })
                  }
                >
                  单步
                </button>
                <button
                  disabled={!active || busy}
                  onClick={() => control("stop")}
                >
                  停止
                </button>
                <button
                  disabled={busy}
                  onClick={() => attempt(() => create(false))}
                >
                  重置
                </button>
              </div>
              <div className="run-status">
                <i className={"dot " + (connected ? "teal" : "gray")} />
                {replayId
                  ? "结果回放"
                  : snapshot
                    ? snapshot.paused && !terminal(snapshot.state)
                      ? "已暂停"
                      : stateLabel[snapshot.state]
                    : "准备就绪"}
                <code>
                  {snapshot
                    ? "#" + snapshot.id.slice(0, 8)
                    : `固定步长 ${scene?.dt_s ?? 0.05} s`}
                </code>
              </div>
            </div>
            {(snapshot?.config.mode ?? mode) !== "simulation" && (
              <div className="notice">
                录制素材用于感知和时序分析。算法输出不会改变后续画面，不能据此证明闭环行驶成功。
              </div>
            )}
            {snapshot?.reason && (
              <div
                className={
                  "notice " + (snapshot.state === "failed" ? "danger" : "")
                }
              >
                {replayId ? "该次运行最终结果" : "本次结果"}：
                {reasonLabel[snapshot.reason] || snapshot.reason}。
                {snapshot.metrics?.success === false &&
                  "未达到完整寻迹成功条件。"}
              </div>
            )}
            <div className="metrics-strip">
              {[
                ["算法自报状态", algorithmStatus, ""],
                ["置信度", fmt(frame?.output?.confidence), ""],
                ["实际速度", fmt(frame?.applied?.actual.speed_mps), "m/s"],
                [
                  "实际转角",
                  fmt(frame?.applied?.actual.steering_angle_rad),
                  "rad",
                ],
                ["推理耗时", fmt(frame?.inference_ms, 1), "ms"],
                [
                  "有效进度",
                  frame?.evaluation
                    ? (frame.evaluation.completion * 100).toFixed(1)
                    : "不提供",
                  "%",
                ],
              ].map(([label, value, unit]) => (
                <div
                  key={label}
                  title={
                    label === "算法自报状态" && frame && !frame.output
                      ? "本帧没有新的算法输出，显示平台执行阶段。"
                      : undefined
                  }
                >
                  <span>{label}</span>
                  <strong>
                    {value}
                    <small>{value === "不提供" ? "" : unit}</small>
                  </strong>
                </div>
              ))}
            </div>
            <RouteAssessment
              evaluation={frame?.evaluation ?? null}
              hasTruth={(snapshot?.config.mode ?? mode) === "simulation"}
            />
            <div className="camera-grid">
              <CameraPanel
                image={snapshot?.image || preview.image}
                frame={frame}
                calibration={
                  snapshot ? snapshot.calibration : preview.calibration
                }
                hint={currentHint}
                hintMode={!active && !replayId ? hintMode : null}
                onHint={(value) => {
                  updateSettings({ hint: value });
                  updateSettings({ hintMode: null });
                }}
              />
              <CameraPanel
                image={snapshot?.image || preview.image}
                frame={frame}
                calibration={
                  snapshot ? snapshot.calibration : preview.calibration
                }
                overlay
                hint={currentHint}
              />
            </div>
            <div className="lower-grid">
              <MapPanel
                scene={scene}
                frame={frame}
                history={snapshot?.history || []}
              />
              <section className="panel controls-panel">
                <div className="panel-title">
                  <h2>
                    {displayAlgorithm === "manual"
                      ? "手动驾驶"
                      : "算法输出与诊断"}
                  </h2>
                  <span>
                    {displayAlgorithm === "manual"
                      ? "正转角向左 · 不允许倒车"
                      : "缺失信息显示「不提供」"}
                  </span>
                </div>
                {displayAlgorithm === "manual" && !replayId ? (
                  <div className="drive-controls">
                    <div className="key-hint">
                      <kbd>↑</kbd>
                      <kbd>↓</kbd> 加减速 <kbd>←</kbd>
                      <kbd>→</kbd> 转向 <kbd>空格</kbd> 制动
                    </div>
                    <label>
                      目标速度{" "}
                      <strong>{action.speed_mps.toFixed(2)} m/s</strong>
                      <input
                        aria-label="目标速度"
                        type="range"
                        min="0"
                        max={speedLimit}
                        step=".05"
                        value={action.speed_mps}
                        onChange={(e) =>
                          setAction((a) => ({
                            ...a,
                            speed_mps: Number(e.target.value),
                          }))
                        }
                      />
                    </label>
                    <label>
                      前轮转角{" "}
                      <strong>
                        {action.steering_angle_rad.toFixed(2)} rad
                      </strong>
                      <input
                        aria-label="前轮转角"
                        type="range"
                        min={-steerLimit}
                        max={steerLimit}
                        step=".01"
                        value={action.steering_angle_rad}
                        onChange={(e) =>
                          setAction((a) => ({
                            ...a,
                            steering_angle_rad: Number(e.target.value),
                          }))
                        }
                      />
                      <div className="range-labels">
                        <span>右转 −</span>
                        <span>回正 0</span>
                        <span>左转 +</span>
                      </div>
                    </label>
                    <div className="buttons">
                      <button
                        onClick={() =>
                          setAction((a) => ({ ...a, steering_angle_rad: 0 }))
                        }
                      >
                        转向回正
                      </button>
                      <button
                        className="brake"
                        onClick={() =>
                          setAction({ steering_angle_rad: 0, speed_mps: 0 })
                        }
                      >
                        制动停车
                      </button>
                    </div>
                    <p className="field-note">
                      先启动实验，再设置速度。窗口失焦立即请求停车；控制信号超过
                      0.6 s 未更新时自动制动。
                    </p>
                  </div>
                ) : (
                  <div className="diagnostics">
                    <p>
                      {frame?.output?.diagnostics.join("；") ||
                        "尚无算法诊断信息。"}
                    </p>
                    <pre>
                      {frame?.output
                        ? JSON.stringify(
                            {
                              action: frame.output.action,
                              debug: frame.output.debug,
                            },
                            null,
                            2,
                          )
                        : "不提供"}
                    </pre>
                  </div>
                )}
                <div className="interventions">
                  <span>本帧执行干预</span>
                  <code>{frame?.interventions.join(" · ") || "无"}</code>
                </div>
              </section>
            </div>
            <Charts history={snapshot?.history || []} />
            <section className="panel replay-panel">
              <div className="panel-title">
                <h2>回放与结果导出</h2>
                <span>
                  {replayId
                    ? "浏览已保存结果，不改变算法历史"
                    : "实验结束后可拖动查看任意已保存帧"}
                </span>
              </div>
              <div className="replay-controls">
                {replayId ? (
                  <>
                    <button onClick={() => setPlaying((v) => !v)}>
                      {playing ? "暂停回放" : "播放回放"}
                    </button>
                    <input
                      aria-label="回放帧"
                      type="range"
                      min="0"
                      max={Math.max(0, replayCount - 1)}
                      value={replayFrame}
                      onChange={(e) => {
                        setPlaying(false);
                        setReplayFrame(Number(e.target.value));
                      }}
                    />
                    <code>
                      {replayFrame + 1} / {replayCount}
                    </code>
                  </>
                ) : (
                  <button
                    disabled={
                      !snapshot ||
                      !terminal(snapshot.state) ||
                      snapshot.frame_count === 0
                    }
                    onClick={() =>
                      snapshot &&
                      openReplay({ episode_id: snapshot.id } as Manifest)
                    }
                  >
                    进入结果回放
                  </button>
                )}
                {snapshot && (
                  <div className="export-links">
                    <a
                      href={`/api/results/${snapshot.id}/export/json`}
                      download
                    >
                      ↓ JSON
                    </a>
                    <a href={`/api/results/${snapshot.id}/export/csv`} download>
                      ↓ CSV
                    </a>
                  </div>
                )}
              </div>
            </section>
            <details className="panel logs">
              <summary>
                运行日志与错误{" "}
                <span>{snapshot?.failures.length || 0} 个错误</span>
              </summary>
              <pre>
                {[
                  ...(snapshot?.logs || [
                    "场景已准备。创建实验后初始化独立算法进程。",
                  ]),
                  ...(snapshot?.failures.map(
                    (f) => `${f.kind}: ${f.message}`,
                  ) || []),
                ].join("\n")}
              </pre>
            </details>
          </>
        )}

        {tab === "benchmarks" && (
          <BenchmarkPanel
            algorithms={catalog.algorithms}
            families={catalog.families}
            onReplay={openReplay}
          />
        )}

        {tab === "results" && (
          <ResultsPage
            results={results}
            selected={selected}
            setSelected={setSelected}
            refresh={() =>
              attempt(async () => setResults(await api<Manifest[]>("/results")))
            }
            onReplay={openReplay}
            busy={busy}
            onDelete={(ids) => {
              if (
                !window.confirm(
                  `删除 ${ids.length} 条运行记录及其保存的图像？此操作不可恢复。`,
                )
              )
                return;
              void attempt(async () => {
                const deleted = new Set<string>();
                try {
                  for (const id of ids) {
                    await api(`/results/${id}`, { method: "DELETE" });
                    deleted.add(id);
                  }
                } finally {
                  setSelected((old) => old.filter((id) => !deleted.has(id)));
                  if (
                    (snapshot && deleted.has(snapshot.id)) ||
                    (replayId && deleted.has(replayId))
                  )
                    clearView();
                  setResults(await api<Manifest[]>("/results"));
                }
              });
            }}
          />
        )}

        {tab === "editor" &&
          (preview.scene ? (
            <MapEditor
              onMapsChange={setSavedMaps}
              base={customScene || preview.scene}
              busy={busy}
              attempt={attempt}
              onApply={(data) => {
                clearView();
                updateSettings({
                  preview: data,
                  customScene: data.scene,
                  sceneText: JSON.stringify(data.scene, null, 2),
                  family: "custom",
                  seed: data.scene?.seed ?? seed,
                  mode: "simulation",
                  hint: null,
                });
                setTab("lab");
              }}
            />
          ) : (
            <div className="panel empty">
              请先返回实验工作台，选择闭环仿真场景。
            </div>
          ))}
        {tab === "submissions" && (
          <SubmissionPanel
            algorithms={catalog.algorithms}
            busy={busy}
            attempt={attempt}
            refresh={async () =>
              setCatalog(await api<typeof catalog>("/catalog"))
            }
            onSelect={(plugin) => {
              clearView();
              updateSettings({
                algorithm: plugin.id,
                execution: plugin.capabilities[0],
                parameters: "{}",
              });
              setTab("lab");
            }}
          />
        )}
        <footer>
          智能交通创新实践 · 视觉寻迹实验平台
          <span>地图真值仅用于评分与可视化</span>
        </footer>
      </main>
    </div>
  );
}
