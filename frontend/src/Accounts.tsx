import { useCallback, useEffect, useState, type FormEvent } from "react";
import App from "./App";
import { api, post, setAccountOwner } from "./types";
import { StorageOwner } from "./usePersistentState";
import "./accounts.css";

type User = {
  id: string;
  username: string;
  display_name: string;
  role: "admin" | "student";
  enabled: boolean;
  must_change_password: boolean;
  used_bytes?: number;
};
type Auth = {
  enabled: boolean;
  user: User | null;
  limits?: { user_runs: number; total_runs: number };
};
type Workspace = {
  used_bytes: number;
  limit_bytes: number;
  user_runs: number;
  total_runs: number;
};
const message = (error: unknown) =>
  error instanceof Error ? error.message : String(error);
const size = (bytes: number) => `${(bytes / 1024 ** 2).toFixed(1)} MiB`;

function notifyTabs() {
  try {
    localStorage.setItem("pathlab.auth-change", String(Date.now()));
  } catch {
    /* Storage can be disabled. */
  }
}

function PasswordForm({ changed }: { changed: () => void }) {
  const [oldPassword, setOld] = useState("");
  const [newPassword, setNew] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (newPassword !== confirmation) {
      setError("两次新密码不一致");
      return;
    }
    setBusy(true);
    setError("");
    try {
      await post("/auth/password", {
        old_password: oldPassword,
        new_password: newPassword,
      });
      notifyTabs();
      changed();
    } catch (error) {
      setError(message(error));
    } finally {
      setBusy(false);
    }
  };
  return (
    <form className="account-form" onSubmit={submit}>
      <h3>修改密码</h3>
      <p>修改后所有设备都需要重新登录。</p>
      <label>
        原密码
        <input
          type="password"
          autoComplete="current-password"
          required
          maxLength={128}
          value={oldPassword}
          onChange={(e) => setOld(e.target.value)}
        />
      </label>
      <label>
        新密码
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          value={newPassword}
          onChange={(e) => setNew(e.target.value)}
        />
      </label>
      <label>
        确认新密码
        <input
          type="password"
          autoComplete="new-password"
          required
          minLength={12}
          maxLength={128}
          value={confirmation}
          onChange={(e) => setConfirmation(e.target.value)}
        />
      </label>
      {error && (
        <p className="account-error" role="alert">
          {error}
        </p>
      )}
      <button disabled={busy}>
        {busy ? "正在修改…" : "保存密码并重新登录"}
      </button>
    </form>
  );
}

function AccountPanel({
  user,
  close,
  refresh,
}: {
  user: User;
  close: () => void;
  refresh: () => void;
}) {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [invitations, setInvitations] = useState<
    { id: string; remaining: number; expires: number }[]
  >([]);
  const [submissions, setSubmissions] = useState<
    { id: string; name: string }[]
  >([]);
  const [sources, setSources] = useState<{ id: string; frame_count: number }[]>(
    [],
  );
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [username, setUsername] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [password, setPassword] = useState("");
  const [uses, setUses] = useState(30);
  const reload = useCallback(async () => {
    const [usage, algorithms, media] = await Promise.all([
      api<Workspace>("/account/workspace"),
      api<typeof submissions>("/submissions"),
      api<typeof sources>("/sources"),
    ]);
    setWorkspace(usage);
    setSubmissions(algorithms);
    setSources(media);
    if (user.role === "admin") {
      const [people, codes] = await Promise.all([
        api<User[]>("/admin/users"),
        api<typeof invitations>("/admin/invitations"),
      ]);
      setUsers(people);
      setInvitations(codes);
    }
  }, [user.role]);
  useEffect(() => {
    void reload().catch((e) => setError(message(e)));
  }, [reload]);
  const perform = async (operation: () => Promise<unknown>) => {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await operation();
      await reload();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="account-backdrop">
      <section
        className="account-dialog"
        role="dialog"
        aria-modal="true"
        aria-label="账号与工作区"
      >
        <header>
          <h2>账号与工作区</h2>
          <button onClick={close} aria-label="关闭账号设置">
            关闭
          </button>
        </header>
        <p>
          {user.display_name} · {user.username} ·{" "}
          {user.role === "admin" ? "教师管理员" : "学生"}
        </p>
        {workspace && (
          <p className="account-usage">
            已使用 {size(workspace.used_bytes)} / {size(workspace.limit_bytes)}{" "}
            · 每人最多 {workspace.user_runs} 个实验，全站 {workspace.total_runs}{" "}
            个。批量任务在容量不足时排队。
          </p>
        )}
        {error && (
          <p className="account-error" role="alert">
            {error}
          </p>
        )}
        {notice && (
          <label className="account-notice">
            请复制保存（关闭后不再展示）
            <textarea readOnly value={notice} />
          </label>
        )}
        <div className="account-columns">
          <PasswordForm changed={refresh} />
          <section>
            <h3>自己的算法和素材</h3>
            <p>运行记录在“运行记录与对比”中删除，地图在地图编辑页维护。</p>
            {submissions.map((item) => (
              <div className="account-item" key={item.id}>
                <span>{item.name}</span>
                <button
                  disabled={busy}
                  onClick={() => {
                    if (
                      confirm(
                        `删除算法“${item.name}”？正在运行或排队的算法不能删除。`,
                      )
                    )
                      void perform(() =>
                        api(`/submissions/${item.id}`, { method: "DELETE" }),
                      );
                  }}
                >
                  删除算法
                </button>
              </div>
            ))}
            {sources.map((item) => (
              <div className="account-item" key={item.id}>
                <span>
                  素材 {item.id.slice(0, 8)} · {item.frame_count} 帧
                </span>
                <button
                  disabled={busy}
                  onClick={() => {
                    if (
                      confirm(
                        "删除素材后，依赖它的历史回放可能无法显示图像。继续删除？",
                      )
                    )
                      void perform(() =>
                        api(`/sources/${item.id}`, { method: "DELETE" }),
                      );
                  }}
                >
                  删除素材
                </button>
              </div>
            ))}
            {!submissions.length && !sources.length && (
              <p>尚未上传算法或素材。</p>
            )}
          </section>
        </div>
        {user.role === "admin" && (
          <section className="account-admin">
            <h3>教师管理</h3>
            <div className="account-columns">
              <form
                className="account-form"
                onSubmit={(event) => {
                  event.preventDefault();
                  void perform(async () => {
                    const account = await post<User>("/admin/users", {
                      username,
                      password,
                      display_name: displayName,
                    });
                    setNotice(
                      `账号：${account.username}\n临时密码：${password}\n学生首次登录必须修改密码。`,
                    );
                    setUsername("");
                    setDisplayName("");
                    setPassword("");
                  });
                }}
              >
                <h4>创建学生账号</h4>
                <label>
                  账号
                  <input
                    required
                    minLength={3}
                    maxLength={32}
                    pattern="[a-zA-Z0-9][a-zA-Z0-9_.\-]{2,31}"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    autoComplete="off"
                  />
                </label>
                <label>
                  姓名
                  <input
                    maxLength={60}
                    value={displayName}
                    onChange={(e) => setDisplayName(e.target.value)}
                  />
                </label>
                <label>
                  临时密码
                  <input
                    required
                    type="password"
                    minLength={12}
                    maxLength={128}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                </label>
                <button disabled={busy}>创建账号</button>
              </form>
              <section>
                <h4>发放课程邀请码</h4>
                <p>学生使用邀请码自行设置账号和密码。邀请码有效期 7 天。</p>
                <label>
                  可注册人数
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={uses}
                    onChange={(e) => setUses(Number(e.target.value))}
                  />
                </label>
                <button
                  disabled={busy}
                  onClick={() =>
                    void perform(async () => {
                      const result = await post<{ code: string }>(
                        "/admin/invitations",
                        { uses, days: 7 },
                      );
                      setNotice(
                        `邀请码：${result.code}\n可供 ${uses} 人注册，7 天有效。`,
                      );
                    })
                  }
                >
                  生成邀请码
                </button>
                {invitations.map((code) => (
                  <div className="account-item" key={code.id}>
                    <span>
                      剩余 {code.remaining} 次 ·{" "}
                      {new Date(code.expires * 1000).toLocaleDateString()} 到期
                    </span>
                    <button
                      disabled={busy}
                      onClick={() => {
                        if (confirm("撤销这个邀请码？已注册的账号不受影响。"))
                          void perform(() =>
                            api(`/admin/invitations/${code.id}`, {
                              method: "DELETE",
                            }),
                          );
                      }}
                    >
                      撤销邀请码
                    </button>
                  </div>
                ))}
              </section>
            </div>
            <div className="account-table">
              <table>
                <thead>
                  <tr>
                    <th>账号 / 姓名</th>
                    <th>状态</th>
                    <th>存储</th>
                    <th>管理</th>
                  </tr>
                </thead>
                <tbody>
                  {users.map((item) => (
                    <tr key={item.id}>
                      <td>
                        {item.username}
                        <small>
                          {item.display_name} ·{" "}
                          {item.role === "admin" ? "管理员" : "学生"}
                        </small>
                      </td>
                      <td>{item.enabled ? "正常" : "已停用"}</td>
                      <td>{size(item.used_bytes || 0)}</td>
                      <td>
                        <button
                          disabled={busy || item.id === user.id}
                          onClick={() => {
                            if (
                              confirm(
                                `${item.enabled ? "停用" : "启用"} ${item.username}？停用会退出其登录并停止任务，数据保留。`,
                              )
                            )
                              void perform(() =>
                                api(`/admin/users/${item.id}`, {
                                  method: "PATCH",
                                  headers: {
                                    "Content-Type": "application/json",
                                  },
                                  body: JSON.stringify({
                                    enabled: !item.enabled,
                                  }),
                                }),
                              );
                          }}
                        >
                          {item.enabled ? "停用" : "启用"}
                        </button>
                        <button
                          disabled={busy}
                          onClick={() => {
                            if (
                              confirm(
                                `停止 ${item.username} 的所有实验及批量任务？`,
                              )
                            )
                              void perform(() =>
                                post(`/admin/users/${item.id}/stop`, {}),
                              );
                          }}
                        >
                          停止任务
                        </button>
                        <button
                          disabled={busy || item.id === user.id}
                          onClick={() => {
                            if (
                              confirm(
                                `重置 ${item.username} 的密码并退出其所有登录？`,
                              )
                            )
                              void perform(async () => {
                                const result = await post<{
                                  temporary_password: string;
                                }>(
                                  `/admin/users/${item.id}/reset-password`,
                                  {},
                                );
                                setNotice(
                                  `账号：${item.username}\n临时密码：${result.temporary_password}`,
                                );
                              });
                          }}
                        >
                          重置密码
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </section>
    </div>
  );
}

export function AccountGate() {
  const [auth, setAuth] = useState<Auth | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [invitation, setInvitation] = useState("");
  const [panel, setPanel] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const next = await api<Auth>("/auth/me");
      setAccountOwner(next.user?.id || null);
      setAuth(next);
      setError("");
    } catch (e) {
      setError(message(e));
    }
  }, []);
  useEffect(() => {
    void refresh();
    const changed = () => {
      setPanel(false);
      void refresh();
    };
    const focused = () => {
      void refresh();
    };
    const stored = (event: StorageEvent) => {
      if (event.key === "pathlab.auth-change") changed();
    };
    window.addEventListener("pathlab-session-expired", changed);
    window.addEventListener("storage", stored);
    window.addEventListener("focus", focused);
    const timer = setInterval(() => {
      void refresh();
    }, 60_000);
    return () => {
      window.removeEventListener("pathlab-session-expired", changed);
      window.removeEventListener("storage", stored);
      window.removeEventListener("focus", focused);
      clearInterval(timer);
    };
  }, [refresh]);
  const logout = async () => {
    setBusy(true);
    try {
      await post("/auth/logout", {});
      setPanel(false);
      notifyTabs();
      await refresh();
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  };
  if (!auth)
    return (
      <main className="account-login">
        <h1>寻迹实验室</h1>
        <p>{error || "正在连接平台…"}</p>
        {error && <button onClick={() => void refresh()}>重试</button>}
      </main>
    );
  if (!auth.enabled) return <App />;
  if (auth.user?.must_change_password)
    return (
      <main className="account-login">
        <h1>请先修改临时密码</h1>
        <p>账号：{auth.user.username}</p>
        <PasswordForm changed={() => void refresh()} />
        <button onClick={() => void logout()}>退出登录</button>
      </main>
    );
  if (auth.user)
    return (
      <StorageOwner.Provider key={auth.user.id} value={auth.user.id}>
        <App
          accountControls={
            <div className="account-controls">
              <strong>{auth.user.display_name}</strong>
              <small>{auth.user.username} · 独立实验工作区</small>
              <div>
                <button onClick={() => setPanel(true)}>
                  账号{auth.user.role === "admin" ? "与用户管理" : "与存储"}
                </button>
                <button disabled={busy} onClick={() => void logout()}>
                  退出
                </button>
              </div>
              {error && <p role="alert">{error}</p>}
            </div>
          }
        />
        {panel && (
          <AccountPanel
            user={auth.user}
            close={() => setPanel(false)}
            refresh={() => {
              setPanel(false);
              void refresh();
            }}
          />
        )}
      </StorageOwner.Provider>
    );
  return (
    <main className="account-login">
      <div className="brand-symbol">↝</div>
      <h1>寻迹实验室</h1>
      <p>登录自己的账号，独立保存地图、算法与实验记录。</p>
      <form
        className="account-form"
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          void (async () => {
            try {
              if (registering)
                await post("/auth/register", {
                  username,
                  password,
                  display_name: displayName,
                  invitation,
                });
              await post("/auth/login", { username, password });
              setPassword("");
              setInvitation("");
              notifyTabs();
              await refresh();
            } catch (e) {
              setError(message(e));
            } finally {
              setBusy(false);
            }
          })();
        }}
      >
        <label>
          账号
          <input
            required
            minLength={3}
            maxLength={32}
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        {registering && (
          <label>
            姓名
            <input
              maxLength={60}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />
          </label>
        )}
        <label>
          密码
          <input
            required
            type="password"
            minLength={registering ? 12 : 1}
            maxLength={128}
            autoComplete={registering ? "new-password" : "current-password"}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {registering && (
          <label>
            教师提供的邀请码
            <input
              required
              maxLength={128}
              autoComplete="off"
              value={invitation}
              onChange={(e) => setInvitation(e.target.value)}
            />
          </label>
        )}
        {error && (
          <p className="account-error" role="alert">
            {error}
          </p>
        )}
        <button disabled={busy}>
          {busy ? "正在处理…" : registering ? "注册并登录" : "登录"}
        </button>
        <button
          type="button"
          className="account-secondary"
          disabled={busy}
          onClick={() => {
            setRegistering(!registering);
            setError("");
          }}
        >
          {registering ? "已有账号，返回登录" : "有邀请码，注册账号"}
        </button>
        <small>忘记密码请联系教师重置。</small>
      </form>
    </main>
  );
}
