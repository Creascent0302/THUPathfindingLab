import { useEffect, useState } from "react";
import {
  api,
  post,
  fmt,
  reasonLabel,
  stateLabel,
  terminal,
  type Algorithm,
  type Benchmark,
  type Capability,
  type Manifest,
  type Scene,
  type Score,
} from "./types";
import "./evaluation.css";

const componentNames: Record<string, string> = {
  tracking: "跟踪精度",
  efficiency: "行驶效率",
  smoothness: "转向平滑",
  safety: "安全表现",
  realtime: "实时计算",
};
const percent = (value: number | null | undefined) =>
  value == null ? "—" : `${(value * 100).toFixed(1)}%`;

export function ScoreDetails({ score }: { score: Score | null | undefined }) {
  if (!score) return <span className="eval-muted">无真值或旧记录，未评分</span>;
  return (
    <details className="eval-score-detail">
      <summary>
        <strong>{score.total.toFixed(1)}</strong>
        <span> / 100</span>
      </summary>
      <div className="eval-score-breakdown">
        <p>{score.rule}</p>
        {Object.entries(score.components).map(([key, part]) => (
          <div key={key}>
            <span>
              {componentNames[key] || key} · 权重 {part.weight}%
            </span>
            <b>{fmt(part.value, 1)}</b>
          </div>
        ))}
        <small>评分版本 {score.version} · 缺失分项不虚构数值</small>
      </div>
    </details>
  );
}

export function BenchmarkPanel({
  algorithms,
  families,
  onReplay,
}: {
  algorithms: Algorithm[];
  families: Record<string, string>;
  onReplay: (run: Manifest) => void;
}) {
  const [methods, setMethods] = useState<string[]>([
    "temporal_pursuit",
    "temporal_mpc",
  ]);
  const [selectedFamilies, setFamilies] = useState<string[]>([
    "straight",
    "bend",
    "s_curve",
  ]);
  const [mapIds, setMapIds] = useState<string[]>([]);
  const [maps, setMaps] = useState<{ id: string; scene: Scene }[]>([]);
  const [execution, setExecution] = useState<Capability>("action");
  const [name, setName] = useState("多方法对比");
  const [seeds, setSeeds] = useState("101, 102, 103");
  const [steps, setSteps] = useState(4000);
  const [timeout, setTimeoutValue] = useState(1);
  const [parameters, setParameters] = useState("{}");
  const [history, setHistory] = useState<Benchmark[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [batch, setBatch] = useState<Benchmark | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [itemFilter, setItemFilter] = useState("all");
  const offered = algorithms.filter(
    (a) => a.id !== "manual" && a.capabilities.includes(execution),
  );
  const usableMethods = methods.filter((id) =>
    offered.some((a) => a.id === id && a.available !== false),
  );
  const seedValues = seeds.trim()
    ? seeds
        .trim()
        .split(/[,，\s]+/)
        .map(Number)
    : [];
  const taskCount =
    usableMethods.length *
    (selectedFamilies.length + mapIds.length) *
    seedValues.length;

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const refresh = async () => {
      try {
        const [batches, saved] = await Promise.all([
          api<Benchmark[]>("/benchmarks"),
          api<{ id: string; scene: Scene }[]>("/maps"),
        ]);
        if (cancelled) return;
        setHistory(batches);
        setMaps(saved);
        const id = selectedId || batches[0]?.id;
        if (id) {
          const detail = await api<Benchmark>(`/benchmarks/${id}`);
          if (!cancelled) {
            setBatch(detail);
            if (!selectedId) setSelectedId(id);
          }
        } else setBatch(null);
      } catch (e) {
        if (!cancelled) setError(String(e));
      } finally {
        if (!cancelled) timer = window.setTimeout(refresh, 1500);
      }
    };
    void refresh();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [selectedId]);

  const act = async (fn: () => Promise<void>) => {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };
  const toggle = (values: string[], id: string) =>
    values.includes(id)
      ? values.filter((value) => value !== id)
      : [...values, id];
  const start = () =>
    act(async () => {
      if (
        !seedValues.length ||
        seedValues.some(
          (seed) => !Number.isInteger(seed) || seed < 0 || seed > 4294967295,
        ) ||
        new Set(seedValues).size !== seedValues.length
      )
        throw new Error("种子应为互不重复的非负整数，用逗号分隔");
      const settings = JSON.parse(parameters);
      if (
        settings == null ||
        typeof settings !== "object" ||
        Array.isArray(settings)
      )
        throw new Error("算法参数须为以算法 ID 为键的 JSON 对象");
      const created = await post<Benchmark>("/benchmarks", {
        name,
        algorithms: usableMethods.map((algorithm) => ({
          algorithm,
          execution,
          parameters: settings[algorithm] || {},
        })),
        families: selectedFamilies,
        map_ids: mapIds,
        seeds: seedValues,
        max_steps: steps,
        timeout_s: timeout,
      });
      setBatch(created);
      setSelectedId(created.id);
      setHistory(await api<Benchmark[]>("/benchmarks"));
    });
  const visibleItems =
    batch?.items.filter(
      (item) =>
        itemFilter === "all" ||
        (itemFilter === "unsuccessful"
          ? terminal(item.state) && !item.metrics?.success
          : item.method_id === itemFilter),
    ) || [];

  return (
    <div className="eval-page">
      {error && (
        <div className="error-banner" role="alert">
          {error}
          <button aria-label="关闭评测错误" onClick={() => setError("")}>
            ×
          </button>
        </div>
      )}
      <section className="panel eval-create">
        <div className="panel-title">
          <h2>创建批量评测</h2>
          <span>同一组地图与种子 · 独立算法进程 · 串行执行</span>
        </div>
        <div className="eval-plan-grid">
          <div>
            <label className="eval-field">
              批次名称
              <input
                value={name}
                maxLength={80}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label className="eval-field">
              执行模式
              <select
                value={execution}
                onChange={(e) => setExecution(e.target.value as Capability)}
              >
                <option value="action">直接动作 action</option>
                <option value="path">平台跟踪局部路径 path</option>
              </select>
            </label>
            <fieldset className="eval-choices">
              <legend>对比方法</legend>
              {offered.map((algorithm) => (
                <label
                  key={algorithm.id}
                  title={algorithm.unavailable_reason || algorithm.description}
                >
                  <input
                    type="checkbox"
                    checked={methods.includes(algorithm.id)}
                    disabled={algorithm.available === false}
                    onChange={() => setMethods(toggle(methods, algorithm.id))}
                  />
                  <span>
                    {algorithm.name}
                    <small>
                      v{algorithm.version}
                      {algorithm.available === false ? " · 不可用" : ""}
                    </small>
                  </span>
                </label>
              ))}
            </fieldset>
          </div>
          <div>
            <fieldset className="eval-choices">
              <legend>内置地图</legend>
              {Object.entries(families).map(([id, title]) => (
                <label key={id}>
                  <input
                    type="checkbox"
                    checked={selectedFamilies.includes(id)}
                    onChange={() => setFamilies(toggle(selectedFamilies, id))}
                  />
                  {title}
                </label>
              ))}
            </fieldset>
            <fieldset className="eval-choices">
              <legend>已保存自定义地图</legend>
              {maps.length ? (
                maps.map((map) => (
                  <label key={map.id}>
                    <input
                      type="checkbox"
                      checked={mapIds.includes(map.id)}
                      onChange={() => setMapIds(toggle(mapIds, map.id))}
                    />
                    {map.scene.name}
                  </label>
                ))
              ) : (
                <p className="field-note">
                  在「自定义地图」保存场景后即可加入评测。
                </p>
              )}
            </fieldset>
          </div>
          <div>
            <label className="eval-field">
              测试种子
              <input
                value={seeds}
                onChange={(e) => setSeeds(e.target.value)}
                placeholder="101, 102, 103"
              />
            </label>
            <p className="field-note">
              每张地图使用同一组种子。自定义地图保留几何与物件设置，种子控制外观随机性。
            </p>
            <div className="eval-field-pair">
              <label className="eval-field">
                单次最大帧数
                <input
                  type="number"
                  min={1}
                  max={6000}
                  value={steps}
                  onChange={(e) => setSteps(Number(e.target.value))}
                />
              </label>
              <label className="eval-field">
                推理超时 / s
                <input
                  type="number"
                  min={0.05}
                  max={10}
                  step={0.05}
                  value={timeout}
                  onChange={(e) => setTimeoutValue(Number(e.target.value))}
                />
              </label>
            </div>
            <details className="eval-advanced">
              <summary>各方法参数（可选）</summary>
              <p className="field-note">
                按算法 ID 设置参数，如 {`{"temporal_mpc":{"speed_mps":0.7}}`}
                。默认使用已注册算法设置。
              </p>
              <textarea
                aria-label="批量算法参数"
                value={parameters}
                onChange={(e) => setParameters(e.target.value)}
                rows={5}
                spellCheck={false}
              />
            </details>
            <div className="eval-start">
              <strong>
                {taskCount} <small>次独立运行 / 最多 128 次</small>
              </strong>
              <button
                className="primary"
                disabled={
                  busy || taskCount < 1 || taskCount > 128 || !name.trim()
                }
                onClick={start}
              >
                启动批量评测
              </button>
            </div>
            <p className="field-note">
              关闭页面后继续执行。最多排队 3 批，运行记录共用 200 条配额。
            </p>
          </div>
        </div>
      </section>

      <section className="panel eval-monitor">
        <div className="panel-title">
          <h2>批次与进度</h2>
          <span>配置在启动时冻结并保存</span>
        </div>
        <div className="eval-batch-toolbar">
          <select
            aria-label="评测批次"
            value={selectedId || ""}
            onChange={(e) => {
              setSelectedId(e.target.value);
              setBatch(null);
            }}
          >
            <option value="" disabled>
              选择批次
            </option>
            {history.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.name} · {stateLabel[entry.state]} ·{" "}
                {new Date(entry.created_at).toLocaleString()}
              </option>
            ))}
          </select>
          {batch && (
            <div className="buttons">
              <button
                disabled={busy || terminal(batch.state)}
                onClick={() =>
                  act(async () =>
                    setBatch(
                      await post<Benchmark>(
                        `/benchmarks/${batch.id}/cancel`,
                        {},
                      ),
                    ),
                  )
                }
              >
                取消批次
              </button>
              <a
                className="inline-link"
                href={`/api/benchmarks/${batch.id}/export?format=json`}
                download
              >
                ↓ JSON
              </a>
              <a
                className="inline-link"
                href={`/api/benchmarks/${batch.id}/export?format=csv`}
                download
              >
                ↓ CSV
              </a>
              <button
                className="danger-button"
                disabled={
                  busy ||
                  !terminal(batch.state) ||
                  batch.items.some((item) => item.state === "running")
                }
                onClick={() => {
                  if (window.confirm("删除此批次汇总？单次运行记录仍保留。"))
                    void act(async () => {
                      await api(`/benchmarks/${batch.id}`, {
                        method: "DELETE",
                      });
                      setSelectedId(null);
                      setBatch(null);
                      setHistory(await api<Benchmark[]>("/benchmarks"));
                    });
                }}
              >
                删除汇总
              </button>
            </div>
          )}
        </div>
        {batch ? (
          <>
            <div className="eval-progress">
              <progress
                max={batch.summary.total}
                value={batch.summary.finished}
              />
              <strong>
                {batch.summary.finished} / {batch.summary.total}
              </strong>
              <span>
                {stateLabel[batch.state]}
                {batch.active_frame != null
                  ? ` · 当前运行 ${batch.active_frame} 帧`
                  : ""}
              </span>
            </div>
            <div className="eval-meta">
              <span>
                测试集 <code>{batch.test_set_sha256.slice(0, 16)}</code>
              </span>
              <span>评分 v{batch.score_version}</span>
              <span>{batch.summary.comparison_note}</span>
            </div>
            {batch.reason && <p className="notice">{batch.reason}</p>}
          </>
        ) : (
          <div className="empty">创建批次后，在这里查看进度与对比结果。</div>
        )}
      </section>

      {batch && (
        <>
          <section className="panel table-wrap">
            <div className="panel-title">
              <h2>方法对比</h2>
              <span>
                {batch.summary.comparable
                  ? "优先比较成功率，其次比较平均分"
                  : "等待完整配对；当前数值为过程观察"}
              </span>
            </div>
            <table className="eval-comparison">
              <thead>
                <tr>
                  <th>方法</th>
                  <th>覆盖 / 成功</th>
                  <th>成功率</th>
                  <th>平均分</th>
                  <th>完成度</th>
                  <th>误差均值 / P95</th>
                  <th>完成时间</th>
                  <th>碰撞 / 换线</th>
                  <th>推理 P95</th>
                  <th>执行失败</th>
                </tr>
              </thead>
              <tbody>
                {batch.summary.methods.map((method, index) => (
                  <tr key={method.method_id}>
                    <td>
                      <strong>
                        {batch.summary.comparable && (
                          <span className="eval-rank">{index + 1}</span>
                        )}
                        {method.name}
                      </strong>
                      <small>{method.execution}</small>
                    </td>
                    <td>
                      {method.finished} / {method.planned}
                      <small>成功 {method.successes} 次</small>
                    </td>
                    <td>{percent(method.success_rate)}</td>
                    <td>
                      <b className="eval-score">{fmt(method.score, 1)}</b>
                      {method.score == null && (
                        <small>
                          已完成均分 {fmt(method.observed_score, 1)}
                        </small>
                      )}
                    </td>
                    <td>{percent(method.completion)}</td>
                    <td>
                      {fmt(method.tracking_error_m, 3)} /{" "}
                      {fmt(method.tracking_p95_m, 3)}
                      <small>m · 有跟踪数据的运行</small>
                    </td>
                    <td>
                      {fmt(method.completion_time_s, 1)} s
                      <small>仅成功运行</small>
                    </td>
                    <td>
                      {method.collisions} / {method.illegal_switches}
                    </td>
                    <td>
                      {fmt(method.inference_p95_ms, 1)} ms
                      <small>各次 P95 的均值</small>
                    </td>
                    <td>
                      {method.execution_failures}
                      <small>总测量 {method.measured_runs} 次</small>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="field-note eval-table-note">
              执行失败保留并计零分；取消或未跑完的批次不排名。不同测试集、车辆、物理或渲染版本应分别比较。推理时间包含
              Worker 通信，受机器负载影响。
            </p>
          </section>
          <section className="panel table-wrap">
            <div className="panel-title">
              <h2>逐项结果</h2>
              <select
                aria-label="筛选评测结果"
                value={itemFilter}
                onChange={(e) => setItemFilter(e.target.value)}
              >
                <option value="all">全部作业</option>
                <option value="unsuccessful">未成功的作业</option>
                {batch.methods.map((method) => (
                  <option key={method.id} value={method.id}>
                    {method.name}
                  </option>
                ))}
              </select>
            </div>
            <table>
              <thead>
                <tr>
                  <th>方法</th>
                  <th>地图 / 种子</th>
                  <th>状态与原因</th>
                  <th>评分</th>
                  <th>完成度</th>
                  <th>记录</th>
                </tr>
              </thead>
              <tbody>
                {visibleItems.map((item) => {
                  const method = batch.methods.find(
                    (value) => value.id === item.method_id,
                  )!;
                  const scene = batch.cases.find(
                    (value) => value.id === item.case_id,
                  )!;
                  return (
                    <tr key={`${item.case_id}:${item.method_id}`}>
                      <td>{method.name}</td>
                      <td>
                        {scene.name}
                        <small>seed {scene.seed}</small>
                      </td>
                      <td>
                        {stateLabel[item.state]}
                        <small>
                          {item.error ||
                            reasonLabel[item.metrics?.reason || ""] ||
                            item.metrics?.reason ||
                            "等待执行"}
                        </small>
                      </td>
                      <td>
                        <ScoreDetails score={item.metrics?.score} />
                      </td>
                      <td>{percent(item.metrics?.completion)}</td>
                      <td>
                        {item.run_id ? (
                          <>
                            <button
                              disabled={!item.metrics?.frames}
                              onClick={() =>
                                onReplay({
                                  episode_id: item.run_id!,
                                } as Manifest)
                              }
                            >
                              回放
                            </button>
                            <a
                              className="inline-link"
                              href={`/api/results/${item.run_id}/export/json`}
                            >
                              JSON
                            </a>
                            <small>#{item.run_id.slice(0, 8)}</small>
                          </>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>
        </>
      )}
      <details className="panel eval-rubric">
        <summary>评分含义与边界</summary>
        <p>
          成功运行得 60–100 分；失败运行最高 49 分，静止且没有进度得 0
          分。总分用于课程内对比，核心成功判据保持独立。
        </p>
        <p>
          质量由跟踪误差（35%）、单位时间有效前进效率（20%）、实际转向平滑度（15%）、安全表现（20%）、实时计算（10%）加权组成。碰撞或非法换线使安全分归零。展开单次得分可查看各分项。
        </p>
        <p>
          误差只统计有效跟踪阶段；完成时间只统计成功案例；提前失败可能只有很少有效误差样本，应同时查看成功率与覆盖数。相同批次内使用同一组完整场景、车辆与随机种子。自定义物件碰撞按车体与障碍物平面轮廓判断，终止后的惯性制动也会检测碰撞。
        </p>
      </details>
    </div>
  );
}
