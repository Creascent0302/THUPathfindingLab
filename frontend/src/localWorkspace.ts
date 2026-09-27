// Only handles and UI drafts are kept in browser storage; experiment files live
// in the explicitly selected directory. Each tab holds an exclusive writer lock.
export type Directory = FileSystemDirectoryHandle & {
  requestPermission(options: { mode: "readwrite" }): Promise<PermissionState>;
};

type PickerWindow = Window & {
  showDirectoryPicker?: (options: {
    mode: "readwrite";
    id: string;
  }) => Promise<Directory>;
};
export const canChooseDirectory = () =>
  window.isSecureContext && !!(window as PickerWindow).showDirectoryPicker;
export const chooseDirectory = () =>
  (window as PickerWindow).showDirectoryPicker!({
    mode: "readwrite",
    id: "pathlab-workspace",
  });

const keys = ["pathlab.setup.v1", "pathlab.map-draft.v1", "pathlab.tab.v1"];
export function drafts(): Record<string, string> {
  return Object.fromEntries(
    keys.flatMap((key) => {
      const value = localStorage.getItem(key);
      return value === null ? [] : [[key, value]];
    }),
  );
}
export function restoreDrafts(values: Record<string, string>) {
  for (const key of keys) {
    localStorage.removeItem(key);
    if (typeof values[key] === "string" && values[key].length < 2 * 1024 * 1024)
      localStorage.setItem(key, values[key]);
  }
}

export async function checkedFetch(path: string, options?: RequestInit) {
  const response = await fetch(`/api${path}`, options);
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error(detail.detail || `请求失败 (${response.status})`);
  }
  return response;
}

async function write(directory: Directory, name: string, value: Blob | string) {
  const file = await directory.getFileHandle(name, { create: true });
  const stream = await file.createWritable();
  try {
    await stream.write(value);
    await stream.close(); // Browser commits only after successful completion.
  } catch (error) {
    await stream.abort().catch(() => {});
    throw error;
  }
}

export type Checkpoint = {
  format: "pathlab-local-v1";
  archive: string;
  revision: string;
  savedAt: string;
  drafts: Record<string, string>;
};

export async function readCheckpoint(
  directory: Directory,
): Promise<Checkpoint | null> {
  let file: File;
  try {
    file = await (
      await directory.getFileHandle("pathlab-workspace.json")
    ).getFile();
  } catch (error) {
    if (error instanceof DOMException && error.name === "NotFoundError")
      return null;
    throw error;
  }
  if (file.size > 8 * 1024 * 1024) throw new Error("工作区索引过大");
  const data = JSON.parse(await file.text());
  if (
    data.format !== "pathlab-local-v1" ||
    !/^workspace-[ab]\.zip$/.test(data.archive) ||
    typeof data.revision !== "string" ||
    typeof data.drafts !== "object" ||
    !data.drafts
  )
    throw new Error("这个目录的工作区索引损坏，请选择其他目录或恢复备份");
  return data;
}

export async function restoreDirectory(
  directory: Directory,
  checkpoint: Checkpoint,
) {
  const file = await (
    await directory.getFileHandle(checkpoint.archive)
  ).getFile();
  if (file.size > 130 * 1024 * 1024)
    throw new Error("工作区压缩包超过 130 MiB");
  await checkedFetch("/workspace/archive", { method: "POST", body: file });
  restoreDrafts(checkpoint.drafts);
}

export async function saveDirectory(directory: Directory, revision: string) {
  const previous = await readCheckpoint(directory);
  const archive =
    previous?.archive === "workspace-a.zip"
      ? "workspace-b.zip"
      : "workspace-a.zip";
  const response = await checkedFetch("/workspace/archive");
  const target = await directory.getFileHandle(archive, { create: true });
  const stream = await target.createWritable();
  // The response is streamed directly to disk rather than accumulated as a Blob.
  if (!response.body) throw new Error("服务器没有返回工作区数据");
  await response.body.pipeTo(stream);
  const checkpoint: Checkpoint = {
    format: "pathlab-local-v1",
    archive,
    revision,
    savedAt: new Date().toISOString(),
    drafts: drafts(),
  };
  // Commit the index last. A failed download leaves the previous checkpoint intact.
  await write(
    directory,
    "pathlab-workspace.json",
    JSON.stringify(checkpoint, null, 2),
  );
  return checkpoint;
}

export async function rememberDirectory(directory: Directory): Promise<void> {
  const db = await database();
  try {
    await new Promise<void>((resolve, reject) => {
      const tx = db.transaction("handles", "readwrite");
      tx.objectStore("handles").put(directory, "workspace");
      tx.oncomplete = () => resolve();
      tx.onerror = () => reject(tx.error);
    });
  } finally {
    db.close();
  }
}
export async function rememberedDirectory(): Promise<Directory | null> {
  const db = await database();
  try {
    return await new Promise((resolve, reject) => {
      const request = db
        .transaction("handles")
        .objectStore("handles")
        .get("workspace");
      request.onsuccess = () => resolve(request.result || null);
      request.onerror = () => reject(request.error);
    });
  } finally {
    db.close();
  }
}
function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open("pathlab-local-workspace", 1);
    request.onupgradeneeded = () => request.result.createObjectStore("handles");
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}
