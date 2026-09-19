import { useEffect, useRef, useState } from "react";
import { post, type Action, type Snapshot } from "./types";

export function useLiveStream(
  liveId: string | null,
  setSnapshot: (snapshot: Snapshot) => void,
) {
  const [connected, setConnected] = useState(false);
  useEffect(() => {
    if (!liveId) return;
    let stopped = false,
      socket: WebSocket | null = null,
      pollTimer = 0,
      reconnectTimer = 0;
    const connect = () => {
      if (stopped) return;
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss:" : "ws:"}//${location.host}/api/runs/${liveId}/stream`,
      );
      socket.onopen = () => {
        setConnected(true);
        socket?.send("snapshot");
      };
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data) as Snapshot;
        setSnapshot(data);
        // One outstanding request; do not accumulate messages if rendering is slow.
        pollTimer = window.setTimeout(() => {
          if (socket?.readyState === WebSocket.OPEN) socket.send("snapshot");
        }, 160);
      };
      socket.onclose = () => {
        setConnected(false);
        clearTimeout(pollTimer);
        if (!stopped) reconnectTimer = window.setTimeout(connect, 1000);
      };
    };
    connect();
    return () => {
      stopped = true;
      clearTimeout(pollTimer);
      clearTimeout(reconnectTimer);
      socket?.close();
      setConnected(false);
    };
  }, [liveId]);
  return connected;
}

export function useManualDrive(
  liveId: string | null,
  active: boolean,
  algorithm: string | undefined,
  tab: string,
  speedLimit: number,
  steerLimit: number,
) {
  const [action, setAction] = useState<Action>({
    steering_angle_rad: 0,
    speed_mps: 0,
  });
  const currentAction = useRef(action);
  useEffect(() => {
    currentAction.current = action;
  }, [action]);
  useEffect(() => {
    if (!liveId || !active || algorithm !== "manual") return;
    const timer = window.setInterval(() => {
      post(`/runs/${liveId}/action`, currentAction.current).catch(() => {
        /* Transport status is shown by the live connection badge. */
      });
    }, 150);
    return () => clearInterval(timer);
  }, [liveId, active, algorithm]);
  useEffect(() => {
    const zero = () => setAction({ steering_angle_rad: 0, speed_mps: 0 });
    const down = (event: KeyboardEvent) => {
      if (
        !active ||
        algorithm !== "manual" ||
        tab !== "lab" ||
        /INPUT|TEXTAREA|SELECT/.test((event.target as HTMLElement).tagName)
      )
        return;
      if (
        !["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(
          event.key,
        )
      )
        return;
      event.preventDefault();
      setAction((a) =>
        event.key === " "
          ? { steering_angle_rad: 0, speed_mps: 0 }
          : {
              speed_mps:
                event.key === "ArrowUp"
                  ? Math.min(speedLimit, a.speed_mps + 0.1)
                  : event.key === "ArrowDown"
                    ? Math.max(0, a.speed_mps - 0.1)
                    : a.speed_mps,
              steering_angle_rad:
                event.key === "ArrowLeft"
                  ? steerLimit
                  : event.key === "ArrowRight"
                    ? -steerLimit
                    : a.steering_angle_rad,
            },
      );
    };
    const up = (event: KeyboardEvent) => {
      if (["ArrowLeft", "ArrowRight"].includes(event.key))
        setAction((a) => ({ ...a, steering_angle_rad: 0 }));
    };
    window.addEventListener("keydown", down);
    window.addEventListener("keyup", up);
    window.addEventListener("blur", zero);
    return () => {
      window.removeEventListener("keydown", down);
      window.removeEventListener("keyup", up);
      window.removeEventListener("blur", zero);
    };
  }, [active, algorithm, speedLimit, steerLimit, tab]);
  return [action, setAction] as const;
}
