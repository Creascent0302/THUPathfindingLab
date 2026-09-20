import { useCallback, useRef, useState, type SetStateAction } from "react";

// Structural checks protect restoration from malformed/obsolete browser data.
// Geometry limits belong to the server: unfinished, invalid drafts are saved too.
export function matchesShape(value: unknown, example: unknown): boolean {
  if (example === undefined) return true;
  if (example === null) return value === null;
  if (typeof example === "number")
    return typeof value === "number" && Number.isFinite(value);
  if (Array.isArray(example))
    return (
      Array.isArray(value) &&
      (!example.length || value.every((item) => matchesShape(item, example[0])))
    );
  if (typeof example === "object")
    return (
      value !== null &&
      typeof value === "object" &&
      !Array.isArray(value) &&
      Object.entries(example).every(([key, item]) =>
        matchesShape((value as Record<string, unknown>)[key], item),
      )
    );
  return typeof value === typeof example;
}

export function usePersistentState<T>(
  key: string,
  initial: () => T,
  restore: (value: unknown) => T,
  serialize: (value: T) => unknown = (value) => value,
) {
  const [loaded] = useState(() => {
    try {
      const raw = localStorage.getItem(key);
      return {
        value: raw === null ? initial() : restore(JSON.parse(raw)),
        error: "",
      };
    } catch {
      return {
        value: initial(),
        error: "无法恢复浏览器中的草稿或设置；可加载已保存地图，或导入 JSON。",
      };
    }
  });
  const [value, setValue] = useState(loaded.value);
  const [storageError, setStorageError] = useState(loaded.error);
  const current = useRef(value);
  const encode = useRef(serialize);
  encode.current = serialize;
  const update = useCallback(
    (patch: SetStateAction<T>) => {
      const next =
        typeof patch === "function"
          ? (patch as (old: T) => T)(current.current)
          : patch;
      current.current = next;
      // Write in the edit event, before navigation/unmount or immediate reload.
      // Keep editing possible when the browser denies storage or its quota is full.
      try {
        localStorage.setItem(key, JSON.stringify(encode.current(next)));
        setStorageError("");
      } catch {
        setStorageError(
          "浏览器自动保存失败，刷新可能丢失修改。请保存地图或导出 JSON。",
        );
      }
      setValue(next);
    },
    [key],
  );
  return [value, update, storageError] as const;
}
