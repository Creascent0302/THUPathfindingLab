import { useEffect, useState } from "react";
import type { Scene } from "./types";

type Vehicle = Scene["vehicle"];
const fields: {
  key: keyof Vehicle;
  label: string;
  min: number;
  max: number;
  step: number;
}[] = [
  {
    key: "max_speed_mps",
    label: "最高速度 / m/s",
    min: 0.1,
    max: 5,
    step: 0.1,
  },
  {
    key: "acceleration_mps2",
    label: "最大加速度 / m/s²",
    min: 0.1,
    max: 10,
    step: 0.1,
  },
  {
    key: "braking_mps2",
    label: "制动减速度 / m/s²",
    min: 0.1,
    max: 20,
    step: 0.1,
  },
  {
    key: "steering_rate_rad_s",
    label: "前轮转角变化率 / rad/s",
    min: 0.1,
    max: 10,
    step: 0.1,
  },
  {
    key: "speed_response_s",
    label: "速度响应时间 / s",
    min: 0.08,
    max: 1.5,
    step: 0.02,
  },
  {
    key: "yaw_response_s",
    label: "车身转向响应 / s",
    min: 0.05,
    max: 1,
    step: 0.01,
  },
  {
    key: "lateral_response_s",
    label: "速度方向响应 / s",
    min: 0.05,
    max: 1,
    step: 0.01,
  },
  {
    key: "jerk_limit_mps3",
    label: "加速度变化上限 / m/s³",
    min: 0.5,
    max: 40,
    step: 0.5,
  },
  {
    key: "max_lateral_acceleration_mps2",
    label: "横向加速度上限 / m/s²",
    min: 0.3,
    max: 15,
    step: 0.1,
  },
];

export function VehicleSettings({
  scene,
  disabled,
  apply,
}: {
  scene: Scene | null;
  disabled: boolean;
  apply: (scene: Scene) => void;
}) {
  const [vehicle, setVehicle] = useState<Vehicle | null>(
    scene?.vehicle ?? null,
  );
  useEffect(() => setVehicle(scene?.vehicle ?? null), [scene]);
  if (!scene || !vehicle) return null;
  return (
    <details>
      <summary>车辆惯性与制动</summary>
      <p className="field-note">
        响应时间越大，惯性越明显。松开油门或停止实验后，车辆按制动参数继续运动至停稳。青色箭头表示实际速度方向。
      </p>
      <label>
        运动模型
        <select
          aria-label="运动模型"
          disabled={disabled}
          value={vehicle.motion_model}
          onChange={(e) =>
            setVehicle({
              ...vehicle,
              motion_model: e.target.value as Vehicle["motion_model"],
            })
          }
        >
          <option value="inertial_v2">惯性与速度向量 v2</option>
          <option value="kinematic_v1">历史运动学 v1</option>
        </select>
      </label>
      {fields
        .filter((_, i) => vehicle.motion_model === "inertial_v2" || i < 4)
        .map((field) => (
          <label key={field.key}>
            {field.label}
            <input
              aria-label={field.label}
              type="number"
              min={field.min}
              max={field.max}
              step={field.step}
              disabled={disabled}
              value={vehicle[field.key]}
              onChange={(e) =>
                setVehicle({ ...vehicle, [field.key]: Number(e.target.value) })
              }
            />
          </label>
        ))}
      <button disabled={disabled} onClick={() => apply({ ...scene, vehicle })}>
        应用车辆设置
      </button>
      <p className="field-note">
        设置随场景保存，所有算法均会收到相同的车辆参数。批量测试可选择保存后的自定义地图。
      </p>
    </details>
  );
}
