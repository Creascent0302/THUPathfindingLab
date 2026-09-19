import type { Dispatch, SetStateAction } from "react";
import { fmt, reasonLabel, stateLabel, terminal, type Manifest } from "./types";

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
  const selectedResults = results.filter((r) =>
    selected.includes(r.episode_id),
  );
  return (
    <>
      <div className="toolbar">
        <p>选择记录进行对比。场景、种子、提示和执行模式应保持一致。</p>
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
      <section className="panel table-wrap">
        <table>
          <thead>
            <tr>
              <th>对比</th>
              <th>运行 / 算法</th>
              <th>场景 · 种子</th>
              <th>状态 / 结果</th>
              <th>有效进度</th>
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
      <div className="notice">
        教师批量评测：
        <code>
          python run.py benchmark --algorithms stop constant --seeds 101 102
          --steps 400
        </code>
        。完整配置和阈值在查看结果之前固定并保存。
      </div>
    </>
  );
}
