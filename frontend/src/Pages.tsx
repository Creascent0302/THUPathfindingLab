import { useEffect, useState, type Dispatch, type SetStateAction } from "react";
import {
  api,
  fmt,
  reasonLabel,
  stateLabel,
  terminal,
  type Manifest,
} from "./types";
import { ScoreDetails } from "./BenchmarkPanel";

export function ResultsPage({
  results,
  selected,
  setSelected,
  refresh,
  onReplay,
  onDelete,
  busy,
}: {
  results: Manifest[];
  selected: string[];
  setSelected: Dispatch<SetStateAction<string[]>>;
  refresh: () => void;
  onReplay: (run: Manifest) => void;
  onDelete: (ids: string[]) => void;
  busy: boolean;
}) {
  const [storage, setStorage] = useState<{
    used_bytes: number;
    limit_bytes: number;
  } | null>(null);
  const [storageError, setStorageError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    api<{ runs: NonNullable<typeof storage> }>("/storage", {
      signal: controller.signal,
    })
      .then((data) => {
        setStorage(data.runs);
        setStorageError("");
      })
      .catch((e) => {
        if (e.name !== "AbortError")
          setStorageError("容量读取失败，请刷新记录。");
      });
    return () => controller.abort();
  }, [results]);
  const selectedResults = results.filter((r) =>
    selected.includes(r.episode_id),
  );
  const comparable =
    selectedResults.length > 1 &&
    selectedResults.every(
      (r) =>
        r.comparison_key &&
        r.comparison_key === selectedResults[0].comparison_key,
    );
  return (
    <>
      <div className="toolbar">
        <p>查看单次结果。多方法、多地图和多种子对比请使用「批量评测」。</p>
        <div className="buttons">
          <button
            onClick={() =>
              setSelected(
                results
                  .filter((r) => terminal(r.state))
                  .map((r) => r.episode_id),
              )
            }
          >
            选择已结束记录
          </button>
          <button
            className="danger-button"
            disabled={busy || !selectedResults.some((r) => terminal(r.state))}
            onClick={() =>
              onDelete(
                selectedResults
                  .filter((r) => terminal(r.state))
                  .map((r) => r.episode_id),
              )
            }
          >
            删除选中记录
          </button>
          <button onClick={refresh}>刷新记录</button>
        </div>
      </div>
      <p className="field-note" aria-label="运行记录存储">
        {storageError ||
          (storage
            ? `运行记录占用 ${(storage.used_bytes / 1024 ** 2).toFixed(1)} MiB / ${storage.limit_bytes / 1024 ** 3} GiB。`
            : "正在读取运行记录容量…")}
        删除记录会同时释放帧数据和图像；地图、训练数据、算法报告及算法包不占用此配额。
      </p>
      <section className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>对比</th>
              <th>运行 / 算法</th>
              <th>场景 · 种子</th>
              <th>状态 / 结果</th>
              <th>有效进度</th>
              <th>评分</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {results.map((r) => (
              <tr key={r.episode_id}>
                <td>
                  <input
                    type="checkbox"
                    aria-label={`对比 ${r.episode_id.slice(0, 8)}`}
                    checked={selected.includes(r.episode_id)}
                    onChange={(e) =>
                      setSelected((old) =>
                        e.target.checked
                          ? [...old, r.episode_id]
                          : old.filter((id) => id !== r.episode_id),
                      )
                    }
                  />
                </td>
                <td>
                  <strong>{r.algorithm.name}</strong>
                  <small>
                    #{r.episode_id.slice(0, 8)} · {r.config.execution}
                  </small>
                  {r.benchmark_id && (
                    <small>批次 #{r.benchmark_id.slice(0, 8)}</small>
                  )}
                </td>
                <td>
                  {r.scene?.name || "录制素材"}
                  <small>seed {r.scene?.seed ?? "不适用"}</small>
                </td>
                <td>
                  {stateLabel[r.state]}
                  <small>
                    {reasonLabel[r.metrics?.reason || ""] ||
                      r.failures[0]?.message ||
                      r.metrics?.reason ||
                      "—"}
                  </small>
                </td>
                <td>
                  {r.metrics?.completion == null
                    ? "不提供"
                    : `${(r.metrics.completion * 100).toFixed(1)}%`}
                </td>
                <td>
                  <ScoreDetails score={r.metrics?.score} />
                </td>
                <td>
                  <button
                    disabled={!r.metrics?.frames}
                    onClick={() => onReplay(r)}
                  >
                    回放
                  </button>
                  <button
                    className="danger-button"
                    disabled={busy || !terminal(r.state)}
                    title={
                      terminal(r.state)
                        ? "删除记录和已保存图像"
                        : "请先停止实验"
                    }
                    onClick={() => onDelete([r.episode_id])}
                  >
                    删除
                  </button>
                  <a
                    className="inline-link"
                    href={`/api/results/${r.episode_id}/export/json`}
                  >
                    JSON
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!results.length && (
          <div className="empty">
            还没有实验记录。运行一次实验后，配置、动作和结果会自动保存在这里。
          </div>
        )}
      </section>
      {selectedResults.length > 0 && (
        <section className="panel table-wrap">
          <div className="panel-title">
            <h2>选中实验对比</h2>
            <span>单次结果，不代替多种子成功率</span>
          </div>
          {selectedResults.length > 1 && !comparable && (
            <p className="eval-comparability">
              这些记录的场景、种子、车辆、物理/渲染版本、执行条件不同，或来自没有比较标识的旧版本。仅并排查看，不形成公平排名。
            </p>
          )}
          {comparable && (
            <p className="field-note eval-table-note">
              比较标识一致：使用相同场景、车辆模型、渲染、提示与执行设置。
            </p>
          )}
          <table>
            <thead>
              <tr>
                <th>指标</th>
                {selectedResults.map((r) => (
                  <th key={r.episode_id}>
                    {r.algorithm.name}
                    <small>#{r.episode_id.slice(0, 8)}</small>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {[
                [
                  "综合评分 / 100",
                  (r: Manifest) => fmt(r.metrics?.score?.total, 1),
                ],
                [
                  "整体成功",
                  (r: Manifest) =>
                    r.metrics?.success == null
                      ? "不提供"
                      : r.metrics.success
                        ? "是"
                        : "否",
                ],
                [
                  "接入时间 / s",
                  (r: Manifest) => fmt(r.metrics?.acquisition_time_s),
                ],
                [
                  "跟踪偏差均值 / m",
                  (r: Manifest) =>
                    fmt(r.metrics?.tracking_lateral_error_m.mean, 3),
                ],
                [
                  "跟踪偏差 P95 / m",
                  (r: Manifest) =>
                    fmt(r.metrics?.tracking_lateral_error_m.p95, 3),
                ],
                [
                  "推理 P95 / ms",
                  (r: Manifest) => fmt(r.metrics?.inference_ms.p95, 1),
                ],
                [
                  "非法换线次数",
                  (r: Manifest) =>
                    r.metrics?.illegal_switches == null
                      ? "不提供"
                      : String(r.metrics.illegal_switches.length),
                ],
                [
                  "安全干预帧数",
                  (r: Manifest) =>
                    String(r.metrics?.safety_intervention_frames ?? "不提供"),
                ],
                [
                  "碰撞次数",
                  (r: Manifest) =>
                    String(r.metrics?.collision_count ?? "不提供"),
                ],
                [
                  "合法绕行时间 / s",
                  (r: Manifest) => fmt(r.metrics?.avoidance_duration_s, 1),
                ],
                [
                  "完成时间 / s",
                  (r: Manifest) => fmt(r.metrics?.completion_time_s, 1),
                ],
                [
                  "加加速度 P95 / m/s³",
                  (r: Manifest) => fmt(r.metrics?.jerk_mps3?.p95, 2),
                ],
                [
                  "向量加速度 P95 / m/s²",
                  (r: Manifest) =>
                    fmt(r.metrics?.vector_acceleration_mps2?.p95, 2),
                ],
                [
                  "转向速率 P95 / rad/s",
                  (r: Manifest) => fmt(r.metrics?.steering_rate_rad_s?.p95, 2),
                ],
              ].map(([label, fn]) => (
                <tr key={label as string}>
                  <td>{label as string}</td>
                  {selectedResults.map((r) => (
                    <td key={r.episode_id}>
                      {(fn as (r: Manifest) => string)(r)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </>
  );
}
