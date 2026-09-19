export type Point = [number, number];
export type Action = { steering_angle_rad: number; speed_mps: number };
export type Pose = {
  x_m: number;
  y_m: number;
  yaw_rad: number;
  speed_mps?: number;
  steering_angle_rad?: number;
  velocity_x_mps?: number;
  velocity_y_mps?: number;
  yaw_rate_rad_s?: number;
  acceleration_mps2?: number;
};
export type Capability = "action" | "path" | "perception";
export type Mode = "simulation" | "image" | "sequence";
export type Hint = {
  kind: "marker" | "point" | "region" | "none";
  point_px?: Point;
  region_px?: [number, number, number, number];
  direction?: string;
  marker_rgb?: [number, number, number];
};
export type Algorithm = {
  id: string;
  name: string;
  version: string;
  description: string;
  capabilities: Capability[];
  available?: boolean;
  unavailable_reason?: string | null;
};
export type Calibration = {
  width: number;
  height: number;
  intrinsic: number[][];
  ground_to_image: number[][];
};
export type SceneObject = {
  kind: "cone" | "box" | "barrier" | "cylinder";
  x_m: number;
  y_m: number;
  yaw_rad: number;
  length_m: number;
  width_m: number;
  height_m: number;
  color_rgb: [number, number, number];
  collidable: boolean;
  enabled: boolean;
};
export type ObjectScatter = {
  count: number;
  kinds: SceneObject["kind"][];
  clearance_m: number;
  spread_m: number;
  scale: number;
};
export type Scene = {
  render_version?: "1" | "2" | "3";
  name: string;
  family: string;
  seed: number;
  target_path: Point[];
  distractors: Point[][];
  objects?: SceneObject[];
  initial_pose: Pose;
  vehicle: {
    motion_model: "kinematic_v1" | "inertial_v2";
    max_speed_mps: number;
    max_steering_rad: number;
    wheelbase_m: number;
    length_m: number;
    width_m: number;
    track_width_m: number;
    acceleration_mps2: number;
    braking_mps2: number;
    steering_rate_rad_s: number;
    speed_response_s: number;
    yaw_response_s: number;
    lateral_response_s: number;
    jerk_limit_mps3: number;
    max_lateral_acceleration_mps2: number;
  };
  camera: {
    width: number;
    height: number;
    height_m: number;
    pitch_down_rad: number;
    horizontal_fov_deg: number;
  };
  appearance: {
    line_width_m: number;
    line_rgb: [number, number, number];
    ground_rgb: [number, number, number];
    surface: "concrete" | "mat" | "plain";
    texture_strength: number;
    shadow: number;
    object_shadows?: boolean;
    sun_azimuth_rad?: number;
    sun_elevation_rad?: number;
    [key: string]: unknown;
  };
  design?: { waypoints: Point[]; radius_m: number } | null;
  task_hint: Hint;
  dt_s: number;
};
export type Output = {
  status: string;
  confidence: number | null;
  centerline_px: Point[] | null;
  candidates_px: Point[][] | null;
  local_path_m: Point[] | null;
  action: Action | null;
  debug: Record<string, unknown>;
  diagnostics: string[];
};
export type Evaluation = {
  phase: string;
  lateral_error_m: number;
  heading_error_rad: number;
  progress_m: number;
  completion: number;
  reason: string | null;
};
export type Frame = {
  frame_id: number;
  timestamp_s: number;
  output: Output | null;
  inference_ms: number | null;
  applied: { actual: Action; requested: Action } | null;
  interventions: string[];
  evaluation: Evaluation | null;
  pose: Pose | null;
  pose_before: Pose | null;
};
export type History = Pick<
  Frame,
  | "frame_id"
  | "timestamp_s"
  | "applied"
  | "evaluation"
  | "pose"
  | "inference_ms"
>;
export type Distribution = {
  mean: number | null;
  p95: number | null;
  max: number | null;
};
export type Metrics = {
  success: boolean | null;
  acquisition_success: boolean | null;
  acquisition_time_s: number | null;
  completion: number | null;
  tracking_lateral_error_m: Distribution;
  inference_ms: Distribution;
  illegal_switches: unknown[] | null;
  reason: string | null;
  safety_intervention_frames: number;
  failure_counts: Record<string, number>;
  frames: number;
  task_frames?: number;
  truth_metrics_available: boolean;
  score?: Score | null;
  collision_count?: number | null;
  collision_duration_s?: number | null;
  completion_time_s?: number | null;
  simulation_time_s?: number | null;
  steering_rate_rad_s?: Distribution;
  acceleration_mps2?: Distribution;
  vector_acceleration_mps2?: Distribution;
  jerk_mps3?: Distribution;
  realtime_miss_rate?: number | null;
};
export type Score = {
  version: string;
  total: number;
  quality: number;
  rule: string;
  components: Record<string, { value: number | null; weight: number }>;
};
export type Config = {
  mode: Mode;
  algorithm: string;
  execution: Capability;
  family: string;
  seed: number;
  parameters: Record<string, unknown>;
  task_hint: Hint | null;
  source_id: string | null;
  scene: Scene | null;
  max_steps: number;
  timeout_s: number;
  record_images: boolean;
  realtime: boolean;
  stress: {
    mode: "deterministic" | "stress";
    delay_frames: number;
    drop_probability: number;
    action_ttl_s: number;
  };
};
export type Snapshot = {
  id: string;
  state: string;
  paused: boolean;
  frame_count: number;
  frame: Frame | null;
  image: string | null;
  scene: Scene | null;
  config: Config;
  calibration: Calibration | null;
  history: History[];
  logs: string[];
  reason: string | null;
  metrics: Metrics | null;
  failures: { kind: string; message: string }[];
};
export type Manifest = {
  episode_id: string;
  state: string;
  config: Config;
  scene: Scene | null;
  algorithm: Algorithm;
  metrics: Metrics | null;
  failures: { kind: string; message: string }[];
  comparison_key?: string | null;
  physics_version?: string;
  render_version?: string;
  score_version?: string;
  benchmark_id?: string;
};
export type BenchmarkMethodSummary = {
  method_id: string;
  name: string;
  algorithm: string;
  execution: Capability;
  planned: number;
  finished: number;
  successes: number;
  success_rate: number | null;
  score: number | null;
  observed_score: number | null;
  completion: number | null;
  tracking_error_m: number | null;
  tracking_p95_m: number | null;
  inference_p95_ms: number | null;
  completion_time_s: number | null;
  collisions: number;
  illegal_switches: number;
  execution_failures: number;
  measured_runs: number;
};
export type Benchmark = {
  id: string;
  name: string;
  state: string;
  reason: string | null;
  created_at: string;
  updated_at: string;
  test_set_sha256: string;
  score_version: string;
  active_frame?: number;
  summary: {
    finished: number;
    total: number;
    comparable: boolean;
    comparison_note: string;
    methods: BenchmarkMethodSummary[];
  };
  methods: {
    id: string;
    name: string;
    algorithm: string;
    execution: Capability;
  }[];
  cases: { id: string; name: string; seed: number; scene: Scene }[];
  items: {
    case_id: string;
    method_id: string;
    state: string;
    run_id: string | null;
    metrics: Metrics | null;
    error: string | null;
  }[];
};
export type Preview = {
  image: string | null;
  scene: Scene | null;
  calibration: Calibration | null;
  geometry?: {
    length_m: number;
    minimum_vehicle_radius_m: number;
    minimum_path_radius_m: number | null;
  };
};

export async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, options);
  if (!response.ok) {
    const body = await response
      .json()
      .catch(() => ({ detail: response.statusText }));
    throw new Error(
      typeof body.detail === "string"
        ? body.detail
        : JSON.stringify(body.detail),
    );
  }
  return response.json() as Promise<T>;
}
export const post = <T>(path: string, body: unknown) =>
  api<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
export const fmt = (n: number | null | undefined, digits = 2) =>
  n == null ? "不提供" : n.toFixed(digits);
export const terminal = (state?: string) =>
  !!state && ["completed", "failed", "cancelled"].includes(state);
export const stateLabel: Record<string, string> = {
  queued: "初始化中",
  running: "运行中",
  completed: "已完成",
  failed: "失败",
  cancelled: "已停止",
};
export const reasonLabel: Record<string, string> = {
  success: "连续完成目标路径",
  episode_timeout: "达到回合时限",
  deviation: "持续偏离路径",
  illegal_switch: "非法换线",
  user_cancelled: "手动停止",
  client_disconnected: "浏览器断线",
  source_complete: "素材处理完成",
  policy_finished: "算法主动结束",
  invalid_motion: "运动不连续",
  collision: "车辆与障碍物碰撞",
};
