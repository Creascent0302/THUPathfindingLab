# 学生算法接口与基本巡线教程

本实验要实现的是：从前向摄像头图像中识别要跟随的引导线，按从近到远的顺序输出它在车辆前方的位置，让平台驱动车辆沿线前进。这里的“车道线”指地面上应跟随的目标线，不要求同时识别左右两条道路边界。

本篇文档介绍该测试平台的输入输出，并给出一个直行算法的接口示例，最后讲解如何自己实现基于图像的巡线方法。

## 1. 车辆怎样运动

平台模拟四轮小车，采用等效前轮转向的自行车模型。车辆坐标系原点位于**后轴中心**，`x` 向前、`y` 向左；长度使用米，时间使用秒，角度使用弧度。

| 参数 / 动作 | 含义 |
|---|---|
| `wheelbase_m` | 轴距，默认 0.32 m |
| `max_steering_rad` | 前轮转角绝对值上限，默认 0.52 rad，约 30° |
| `max_speed_mps` | 前进速度上限，默认 1.5 m/s |
| `steering_angle_rad` | 正值左转、负值右转、0 回正 |
| `speed_mps` | 正值前进、0 请求制动 |

默认运动模型有惯性：速度和转角逐渐变化，制动不会瞬间停下，正反向切换先刹停再换向。转向受轴距、转角和横向加速度等约束，不能原地旋转。上述默认值可以由场景修改，代码必须以本次公开的车辆参数为准。

本实验使用**局部路径模式**。你负责输出前方引导线的米制坐标，平台已有的路径执行器负责计算目标转角和速度，再由车辆模型执行；无需先实现控制器。这个执行器只跟踪你给的路径，不会替你识别目标线或避障，默认也不支持沿路径倒车。

## 2. 平台怎样调用算法

把代码写在 `algorithm.py` 的 `StudentAlgorithm` 类中，提供四个方法：

| 方法 | 调用时机 | 用途 |
|---|---|---|
| `initialize(config, public_context)` | 每次实验创建实例后 | 读取算法参数和车辆限制 |
| `reset(initial_observation, task_hint)` | 实验开始时 | 确定初始目标，清空历史状态 |
| `step(observation)` | 每收到一帧图像 | 识别引导线并返回 `AlgorithmOutput` |
| `close()` | 实验结束时尝试调用 | 释放资源，无资源可写 `pass` |

调用顺序是 `initialize → reset → step → step → … → close`。首帧同时用于 `reset` 和第一次 `step`。`step` 每次只处理当前观测，不能在里面一直等待图像、键盘或开无限循环；跨帧信息放在 `self` 中。

### 能获得哪些输入

| 所需信息 | 从哪里读取 | 用法或注意点 |
|---|---|---|
| 前向图像 | `observation.rgb()` | `H×W×3` 的 NumPy 数组，`uint8`，通道为 RGB |
| 图像尺寸 | `observation.width`、`height` | 不要写死 640×360 |
| 帧号和时间 | `frame_id`、`timestamp_s`、`dt_s` | 掉帧时帧号可能跳变，实际时间间隔用相邻时间戳之差 |
| 相机内参 | `observation.calibration.intrinsic` | 3×3 矩阵，可用于相机几何计算 |
| 地面投影 | `observation.calibration.ground_to_image` | 3×3 矩阵，把车辆地面坐标投影到图像；逆矩阵用于还原地面点 |
| 目标初始化提示 | `reset` 的 `task_hint`，或 `observation.task_hint` | 指定首帧应该接入哪条线，见下文 |
| 车辆参数 | `public_context.get("vehicle_limits")` | 在 `initialize` 中保存；含轴距、转角、速度、制动和倒车限制 |
| 算法参数 | `initialize` 的 `config` | 来自工作台填写的参数字典，可能为空，使用 `config.get(...)` 给默认值 |

`calibration` 在图片、视频输入中可能为 `None`，`vehicle_limits` 也可能不存在。必须先检查再访问。图像若需要转灰度，使用 `cv2.COLOR_RGB2GRAY`，不是 `COLOR_BGR2GRAY`。

`task_hint.kind` 标注轨迹起点的特征或位置，设有四种参数：
- `marker`：用 `marker_rgb` 指定起点标记颜色，`direction="arrow"` 表示图像中有方向箭头；
- `point`：用 `point_px=(u,v)` 指定首帧目标点；
- `region`：用 `region_px=(left,top,right,bottom)` 指定首帧区域；
- `none`：表示没有提示。

**公开输入不含完整地图、目标线真值、真实车辆位置、实际车速或障碍物坐标。** 算法需要的道路位置只能从图像中估计；车辆参数是模型限制，不是实时遥测。网页中的场景俯视图、真实轨迹和评测值供人调试，不能当作算法输入。

### 输出的“线”有两种坐标

| 输出字段 | 坐标含义 | 平台如何使用 |
|---|---|---|
| `centerline_px` | `[(u,v), ...]`，图像左上角为原点，u 向右、v 向下，单位像素 | 在算法画面叠加显示，不会自动控制车辆 |
| `local_path_m` | `[(x,y), ...]`，后轴中心为原点，x 向前、y 向左，单位米 | 局部路径模式下，驱动平台路径执行器 |

例如，`[(0.4,0.0),(0.8,0.1),(1.2,0.25)]` 表示路径逐渐向左弯，**不是图像像素坐标**。通常同时返回两种线：像素线便于检查识别位置，米制路径用于行驶。

`local_path_m` 至少两个点，按本次车体坐标中的行驶顺序，从近到远排列，局部点离后轴中心不超过 30 m。首次实验只输出前方一小段可靠路线，例如 0.4～1.5 m，长度应随可见范围调整；不要为了凑长度虚构远处路线。平台默认前视距离约 0.65 m；路径过短时控制效果可能变差。

`status="TRACK"` 表示可以沿路径行驶；获取或对齐阶段也可以返回 `ACQUIRE` / `ALIGN` 并提供有效路径。没有可靠线时返回 `LOST`，多条线无法确定目标时返回 `AMBIGUOUS`；这些状态会请求制动，可以不提供路径。`FINISHED` 是算法主动结束信号，不等于平台评测成功。

`confidence` 可省略。路径模式未提供时，执行器采用保守系数 0.35；提供时须在 0～1，并会影响速度，不能为了“让车走快一点”随意填 1。`debug` 可记录标量或少量列表，`diagnostics` 可记录文字。返回普通 Python 数值和列表，NumPy 数组用 `.tolist()`，不能包含 NaN / Inf；单帧输出最多 64 KiB，不要塞整张图像。

若以后要自己控制速度、转角或倒车，可改选“车辆动作”，输出 `action=Action(steering_angle_rad=..., speed_mps=...)`。本篇后续练习只需实现局部路径输出。只观察识别效果时，也可以选“图像感知结果”，此模式不驱动车辆。

## 3. 可运行的接口示例：输出车前直线

下面代码完整展示输入读取、图像处理入口、路径输出与像素叠加。**这是一条人为设定的车前直线，不是从图像识别出来的结果，也不是完整巡线答案。** 它只会让车辆沿当前朝向前进，不能修正偏离、转弯或避障。

```python
import cv2
import numpy as np

from pathlab.sdk import AlgorithmOutput


class StudentAlgorithm:
    def initialize(self, config, public_context):
        self.vehicle = public_context.get("vehicle_limits")

    def reset(self, initial_observation, task_hint):
        self.hint = task_hint
        self.last_time = None

    def step(self, observation):
        rgb = observation.rgb()  # 输入：uint8 RGB 图像
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        dt = (observation.dt_s if self.last_time is None
              else observation.timestamp_s - self.last_time)
        self.last_time = observation.timestamp_s

        calibration = observation.calibration
        if calibration is None or self.vehicle is None:
            return AlgorithmOutput(
                status="LOST", diagnostics=["请在有标定的仿真场景运行示例"]
            )

        # 演示路径：当前车辆前方 0.4～1.6 m 的直线，y=0。
        # 实际作业需将这里替换为“从图像识别目标线并转换为米制坐标”。
        path = np.array([(x, 0.0) for x in (0.4, 0.7, 1.0, 1.3, 1.6)])

        # 将演示路径投影回原图，便于在算法画面检查坐标。
        homography = np.asarray(calibration.ground_to_image, dtype=float)
        ground = np.column_stack((path, np.ones(len(path))))
        projected = ground @ homography.T
        projected = projected[projected[:, 2] > 1e-6]
        pixels = projected[:, :2] / projected[:, 2:3]
        visible = ((pixels[:, 0] >= 0) & (pixels[:, 0] < observation.width)
                   & (pixels[:, 1] >= 0) & (pixels[:, 1] < observation.height))

        return AlgorithmOutput(
            status="TRACK",
            local_path_m=path.tolist(),       # 输出给路径执行器
            centerline_px=pixels[visible].tolist(),  # 输出给画面叠加
            debug={
                "frame_id": observation.frame_id,
                "dt_s": float(dt),
                "gray_mean": float(gray.mean()),
                "wheelbase_m": self.vehicle["wheelbase_m"],
                "hint_kind": self.hint.kind,
            },
        )

    def close(self):
        pass
```


## 4. 基本巡线方法：从图像到局部引导线

上一节展示的示例代码并没有利用输入图像，仅展示了各个接口如何使用，下面针对寻迹算法为大家做介绍，逐步建立一条能解释、能调试的处理链：

```text
RGB 图像 → 地面区域 → 深色候选 → 每行线中心
         → 关联同一目标 → 转成米制点 → 平滑、排序 → 局部路径
```

### 第一步：限定观察区域

先观察原始图像，确定地面所在区域。近处引导线一般较宽，远处较细；画面上方可能包含背景或不可靠的远处信息。最初只处理图像中下部的地面，减少无关物体影响。注意若缩小或裁剪图像处理，保存缩放比例和裁剪偏移，输出像素点时还原到**原图坐标**，否则标定转换也会出错。

### 第二步：寻找可能的引导线

把 RGB 图像转换为灰度图，利用“线比地面暗”的差异做阈值分割，得到二值候选图，均匀光照下可采用固定阈值。参数应通过观察候选图调整，不要只盯最终成绩。[OpenCV 阈值分割原理](https://docs.opencv.org/4.x/d7/d4d/tutorial_py_thresholding.html)

增加少量模糊可以抑制噪声，小尺度形态学操作可以去掉孤立点或补小裂缝；操作过强会让细线消失，或把相邻道路连接到一起。阴影和深色障碍物也可能被分割出来，因此“深色区域”只是候选，不等于目标线。

### 第三步：用扫描带提取线中心

从图像下方向上选取若干水平扫描带。每条带内，找出连续的深色区间；一段区间的左右边界为 `u_left` 和 `u_right` 时，中心约为 `(u_left + u_right) / 2`。为它同时保留所在行、宽度等信息。

一行可能有多段深色区间。**分别保留各段中心，不要把整行所有深色像素平均成一个中心**，否则两条平行线会被合成为中间的一条假线。剔除明显过宽或过窄的区间时，也要考虑远近尺度变化。

这一步的结果应是“每个扫描带有若干候选中心”，还不是一条可靠路径。调试时可以通过 `candidates_px` 分组显示候选，先确认真正的线没有被漏掉。

### 第四步：把属于同一目标的中心串起来

首帧依据 `task_hint` 建立目标身份：从提示点或区域附近选择候选，或从起点颜色标记及箭头附近找到应接入的引导线。不能一开始就默认图像中央最近的黑线是目标。

随后从近到远连接候选中心，优先选择与上一扫描带位置、方向连续的点。可以设定允许的横向跳变和方向变化范围；遇到明显跳跃时停止连接。这样能够把一组离散点串成一条局部折线，而不是在相邻道路之间来回跳动。

当两条候选无法区分时先返回 `AMBIGUOUS`；不确定时降低速度或停车，优于输出一条外观平滑但身份错误的线。

### 第五步：把像素点变成车辆坐标

平台提供的矩阵 `H = calibration.ground_to_image` 满足：

```text
[u, v, 1]ᵀ ∝ H [x, y, 1]ᵀ
q = H⁻¹ [u, v, 1]ᵀ
x = q₀ / q₂，y = q₁ / q₂
```

这里的 `(x,y)` 已经是**当前后轴坐标系**下的米制位置，无需再额外叠加相机安装偏移或世界位姿。用原图上的目标线中心做逆变换，得到车辆前方局部点。[OpenCV 单应矩阵说明](https://docs.opencv.org/4.x/d9/dab/tutorial_homography.html)

若 `q₂` 接近零，转换会把像素噪声放大为很远的点，应舍弃；也要剔除非有限值、车后方点和不合理的远点。该变换假设点在地面上，只适用于引导线等地面点，不能把障碍物顶部像素直接当成地面位置。没有标定时先做像素感知实验，不要把像素数硬当成米。

### 第六步：平滑并形成可执行路径

对于前向、没有回头的短局部路段，可用直线或低阶曲线表示 `y=f(x)`；直线阶段先拟合 `y=ax+b`，弯道再考虑二次曲线。使用异常点剔除和适度平滑，避免个别噪声点让路径突然折转。高阶曲线可能产生剧烈振荡，不是阶数越高越好。

在可靠可见范围内重新采样，从近到远输出至少两个点到 `local_path_m`；把识别出的原图点放到 `centerline_px` 方便检查。车正在走向远处时，应每帧重新计算相对于当前车体的路径。不要把某一帧的局部点当成整个实验的固定地图。

路径不能出现不符合车辆转弯能力的尖角。简单几何上最小转弯半径约为 `wheelbase / tan(max_steering)`，默认参数对应约 0.56 m；这只是低速几何限制，有惯性时还要考虑速度、转角变化率等因素。先保留短而平滑的真实线段，再扩展观察距离。

### 第七步：利用前一帧，避免跳到邻线

保存上一帧的目标线位置、方向和可信程度，下一帧优先寻找连续的候选。初学时先低速运行，限定合理的跨帧变化；之后再根据时间间隔和自身历史控制信息改进运动预测。

前一帧像素和车辆坐标都会随小车运动而改变，不能不作判断就原样复用。短暂遮挡可以做有界预测，但要明确限制持续时间和可信范围；本阶段最简单的处理是找不到可靠线就返回 `LOST` 并制动。多条线距离接近时，保持原目标身份比逐帧追最近线更重要。

### 第八步：按层检查，逐步增加难度

按“直线 → 单弯 → S 弯 → 光照变化 → 相邻干扰线”的顺序测试，每次只增加一个难点。先确认候选分割正确，再确认像素中心线正确，随后检查米制路径，最后观察车辆是否沿它行驶。

| 现象 | 优先检查 |
|---|---|
| 两条路之间生成了一条假线 | 是否把同一扫描带的所有暗像素混在一起平均 |
| 画面中的线正确，但车辆反向转弯 | y 向左为正的约定、像素坐标还原、标定逆变换 |
| 路径出现很远的尖刺 | 是否使用了接近地平线的点，齐次除数是否接近零 |
| 邻线一出现就切换目标 | 是否使用起点提示，是否关联上一帧目标 |
| 小车左右摆动 | 路径是否抖动、点序是否正确、可见路径是否过短 |
| 输出了线但车辆不动 | 是否选择局部路径模式、是否提供 `local_path_m`、状态是否允许行驶 |

批量评测时保留失败记录，给不同版本使用相同场景和种子；重点观察合法接入、完成度、偏离、碰撞和综合评分，而不只看自报的 `TRACK`。这个基础方法并不自动解决路口拓扑、连续遮挡或避障，先把输入到路径输出的每一层做对，再逐步扩展。

## 5. 提交时的最小约定

ZIP 根目录放 `algorithm.py`，包含 `StudentAlgorithm`；需要的辅助代码和资源一同打包。不要包含 `.venv`、平台目录或运行记录。ZIP 最大 32 MiB，解压合计最大 128 MiB，单文件最大 32 MiB。

依赖已提供 NumPy、OpenCV 和 SDK；额外第三方库需要教师统一配置，上传 `requirements.txt` 不会自动安装。常见仿真步长是 0.05 s，默认单步硬超时 1 s；这是超时上限，不代表算法达到 20 Hz 的实时要求。

更多字段见 [公共 SDK 协议](protocol.md)，指标含义见 [评测说明](evaluation.md)。
