# 学生算法开发指南

你只需要实现一个 Python 类。平台每帧提供前方摄像头图像，你返回转向角和目标速度，平台负责让小车运动。

```text
摄像头图像 → 识别目标线 → 计算转向和速度 → 小车运动 → 下一帧图像
```

## 1. 怎么提交

1. 在网页「算法提交」中下载代码模板。
2. 修改 `algorithm.py` 中的 `StudentAlgorithm` 类。
3. 将 `algorithm.py` 放在 ZIP 根目录；辅助代码、权重等一起打包。
4. 上传时选择「车辆动作」，点击「上传并选用」，然后选择地图运行。

不需要提交平台配置文件。平台已提供 Python、NumPy、OpenCV 和 `pathlab.sdk`，其他依赖请与教师确认，上传包不会自动安装依赖。ZIP 最大 32 MiB，解压后最大 128 MiB，单文件最大 32 MiB。不要打包虚拟环境或实验记录。

## 2. 需要实现的四个方法

| 方法 | 调用时机 | 你需要做什么 |
|---|---|---|
| `initialize(config, public_context)` | 实例创建后调用一次 | 读取参数、加载模型 |
| `reset(initial_observation, task_hint)` | 实验开始时 | 清空历史状态，确定初始目标 |
| `step(observation)` | 每收到一帧图像 | 返回一个 `AlgorithmOutput` |
| `close()` | 实验结束时尝试调用 | 释放资源，没有资源可写 `pass` |

调用顺序：`initialize → reset → step → step → … → close`。首帧会同时用于 `reset` 和第一次 `step`。用 `self` 保存历史状态；不要在 `step` 中写无限循环、等待键盘或打开图像窗口。

`config` 是算法参数字典，可能为空，请设置默认值。仿真中的 `public_context["vehicle_limits"]` 提供车辆参数，常用字段为：

| 字段 | 含义 |
|---|---|
| `max_steering_rad` | 转角绝对值上限，rad |
| `max_speed_mps` | 前进速度上限，m/s |
| `max_reverse_speed_mps` / `reverse_allowed` | 倒车速度上限 / 是否允许倒车 |
| `wheelbase_m` | 轴距，m |
| `acceleration_mps2` / `braking_mps2` | 加速 / 制动能力，m/s² |

这些是模型参数，不是实时车速或位姿。图片、视频实验中的 `vehicle_limits` 可能为 `None`。

## 3. 输入：每帧能读到什么

最常用的是 `observation.rgb()`：

```python
rgb = observation.rgb()  # NumPy 数组，形状 (高度, 宽度, 3)
gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
```

图像类型是 `uint8`，像素值为 0～255，通道顺序为 **RGB，不是 OpenCV 常用的 BGR**。不需要自己解码图像。

| 输入 | 含义 |
|---|---|
| `observation.width` / `height` | 图像宽、高，不要写死分辨率 |
| `observation.frame_id` | 帧号，从 0 开始，掉帧时可能跳号 |
| `observation.timestamp_s` | 当前观测时间，单位 s |
| `observation.dt_s` | 基础帧间隔；计算实际间隔优先用相邻时间戳之差 |
| `observation.task_hint` | 目标初始化提示，见下文 |
| `observation.calibration` | 相机标定，可能为 `None`；简单像素控制可以暂不使用 |

`task_hint.kind` 决定提示类型：

- `marker`：按 `marker_rgb` 提供的 RGB 颜色识别起点；`direction="arrow"` 时需要从图像识别箭头方向。
- `point`：`point_px=(u,v)` 指出首帧中的目标点。
- `region`：`region_px=(left,top,right,bottom)` 指出首帧中的目标区域。
- `none`：没有额外定位提示。

提示在实验中保持不变，点和框只对应首帧。确定目标后，要自己持续跟踪原路线，不能每帧都选择最近的线。

**算法不会收到地图真值、真实车辆位置、实际车速或障碍物坐标，需要根据图像和历史信息作出判断。**

## 4. 输出：怎样控制小车

在 `step` 中返回：

```python
return AlgorithmOutput(
    status="TRACK",
    action=Action(steering_angle_rad=0.2, speed_mps=0.3),
)
```

这表示请求以 0.3 m/s 前进，并将前轮向左转 0.2 rad。

| 动作字段 | 单位和正负方向 |
|---|---|
| `steering_angle_rad` | 弧度；正数左转，负数右转，0 回正 |
| `speed_mps` | m/s；正数前进，负数倒车，0 请求制动 |

输出应限制在本次车辆参数允许的范围内。车辆有惯性，速度设为 0 不会瞬间停下，转角也不会瞬间到位；正反向切换会先制动再换向。

常用状态：

| `status` | 含义和平台处理 |
|---|---|
| `TRACK` | 正常跟踪，执行动作 |
| `ACQUIRE` / `ALIGN` | 获取目标 / 对齐阶段，也允许执行动作 |
| `UNINITIALIZED` | 尚未确定目标，停车 |
| `LOST` / `AMBIGUOUS` | 丢线 / 无法区分目标，停车 |
| `FINISHED` | 算法认为结束，停车；是否成功由平台评测判断 |
| `ERROR` | 算法出错，结束运行并制动 |

调试时可以额外返回 `centerline_px=[(u,v), ...]` 展示识别的线，`confidence` 表示 0～1 的置信度，`debug={...}` 记录数值，`diagnostics=["说明"]` 记录文字。这些字段可以不填；动作模式下，仅返回中心线不会驱动车辆。

## 5. 最小代码模板

下面的模板默认停车。将标注处替换成自己的视觉识别和控制逻辑，找到可靠目标后设置 `status="TRACK"` 并给出速度和转角。

```python
import cv2

from pathlab.sdk import Action, AlgorithmOutput


class StudentAlgorithm:
    def initialize(self, config, public_context):
        self.limits = public_context.get("vehicle_limits")
        if self.limits is None:
            raise ValueError("请在仿真模式运行这个动作控制模板")
        self.cruise_speed = float(config.get("cruise_speed_mps", 0.3))

    def reset(self, initial_observation, task_hint):
        self.hint = task_hint
        # 在这里清空滤波、目标跟踪等历史状态。

    def step(self, observation):
        rgb = observation.rgb()
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)

        # 在这里实现：识别原目标线 → 计算位置/方向误差 → 决定动作。
        # 例如目标在画面左侧时，可请求正转角；弯道应降低速度。
        # 找不到目标时保持停车，不要继续盲目前进。
        status = "UNINITIALIZED"
        steering = 0.0
        speed = 0.0

        max_steering = self.limits["max_steering_rad"]
        reverse_limit = (
            self.limits["max_reverse_speed_mps"]
            if self.limits["reverse_allowed"] else 0.0
        )
        steering = max(-max_steering, min(max_steering, steering))
        speed = max(-reverse_limit, min(self.limits["max_speed_mps"], speed))
        return AlgorithmOutput(
            status=status,
            action=Action(steering_angle_rad=steering, speed_mps=speed),
            debug={"gray_mean": float(gray.mean())},
        )

    def close(self):
        pass
```

建议先在简单直线上以低速调试，再测试弯道、邻近道路和障碍物。看回放时同时检查识别的线、输出动作和实际运动，逐步定位问题。

## 6. 几条数据规范

- **图像坐标** `(u,v)`：原点在左上角，u 向右、v 向下，单位像素。缩放或裁剪图像后，返回的像素点要换回原图坐标。
- **车辆坐标** `(x,y)`：原点在后轴中心，x 向前、y 向左，单位米；角度使用弧度。像素误差不能直接当成米制误差。
- **标定**：`calibration.intrinsic` 是 3×3 内参；`ground_to_image` 是 3×3 地面投影矩阵，满足 `[u,v,1] ∝ H @ [x,y,1]`，地面点可用逆矩阵转换。它不适用于障碍物顶部等非地面点。
- **返回数据**：使用普通 Python 数字、列表和字典，不能包含 NaN 或无穷大。NumPy 数组用 `.tolist()`，标量可用 `float(...)` 转换。单帧输出总量最多 64 KiB，不要放入整张图像。
- **运行时间**：每次 `step` 应尽快返回。常见仿真步长为 0.05 s；默认单步硬超时为 1 s，超时会终止运行。

如果只想输出规划路径，可在上传时选「局部路径」，返回 `status="TRACK"` 和 `local_path_m=[(0.4,0.0),(0.8,0.1), ...]`，由平台控制转向和速度。路径至少两个点，按行驶顺序排列，使用上述车辆坐标系；默认执行器只支持前进。初学时推荐先用「车辆动作」。
