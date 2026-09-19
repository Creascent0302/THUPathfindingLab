# 参考算法与复现

四种实现均已接入 `algorithms.json` 和前端。部署代码只读 RGB、公开标定、时间、初始化提示、车辆公开约束；地图、真实位姿、场景族、种子和评分不进入策略。训练与评测使用私有真值的代码单独位于 `learning/data.py` 和评测脚本，推理不导入它们。

| ID | 架构 | 依赖与用途 |
|---|---|---|
| `scanline_pid` | 图像扫描线关联 → 低通 PD → 动作 | NumPy/OpenCV；便于教学比较，ID 保留 PID 命名，实际使用 P、D 两项 |
| `temporal_pursuit` | 标定鸟瞰 → 骨架连通性 → 时序身份 → 调速 Pure Pursuit | 推荐作为几何方法参考；无需训练 |
| `temporal_mpc` | 同一视觉层 → 有限时域采样 MPC | 比较两种控制器，显式考虑速度和转向变化约束 |
| `cnn_gru` | 160×96 图像 → CNN → GRU → 转角、速度、可见性 | 可选 PyTorch；真实模仿学习权重，无专家动作回退 |

没有将这些实现命名为 SOTA。引用方法不等于超越已有研究；性能结论以本项目固定集合的实测结果为准。

本轮核心结果：Pure Pursuit 40/40、MPC 40/40、扫描线 25/40、CNN + GRU 35/40；学习模型有一次非法换线。详见 [完整验收结果](algorithm-results.md)，含压力地图、消融、工作进程回归与失败案例。

## 模块化方法

`algorithms/modular/vision.py` 负责几何、图像分割和身份状态；`control.py` 负责两种可替换控制器；`algorithm.py` 仅组装 SDK 生命周期。控制器不读取像素，视觉层不输出车辆动力学真值。

1. 利用公开地面单应矩阵得到 2.5 cm 分辨率的局部鸟瞰图。局部背景对比度抑制阴影，彩色标记单独排除；Zhang–Suen 细化保持断开的线条不被形态学闭运算连接。背景估计使用闭运算，目标掩膜本身不做闭合。
2. 起点标记的方向与位置用于选择目标；也支持公开首帧点 / 区域提示。没有明确身份且存在多个候选时输出 `AMBIGUOUS` 并停车。
3. 通过上一帧请求动作和公开车辆约束预测短时相对运动，将历史目标投影到当前车辆坐标系。多点关联、切向一致性和门限约束阻止跳到相邻线。骨架遍历只允许相邻顶点，避免扫描行均值把同线的不同路段混合。
4. 短时缺失允许 0.45 s 的限速预测，置信度衰减；超时输出 `LOST`。此前确实从图像观测到的橙色终点进入近端盲区时，最多使用 3 s 的尾段预测。它不是从地图推断终点。
5. Pure Pursuit 根据当前速度选择前视距离，并按曲率降低速度。MPC 在 1.2 s 有限时域内采样 63 组两段转向方案，代价含有序路径误差、横向误差和转向平滑项。它是轻量采样优化，不声称求解连续全局最优控制。

两者使用 `action` 接口，图像中心线与米制路径同时用于展示。内部运动预测假设执行其输出动作，因此不把它们注册为可由平台另一控制器替换动作的 `path` 插件。平台制动、掉帧或延迟会使模型预测产生误差，视觉关联门限负责拒绝不一致目标；这不等价于真实里程计。

可在前端参数 JSON 中设置：

```json
{"speed_mps": 0.8, "association_gate_m": 0.16, "memory_s": 0.45}
```

`temporal: false` 和 `topology: false` 分别用于消融。基线支持 `speed_mps`、`kp`、`kd`；扫描线方法保留最后动作最多 1.5 s，缺少完整拓扑身份保证，复杂场景可能失败。

几何方案的 `confidence` 是启发式关联质量分数，不是经校准的成功概率。输出保留状态、候选、路径、预测标志和失败说明，便于课程分析。

## 端到端模型与训练

`algorithms/learning/model.py` 定义 401,259 参数的 CNN + 96 维 GRU；`algorithm.py` 只加载权重并推理。网络直接输出有界转角和速度，10 Hz 更新动作，仿真仍以 20 Hz 推进。GRU 在每次 `reset` 清空；时间倒退会拒绝运行。

模型另预测可见性；可见性很低时输出 `LOST`，按统一平台规则停车。该头不是闭环成功概率，学习算法的 `confidence` 留空。缺少依赖、权重或不匹配的权重格式均明确报错，绝不使用随机初始化模型继续驾驶。

当前权重覆盖默认绿色起点标记。点 / 区域提示与自定义标记颜色没有相应训练覆盖，因此当前权重明确拒绝这些初始化方式。网络保留提示输入通道，后续有相应训练数据时可扩展。训练中的相机扰动不意味着支持任意相机、车辆或真实道路。

训练流程包括：

- 使用完整轨迹的特权专家生成监督标签。专家依据有序真值路线驾驶，部署策略无法调用它。
- 随机改变线宽、灰度、光照、阴影、噪声、模糊、相机高度与俯角，施加短时转向扰动并采集真实纠偏轨迹；加入短暂全图遮挡以训练停车信号。
- 用 12 帧序列训练，前 2 帧只初始化记忆；训练时水平翻转同步反转转向和历史动作符号。
- DAgger 阶段让旧模型实际驾驶，由专家标注其访问的状态；保留 25% 专家行为混合，数据加入训练集继续拟合。专家只存在于离线采集。
- 接入阶段可以用 `--acquisition-weight` 加权前 3.5 s 的转向损失，避免长路径的巡航样本掩盖起点选择问题。
- 训练 / 验证按完整场景分组；训练种子 0–7，离线验证 201–202，闭环开发验证 203–204。最终保留测试种子 1001–1005 不用于训练和调参。
- 对同一初始模型微调得到的权重，提供参数均值工具，借鉴 model soups 思路。结果仍为单个网络，是否改善以独立闭环验证判断；不把论文中的分类性能迁移为本平台结论。

附带权重、训练参数与逐轮真实日志位于 `algorithms/learning/weights/`，数据规模与来源保存在 [训练数据摘要](../artifacts/algorithms/training-data.json)。原始图像数据在本地 `artifacts/learning/`，不要求学生下载，不纳入版本控制。普通 CPU 可以推理；训练需要额外内存和时间。

从头训练（平台启动无需执行）：

```bash
python scripts/setup_learning.py
python run.py learning collect --data artifacts/learning/new-bc --episodes-per-family 8 --validation-seeds 2 --jobs 4
python run.py learning fit --data artifacts/learning/new-bc --epochs 20 --output artifacts/learning/bc.pt
python run.py learning collect --data artifacts/learning/new-dagger --checkpoint algorithms/learning/weights/collection-policy.pt --beta 0.25 --jobs 4
python run.py learning fit --data artifacts/learning/new-bc artifacts/learning/new-dagger --resume artifacts/learning/bc.pt --epochs 8 --lr 0.00015 --output artifacts/learning/dagger.pt
python run.py learning fit --data artifacts/learning/new-bc artifacts/learning/new-dagger --resume artifacts/learning/bc.pt --epochs 4 --lr 0.00015 --acquisition-weight 8 --output artifacts/learning/acquisition.pt
python run.py learning average --checkpoints artifacts/learning/dagger.pt artifacts/learning/acquisition.pt --output artifacts/learning/mean.pt
```

采集目录已有 manifest 时会拒绝覆盖，防止训练记录被替换。模型以完整验证集损失选择 checkpoint。可通过前端参数 `{"checkpoint":"artifacts/learning/dagger.pt"}` 试验新权重；确认验证结果后再替换默认权重。新模型应重新做完整闭环评测，不能只看离线动作误差。

发布版本的 DAgger 数据由基础训练第 7 轮的早期策略采集，采集用权重单独保存在 `collection-policy.pt`，不作为默认驾驶模型。上面的命令使用它以复现同一数据来源；换成自己训练的新策略会得到不同的数据分布。基础拟合完成 20 轮，DAgger 继续拟合 8 轮；接入加权分支训练 4 轮，另验证了 1:1 与 3:1 参数平均候选。最终按闭环验证成功数、非法换线数、成功回合平均跟踪误差依次选择，发布 DAgger 第 8 轮权重。选择过程见 [完整记录](../artifacts/algorithms/model-selection.json)。

## 固定评测

核心集为八类场景 × 五个保留种子，每个算法 40 回合。默认 640×360 RGB、固定 0.05 s、最多 4000 帧、相同车辆约束和公开提示。长多段路径需要约 1300 帧，不能沿用原先 1200 帧上限。评分器与全部阈值保持不变。

维护者可激活 `.venv` 后使用快速评测脚本：

```bash
python scripts/evaluate_algorithms.py --algorithms temporal_pursuit temporal_mpc scanline_pid cnn_gru --seeds 1001 1002 1003 1004 1005 --split test --jobs 4 --output artifacts/reproduction
```

该脚本实际闭环运行公开 SDK 策略、物理模型与原有私有评分器；速度统计只计 `step`（含 PNG 解码），不包含工作进程传输。报告同时写入逐回合 JSON、CSV、Markdown、场景和代码 / 权重 SHA-256；失败全部纳入分母。不同机器、同时运行的任务会影响墙钟耗时。

完整协议评测使用无需激活环境的入口：

```bash
python run.py benchmark --algorithms temporal_pursuit temporal_mpc scanline_pid cnn_gru --families parallel repeated --seeds 204 --split validation --steps 4000 --output artifacts/protocol-check
```

它启动真实工作进程并保存逐帧记录，推理耗时包含 JSONL 协议开销。不要将两种耗时口径混用。压力评测在快速脚本中通过 `--suite appearance|camera|occlusion|offset|custom` 单独选择，不能混入核心成功率。

## 方法来源

- [Nav2 Regulated Pure Pursuit 官方实现说明](https://github.com/ros-navigation/navigation2/blob/main/nav2_regulated_pure_pursuit_controller/README.md)：参考自适应前视与曲率调速思想，本项目使用独立实现和自己的接口。
- [NVIDIA, End to End Learning for Self-Driving Cars](https://arxiv.org/abs/1604.07316)：图像直接监督驾驶动作的思路；本项目为不同规模的 CNN + GRU，不是原网络复现。
- [Ross et al., DAgger](https://proceedings.mlr.press/v15/ross11a.html)：由学习策略访问状态并聚合专家监督，缓解闭环分布偏移。
- [Wortsman et al., Model soups](https://arxiv.org/abs/2203.05482)：同初始化微调网络的参数平均；本项目仅借鉴均值思路，重新验证驾驶闭环效果。

没有拷贝或嵌入上述项目的代码，没有使用外部预训练权重。结果只能支持本教学仿真范围内的比较，不能推出真实车辆部署或学术 SOTA 结论。
