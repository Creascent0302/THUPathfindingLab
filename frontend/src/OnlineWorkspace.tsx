import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  canChooseDirectory,
  checkedFetch,
  chooseDirectory,
  drafts,
  readCheckpoint,
  rememberDirectory,
  rememberedDirectory,
  restoreDirectory,
  restoreDrafts,
  saveDirectory,
  type Directory,
} from "./localWorkspace";
import "./online.css";

type Hosting = {
  mode: "local" | "online";
  authenticated?: boolean;
  student?: string;
  expires_in_s?: number;
};
type Inventory = {
  revision: string;
  empty: boolean;
  used_bytes: number;
  limit_bytes: number;
  busy: boolean;
};

export function OnlineWorkspace({ children }: { children: ReactNode }) {
  const [hosting, setHosting] = useState<Hosting | null>(null);
  const [code, setCode] = useState("");
  const [ready, setReady] = useState(false);
  const [directory, setDirectory] = useState<Directory | null>(null);
  const [remembered, setRemembered] = useState<Directory | null>(null);
  const [message, setMessage] = useState(
    "请选择本地目录，或使用压缩包导入 / 下载模式。",
  );
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState("");
  const saving = useRef(false);
  const lastSaved = useRef("");
  const releaseLock = useRef<(() => void) | null>(null);
  const fallbackInput = useRef<HTMLInputElement>(null);

  async function refreshHosting() {
    const info = (await (await checkedFetch("/hosting")).json()) as Hosting;
    setHosting(info);
    return info;
  }
  useEffect(() => {
    void refreshHosting().catch((e) => setError(String(e)));
    void rememberedDirectory()
      .then(setRemembered)
      .catch(() => {});
    return () => releaseLock.current?.();
  }, []);

  async function attempt(work: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  async function lockWorkspace() {
    if (releaseLock.current) return;
    if (!navigator.locks)
      throw new Error(
        "当前浏览器不支持工作区写入锁，请使用新版桌面 Chrome 或 Edge",
      );
    await new Promise<void>((resolve, reject) => {
      void navigator.locks
        .request(
          "pathlab-online-workspace",
          { ifAvailable: true },
          async (lock) => {
            if (!lock) {
              reject(new Error("另一个标签页正在使用工作区，请先关闭它"));
              return;
            }
            await new Promise<void>((release) => {
              releaseLock.current = release;
              resolve();
            });
          },
        )
        .catch(reject);
    });
  }

  async function openDirectory(handle: Directory) {
    if ((await handle.requestPermission({ mode: "readwrite" })) !== "granted")
      throw new Error("需要目录读写授权才能自动保存");
    await lockWorkspace();
    const checkpoint = await readCheckpoint(handle);
    const state = (await (
      await checkedFetch("/workspace")
    ).json()) as Inventory;
    if (checkpoint && state.empty) {
      await restoreDirectory(handle, checkpoint);
      setSaved(checkpoint.savedAt);
    } else if (checkpoint && !state.empty) {
      if (
        !window.confirm(
          "服务器临时会话仍有数据。继续会保留服务器当前内容，并在下次保存时更新这个目录；不会用旧备份覆盖当前实验。",
        )
      )
        return;
    } else if (state.empty) {
      restoreDrafts({});
    }
    await rememberDirectory(handle).catch(() => {});
    setDirectory(handle);
    setReady(true);
    setMessage("目录已授权；运行结束后自动保存，也可点击立即保存。");
    lastSaved.current = "";
  }

  async function save(force = false) {
    if (!directory) return;
    if (saving.current) {
      if (force) throw new Error("正在保存，请完成后再操作");
      return;
    }
    saving.current = true;
    try {
      const response = await fetch("/api/workspace");
      if (!response.ok)
        throw new Error(
          "会话连接中断；本地上一次保存仍保留，请恢复连接后重试。",
        );
      const state = (await response.json()) as Inventory;
      if (state.busy) {
        setMessage(
          "实验仍在运行或批次排队中，结束后自动保存。离开前请先停止实验并保存。",
        );
        if (force) throw new Error("请先停止实验和批量测试，再保存工作区");
        return;
      }
      const signature = state.revision + JSON.stringify(drafts());
      if (signature === lastSaved.current && !force) return;
      setMessage("正在写入本地目录，请勿关闭页面…");
      const checkpoint = await saveDirectory(directory, state.revision);
      lastSaved.current = signature;
      setSaved(checkpoint.savedAt);
      setMessage(
        `已保存到 ${directory.name} · ${(state.used_bytes / 1024 / 1024).toFixed(1)} / 128 MiB`,
      );
      setError("");
    } finally {
      saving.current = false;
    }
  }

  useEffect(() => {
    if (!ready || hosting?.mode !== "online") return;
    const sync = () => {
      void refreshHosting()
        .then((info) => {
          if (!info.authenticated) {
            setMessage(
              "会话已过期。本地上次保存仍在，请重新登录恢复；未保存内容无法恢复。",
            );
            return;
          }
          return save();
        })
        .catch((e) => {
          setError(String(e));
        });
    };
    sync();
    const timer = window.setInterval(sync, 10000);
    const warn = (event: BeforeUnloadEvent) => {
      // A new edit/run could have started since the last checkpoint.
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => {
      clearInterval(timer);
      window.removeEventListener("beforeunload", warn);
    };
  }, [ready, directory]);

  async function download() {
    const response = await checkedFetch("/workspace/archive");
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "pathlab-workspace.zip";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 60000);
    setMessage(
      "已发起下载，请确认文件已保存。此模式需要手动下载，网页不能确认写盘结果。",
    );
  }

  if (hosting?.mode === "local") return <>{children}</>;
  if (!hosting)
    return (
      <div className="online-entry panel">
        <h1>连接实验平台</h1>
        <p>{error || "正在连接…"}</p>
        <button
          onClick={() =>
            void attempt(async () => {
              await refreshHosting();
            })
          }
        >
          重试
        </button>
      </div>
    );
  if (!hosting.authenticated)
    return (
      <div className="online-entry panel">
        <h1>寻迹实验室 · 在线课堂</h1>
        <p>
          输入教师提供的个人访问码。实验在独立临时环境中运行，结果由你保存到本地。
        </p>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            void attempt(async () => {
              await checkedFetch("/session", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code }),
              });
              setCode("");
              setReady(false);
              await refreshHosting();
            });
          }}
        >
          <label>
            个人访问码
            <input
              type="password"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              autoComplete="off"
            />
          </label>
          <button className="primary" disabled={busy}>
            {busy ? "准备运行环境…" : "进入课堂"}
          </button>
        </form>
        {error && <p role="alert">{error}</p>}
      </div>
    );

  const errors = error && (
    <p className="online-error" role="alert">
      {error}
    </p>
  );
  if (!ready)
    return (
      <div className="online-entry panel">
        <h1>选择你的实验工作目录</h1>
        <p>
          推荐使用桌面 Chrome /
          Edge，选择一个专用文件夹。地图、算法包、素材、运行记录与批量结果会一起保存，下次访问时从这里恢复。
        </p>
        <p>
          服务器只保留临时副本：关闭页面后约 5 分钟回收，会话最长 4
          小时。请在离开前结束运行并确认已保存。
        </p>
        <div className="buttons">
          {canChooseDirectory() && (
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                void attempt(async () => openDirectory(await chooseDirectory()))
              }
            >
              选择本地目录
            </button>
          )}
          {remembered && canChooseDirectory() && (
            <button
              disabled={busy}
              onClick={() =>
                void attempt(async () => openDirectory(remembered))
              }
            >
              重新授权 {remembered.name}
            </button>
          )}
          <button
            disabled={busy}
            onClick={() => fallbackInput.current?.click()}
          >
            恢复工作区 ZIP
          </button>
          <button
            disabled={busy}
            onClick={() =>
              void attempt(async () => {
                await lockWorkspace();
                const state = (await (
                  await checkedFetch("/workspace")
                ).json()) as Inventory;
                if (state.empty) restoreDrafts({});
                setReady(true);
                setMessage(
                  "手动下载模式：离开前请下载工作区 ZIP。此模式不会自动写入本地目录。",
                );
              })
            }
          >
            使用手动下载模式
          </button>
        </div>
        {!canChooseDirectory() && (
          <p>此浏览器不支持目录授权，可通过 ZIP 文件恢复和下载保存。</p>
        )}
        <input
          ref={fallbackInput}
          hidden
          type="file"
          accept=".zip"
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (!file) return;
            void attempt(async () => {
              await lockWorkspace();
              if (file.size > 130 * 1024 * 1024)
                throw new Error("ZIP 超过 130 MiB");
              await checkedFetch("/workspace/archive", {
                method: "POST",
                body: file,
              });
              restoreDrafts({});
              setReady(true);
              setMessage(
                "已恢复。当前为手动下载模式，结束后请下载工作区 ZIP。",
              );
            });
          }}
        />
        {errors}
      </div>
    );

  return (
    <>
      <section className="online-bar" aria-label="本地工作区">
        <div>
          <strong>
            {hosting.student} · {directory?.name || "手动下载模式"}
          </strong>
          <span>{message}</span>
          {saved && <small>最近保存：{new Date(saved).toLocaleString()}</small>}
          {(hosting.expires_in_s ?? 99999) < 600 && (
            <p>
              会话将在 {Math.ceil((hosting.expires_in_s || 0) / 60)}{" "}
              分钟内回收，请停止实验并保存。
            </p>
          )}
          {errors}
        </div>
        <div className="buttons">
          {directory && (
            <button
              disabled={busy}
              onClick={() => void attempt(() => save(true))}
            >
              立即保存到本地
            </button>
          )}
          <button disabled={busy} onClick={() => void attempt(download)}>
            下载工作区 ZIP
          </button>
          <button
            disabled={busy}
            onClick={() =>
              void attempt(async () => {
                if (directory) await save(true);
                if (
                  !window.confirm(
                    directory
                      ? "本地保存完成。结束临时会话？"
                      : "请确认已下载最新工作区。结束后服务器临时数据会立即删除，继续？",
                  )
                )
                  return;
                await checkedFetch("/session", { method: "DELETE" });
                releaseLock.current?.();
                releaseLock.current = null;
                setReady(false);
                setDirectory(null);
                setSaved("");
                lastSaved.current = "";
                restoreDrafts({});
                await refreshHosting();
              })
            }
          >
            结束会话
          </button>
        </div>
      </section>
      {children}
    </>
  );
}
