# 公共 SDK 与学生接入协议 v1.0

代码定义是 `pathlab/sdk.py`。所有 SDK 模型拒绝未知顶层字段、NaN、Inf、非法形状与不支持的协议版本。可选值缺失表示「不提供」，不是零。

## 生命周期与输入

```python
initialize(config: dict, public_context: dict) -> None
reset(initial_observation: Observation, task_hint: TaskHint) -> None
step(observation: Observation) -> AlgorithmOutput
close() -> None
```

每次运行创建独立实例。`initialize` 收到注册实验中的参数，和执行能力、坐标说明、纯视觉赛道声明及公开车体限制。`reset` 接收首帧，不消耗推理帧；随后 `step` 从 frame 0 开始顺序执行。

| Observation 字段 | 含义 |
|---|---|
| protocol_version | 固定 `"1.0"` |
| episode_id | 随机运行 UUID，不编码地图/种子 |
| frame_id | 从 0 开始，压力掉帧后可能跳跃 |
| timestamp_s | 当前输入观测的仿真/素材时间，单位 s |
| dt_s | 仿真基准步长；录制素材为 1 / FPS |
| width / height | 本帧尺寸；上限 1280×720 |
| color_space / dtype | `RGB` / `uint8` |
| encoding / image | `png_base64` / PNG 的 Base64 字符串 |
| calibration | 可选；K 和车辆地面到图像的 3×3 单应矩阵 |
| task_hint | 本次公开的初始化提示，在整个回合保持不变 |

Python 中用 `observation.rgb()` 得到 `H×W×3 np.uint8`；颜色通道不是 OpenCV 默认的 BGR。SDK 检查 PNG 文件头尺寸，拒绝声明尺寸与编码内容不一致的图像。

纯视觉观察不含真实世界位姿、地图、目标线 ID、随机种子、场景名称和未来帧。当前没有扩展遥测赛道。调用相机反投影时使用有效标定，不能把像素直接解释为米。

## 初始化提示

```json
{"kind":"marker","marker_rgb":[34,160,94],"direction":"arrow"}
{"kind":"point","point_px":[312,230],"direction":"unspecified"}
{"kind":"region","region_px":[260,160,370,280],"direction":"unspecified"}
{"kind":"none","direction":"unspecified"}
```

像素原点是图像左上角，X 向右，Y 向下。点必须在图像内，区域为 `[left, top, right, bottom]`。人工提示只确定目标位置；没有观察到箭头时，不能把 `unspecified` 理解为已知行进方向。多线不可区分且没有足够提示时，学生算法应返回 `AMBIGUOUS`。

点击或框选在首帧预览中完成，并保存到运行配置；同组算法比较必须使用完全相同的提示。当前示例探针只检查输入和候选，不实现目标连续性推断。

## 三类输出

注册 `capabilities` 可以包含 `perception`、`path`、`action` 中的一种或多种；实验的 `execution` 明确决定执行哪一种。声明不匹配的实验被拒绝。

| 字段 | 含义与限制 |
|---|---|
| status | 必填；UNINITIALIZED / ACQUIRE / ALIGN / TRACK / LOST / AMBIGUOUS / FINISHED / ERROR |
| confidence | 可选 0–1；无可信估计时留 null |
| candidates_px | 多条可见候选线，仅图像几何，不自动推断身份 |
| centerline_px | 算法选定目标中心线，按认为的行进方向排序 |
| local_path_m | 至少两点的车辆坐标路径，X 前、Y 左，按行进顺序近到远 |
| action | steering_angle_rad、speed_mps，两个字段都必须有 |
| lateral_error_m / heading_error_rad / curvature_per_m | 算法自己的估计，缺失可为空；不是评分真值 |
| debug | 有界 JSON 对象，用于候选数量、时序状态等中间结果 |
| diagnostics | 有界文字列表 |

每条中心线/局部路径最多 4096 点，最多 128 个候选，整个输出编码后不得超过 64 KiB。输出中的正转角表示等效前轮向左转，速度为目标前进速度，单位 m/s。超出车体配置的有限动作不隐瞒：保存原始请求，记录饱和/变化率限制，再执行受限动作。NaN / Inf 不是可限幅的动作，直接失败。

`action` 模式缺少动作或 `path` 模式缺少路径，实验失败；不会补成零值。`perception` 模式不驾驶。LOST、AMBIGUOUS、UNINITIALIZED、FINISHED 状态触发明确的停车干预；ERROR 标记算法失败。算法主动 FINISHED 不等于评分成功。

`path` 执行器默认 Pure Pursuit，前视距离 0.65 m，按输出路径顺序选点，计算 `curvature = 2*y/(x²+y²)`、`steering = atan(wheelbase*curvature)`。速度随曲率与置信度降低；没有置信度时使用保守的执行系数 0.35，这不是算法置信度，也不会写回为算法估计。替换执行器只需实现相同 `action(output)` 边界，不读取地图。

## 独立进程 / 其他语言

`algorithms.json` 可注册命令数组（不经过 shell）：

```json
{
  "id":"external_stop",
  "name":"独立进程示例",
  "version":"1.0",
  "capabilities":["action"],
  "command":["{python}","-m","student_template.stdio"]
}
```

`{python}` 替换为当前平台虚拟环境的解释器。也可以注册显式可执行文件或另一个 Python 环境的绝对路径；本地插件默认工作目录为项目根目录。前端上传的算法由平台自动登记，工作目录为上传包中 `algorithm.py` 所在目录；学生无需编辑注册表。

标准输入/输出为 UTF-8 **JSON Lines**，每条消息以一个 LF 结束，最大 8 MiB。不得在 stdout 输出日志（改写 stderr）。请求串行发送，响应必须匹配 id 和版本；不允许 pickle 或任意对象反序列化。

请求：

```json
{"protocol_version":"1.0","id":1,"method":"initialize","payload":{"config":{},"public_context":{"execution":"action"}}}
```

成功响应：

```json
{"protocol_version":"1.0","id":1,"ok":true,"result":null}
```

方法与 payload：

- initialize：`config`、`public_context`；返回 null。
- reset：`observation`、`task_hint`；返回 null。
- step：`observation`；返回完整的 AlgorithmOutput 对象。
- close：空对象；返回 null，再退出。

step 响应示例：

```json
{"protocol_version":"1.0","id":3,"ok":true,"result":{"protocol_version":"1.0","status":"ACQUIRE","confidence":null,"action":{"steering_angle_rad":0.1,"speed_mps":0.3}}}
```

错误响应：

```json
{"protocol_version":"1.0","id":3,"ok":false,"error":"image dimensions unsupported"}
```

超时后平台终止进程并取消后续请求；收到非法 JSON、错误版本、超限消息或断开的 stdout 后记录失败。close 最多等待 0.2 s 后强制清理。标准错误有界保存，不能依赖大量日志作为结果通道。

## 调试建议

先用 `image_probe` 检查实际颜色和候选，再接入自己的实现。优先在单帧/序列中验证感知输出，确认状态重置，然后进入闭环。照片没有有效标定时不要输出伪造的米制路径。

RGB/BGR、形状和生命周期示例见 `tests/test_simulation.py`；故障与外部语言协议测试见 `tests/test_runtime.py`。测试用的故障插件没有加入生产注册表。

## ZIP 提交约定

`GET /api/submissions/template` 下载模板；`POST /api/submissions` 接收 multipart 字段 `file`、`name` 与 `capability`（action / path / perception）。ZIP 的根目录或唯一的一层子目录需包含 `algorithm.py`，其中定义 `StudentAlgorithm`；生命周期与上文相同。可一并打包辅助 Python 模块、资源和权重。

平台静态解析 Python 语法，不在 HTTP 服务中导入提交代码。ZIP 上限 32 MiB，解压合计 128 MiB，单文件 32 MiB，最多 512 个条目；拒绝路径穿越、绝对路径、符号链接、加密文件及重复路径。第三方依赖由教师统一配置，ZIP 中的 requirements / setup 文件不触发安装。每次提交单独保存，SHA-256 随运行配置记录。上传本身不执行算法，选用后在独立进程中运行。进程具有教师账户的系统权限，不能代替恶意代码容器沙箱。
