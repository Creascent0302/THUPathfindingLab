import { CameraPanel } from "./Panels";
import type { Hint, Point, Preview, Scene } from "./types";

// This is an authoring aid only: algorithms never receive the map geometry.
function startPixel(preview: Preview | null, camera: Scene["camera"]): Point {
  let u = camera.width / 2,
    v = camera.height / 2;
  if (preview?.scene && preview.calibration) {
    const { target_path, initial_pose: pose } = preview.scene;
    const dx = target_path[0][0] - pose.x_m;
    const dy = target_path[0][1] - pose.y_m;
    const x = Math.cos(pose.yaw_rad) * dx + Math.sin(pose.yaw_rad) * dy;
    const y = -Math.sin(pose.yaw_rad) * dx + Math.cos(pose.yaw_rad) * dy;
    const projected = preview.calibration.ground_to_image.map(
      (row) => row[0] * x + row[1] * y + row[2],
    );
    if (projected[2] > 0) {
      u = projected[0] / projected[2];
      v = projected[1] / projected[2];
    }
  }
  return [
    Math.max(0, Math.min(camera.width - 1, Math.round(u))),
    Math.max(0, Math.min(camera.height - 1, Math.round(v))),
  ];
}

export function MapHintEditor({
  hint,
  markerColor,
  camera,
  preview,
  onChange,
}: {
  hint: Hint;
  markerColor: [number, number, number];
  camera: Scene["camera"];
  preview: Preview | null;
  onChange: (hint: Hint) => void;
}) {
  const color = hint.marker_rgb || markerColor;
  const pixelHint = hint.kind === "point" || hint.kind === "region";
  function choose(kind: Hint["kind"]) {
    const [u, v] = startPixel(preview, camera);
    if (kind === "marker")
      onChange({ kind, marker_rgb: markerColor, direction: "arrow" });
    else if (kind === "point")
      onChange({ kind, point_px: [u, v], direction: "unspecified" });
    else if (kind === "region")
      onChange({
        kind,
        region_px: [
          Math.max(0, u - 24),
          Math.max(0, v - 24),
          Math.min(camera.width, u + 24),
          Math.min(camera.height, v + 24),
        ],
        direction: "unspecified",
      });
    else onChange({ kind, direction: "unspecified" });
  }
  return (
    <section className="editor-hints padded-panel" aria-label="起点提示设置">
      <label>
        起点提示类型
        <select
          aria-label="起点提示类型"
          value={hint.kind}
          onChange={(e) => choose(e.target.value as Hint["kind"])}
        >
          <option value="marker">颜色标记与方向箭头（marker）</option>
          <option value="point">首帧目标点（point）</option>
          <option value="region">首帧目标区域（region）</option>
          <option value="none">无提示（none）</option>
        </select>
      </label>
      <p className="field-note">
        选择算法如何确定要跟随的线。路线的第一个控制点仍是实际起点。
      </p>
      {hint.kind === "marker" && (
        <label>
          起点标记颜色
          <input
            aria-label="起点标记颜色"
            type="color"
            value={
              "#" + color.map((c) => c.toString(16).padStart(2, "0")).join("")
            }
            onChange={(e) =>
              onChange({
                kind: "marker",
                direction: "arrow",
                marker_rgb: [1, 3, 5].map((i) =>
                  parseInt(e.target.value.slice(i, i + 2), 16),
                ) as [number, number, number],
              })
            }
          />
          <small>圆环和箭头使用同一颜色，通过 marker_rgb 提供给算法。</small>
        </label>
      )}
      {pixelHint && (
        <p className="field-note">
          {hint.kind === "point"
            ? "在下方首帧画面中点击目标线上的点。"
            : "在下方首帧画面中拖动，框选包含目标线的区域。"}
          提示以图像像素保存，仅对应首帧；修改路线或相机后请重新检查。
          圆环与箭头已隐藏，红色选框只在界面显示，不会画进算法输入。
          <br />
          {hint.kind === "point"
            ? `point_px = (${hint.point_px?.map(Math.round).join(", ")})`
            : `region_px = (${hint.region_px?.map(Math.round).join(", ")})`}
        </p>
      )}
      {hint.kind === "none" && (
        <p className="field-note">
          不提供提示，也不绘制起点圆环和箭头。地图归为压力场景；有多条线时，算法需自行选择目标线。
        </p>
      )}
      {preview?.image ? (
        <CameraPanel
          image={preview.image}
          frame={null}
          calibration={preview.calibration}
          hint={hint}
          hintMode={pixelHint ? (hint.kind as "point" | "region") : null}
          onHint={onChange}
        />
      ) : (
        <p className="field-note">地图检查通过后显示首帧画面。</p>
      )}
    </section>
  );
}
