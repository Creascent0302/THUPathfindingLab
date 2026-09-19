import { useState } from "react";
import { api, type Algorithm, type Capability } from "./types";

export function SubmissionPanel({
  algorithms,
  onSelect,
  refresh,
  attempt,
  busy,
}: {
  algorithms: Algorithm[];
  onSelect: (algorithm: Algorithm) => void;
  refresh: () => Promise<void>;
  attempt: (operation: () => Promise<unknown>) => Promise<void>;
  busy: boolean;
}) {
  const [name, setName] = useState("");
  const [capability, setCapability] = useState<Capability>("action");
  const [file, setFile] = useState<File | null>(null);
  const uploaded = algorithms.filter((a) => a.id.startsWith("upload_"));
  return (
    <div className="submission-layout">
      <section className="panel padded-panel">
        <div className="panel-title">
          <h2>提交算法压缩包</h2>
          <a href="/api/submissions/template" download>
            ↓ 下载代码模板
          </a>
        </div>
        <p className="field-note">
          将 algorithm.py 和所需的辅助代码、权重一起打包为
          ZIP。上传后即可在工作台选择并运行，无需修改配置文件。
        </p>
        <label>
          算法名称
          <input
            aria-label="算法名称"
            maxLength={80}
            value={name}
            placeholder="例如：第 3 组 · 实验一"
            onChange={(e) => setName(e.target.value)}
          />
        </label>
        <label>
          输出类型
          <select
            aria-label="提交输出类型"
            value={capability}
            onChange={(e) => setCapability(e.target.value as Capability)}
          >
            <option value="action">车辆动作</option>
            <option value="path">车辆坐标系局部路径</option>
            <option value="perception">图像感知结果</option>
          </select>
        </label>
        <label className="zip-drop">
          {file ? file.name : "选择算法 ZIP"}
          <input
            aria-label="算法压缩包"
            type="file"
            accept=".zip,application/zip"
            disabled={busy}
            onChange={(e) => {
              const next = e.target.files?.[0] || null;
              setFile(next);
              if (next && !name) setName(next.name.replace(/\.zip$/i, ""));
            }}
          />
          <small>ZIP ≤ 32 MiB · 解压 ≤ 128 MiB · 最多 512 个条目</small>
        </label>
        <button
          className="primary"
          disabled={busy || !file}
          onClick={() =>
            attempt(async () => {
              if (!file) return;
              const form = new FormData();
              form.append("file", file);
              form.append("name", name || file.name);
              form.append("capability", capability);
              const algorithm = await api<Algorithm>("/submissions", {
                method: "POST",
                body: form,
              });
              await refresh();
              onSelect(algorithm);
            })
          }
        >
          {busy ? "正在检查并导入…" : "上传并选用"}
        </button>
        <p className="field-note">
          入口类为 StudentAlgorithm。运行环境已提供 NumPy、OpenCV 和平台
          SDK；其他第三方依赖由教师统一配置。
        </p>
      </section>
      <section className="panel padded-panel">
        <div className="panel-title">
          <h2>已提交算法</h2>
          <span>{uploaded.length} 个版本</span>
        </div>
        {uploaded.length ? (
          uploaded.map((a) => (
            <div className="submission-row" key={a.id}>
              <div>
                <strong>{a.name}</strong>
                <small>
                  {a.capabilities.join(" / ")} · #{a.id.slice(-8)}
                </small>
              </div>
              <button disabled={busy} onClick={() => onSelect(a)}>
                选用
              </button>
            </div>
          ))
        ) : (
          <div className="empty">
            上传后的算法会保存在这里，重启服务后仍可使用。
          </div>
        )}
      </section>
    </div>
  );
}
