# 参考算法与复现

六种实现均已接入 `algorithms.json` 和前端，其中四种沿线方法与两种避障方法独立注册。部署代码只读 RGB、公开标定、时间、初始化提示、车辆公开约束；地图、真实位姿、场景族、种子和评分不进入策略。训练与评测使用私有真值的代码单独位于 `learning/data.py` 和评测脚本，推理不导入它们。

| ID | 架构 | 依赖与用途 |
|---|---|---|
| `scanline_pid` | 标记与时序身份 → 自适应旋转扫描线 → 曲率前馈 PD | NumPy/OpenCV；ID 保留 PID 命名，反馈实际使用 P、D 两项 |
| `temporal_pursuit` | 标定鸟瞰 → 骨架连通性 → 时序身份 → 调速 Pure Pursuit | 推荐作为几何方法参考；无需训练 |
| `temporal_mpc` | 同一视觉层 → 有限时域采样 MPC | 比较两种控制器，显式考虑速度和转向变化约束 |
| `cnn_gru` | 160×96 图像 → CNN → GRU → 转角、速度、可见性 | 可选 PyTorch；真实模仿学习权重，无专家动作回退 |
| `temporal_pursuit_avoidance` | 时序拓扑 → RGB 障碍物记忆 → 局部绕行 → Pure Pursuit | 独立避障方案；原 `temporal_pursuit` 不启用此功能 |
| `temporal_mpc_avoidance` | 同一避障规划 → 限速 MPC | 独立避障方案；原 `temporal_mpc` 不启用此功能 |

没有将这些实现命名为 SOTA。引用方法不等于超越已有研究；性能结论以本项目固定集合的实测结果为准。

默认场景使用 `inertial_v2` 动力学、渲染版本 `3`、0.38 rad 前视相机与路侧立体物件。最近一轮修复与成绩见 [复杂地图回归](custom-map-results.md)。[惯性初版](inertial-results.md) 和 [运动学历史结果](algorithm-results.md) 保留当时的代码、模型和评分口径，不能直接混入新版评分排行。

## 模块化方法

`algorithms/modular/vision.py` 负责几何、图像分割和身份状态；`control.py` 负责两种可替换控制器；`algorithm.py` 仅组装 SDK 生命周期。控制器不读取像素，视觉层不输出车辆动力学真值。

1. 利用公开地面单应矩阵得到 2.5 cm 分辨率的局部鸟瞰图。局部背景对比度抑制阴影，彩色标记单独排除；Zhang–Suen 细化保持断开的线条不被形态学闭运算连接。背景估计使用闭运算，目标掩膜本身不做闭合。
2. 起点标记的方向与位置用于选择目标；也支持公开首帧点 / 区域提示。没有明确身份且存在多个候选时输出 `AMBIGUOUS` 并停车。
3. 通过上一帧请求动作和公开车辆约束预测短时相对运动，将历史目标投影到当前车辆坐标系。公共 `pathlab/dynamics.py` 的纯积分函数同时供仿真和算法使用；算法维护自己的 8 维估计，保留速度向量、偏航率和加速度，在坐标变换时保留侧向动量，不读取仿真状态。多点关联、切向一致性和门限约束阻止跳到相邻线。骨架遍历只允许相邻顶点，避免扫描行均值把同线的不同路段混合。
4. 短时缺失允许 0.45 s 的限速预测，置信度衰减；超时输出 `LOST`。此前确实从图像观测到的橙色终点进入近端盲区时，最多使用 3 s 的尾段预测。它不是从地图推断终点。
5. Pure Pursuit 根据速度、偏航与横向响应延迟选择前视距离，按曲率、可见前方弯道与横向加速度限制调速。MPC 在 1.2 s 有限时域内采样 63 组两段转向方案，以相同公共积分器和 0.05 s 子步预测惯性、转向变化及制动；代价含有序路径误差、横向误差和转向平滑项。它是轻量采样优化，不声称求解连续全局最优控制。

两者使用 `action` 接口，图像中心线与米制路径同时用于展示。内部运动预测假设执行其输出动作，因此不把它们注册为可由平台另一控制器替换动作的 `path` 插件。平台制动、掉帧或延迟会使模型预测产生误差，视觉关联门限负责拒绝不一致目标；这不等价于真实里程计。

可在前端参数 JSON 中设置：

```json
{"speed_mps": 0.8, "association_gate_m": 0.16, "memory_s": 0.45}
```

`temporal: false` 和 `topology: false` 分别用于消融。正常运行请保留默认身份约束。

扫描线 2.0 复用标定、图像分割、起点初始化和时序身份模块，独立实现路径提取与控制：在已选目标组件上，沿最近切线旋转小范围的法向扫描截面，将前进和后退两次扫描按路线顺序拼接。因此回头弯不再被错误压成图像每行的一个平均横坐标，相邻道路也不会因为出现在同一行而混合。控制使用实际可见预瞄点的角度误差 PD，并加入少量局部曲率前馈，不调用 Pure Pursuit 或 MPC，也不将远处拟合曲线外推到相机盲区。默认巡航上限 0.65 m/s，实际按曲率、置信度与偏差减速；支持 `speed_mps`、`kp`、`kd`。失线采用与其他几何方法相同的有界记忆和终点盲区处理。它需要公开相机标定；没有目标提示且多条线同时可见时会停止并报告歧义。

几何方案的 `confidence` 是启发式关联质量分数，不是经校准的成功概率。输出保留状态、候选、路径、预测标志和失败说明，便于课程分析。

## 独立的避障算法序列

入口在 `algorithms/avoidance.py`，图像障碍物估计与局部规划在 `algorithms/modular/obstacles.py`。原有四种方法保持独立 ID、版本和行为，不通过 `avoidance=true` 参数切换，也不会在避障困难时悄悄回退到其他方法。学生可以直接在批量评测中同时选择原版与对应避障版。

当前两种避障入口为 **2.0**，修复弯道遮挡时无法侧移、物件边缘污染道路骨架及侧移后无法规划接回的问题。实现逻辑、新旧对照与仍失败的地图见 [避障 v2 修复记录](avoidance-v2.md)；下方及 0920 挑战文档中的历史评测不能替代该版本的结果。

避障版从 RGB 中提取彩色立体物件轮廓与地面接触位置；使用公开标定估计平面占用，并以自身上一帧动作预测短时相对运动。支持范围是当前仿真中的彩色交通锥、纸箱等物件，灰色、低对比或与起点标记同色的物件可能漏检。开发中试过灰色宽面的运动残差，但会误把近邻道路当成障碍物，最终版移除了这个分支。策略没有访问地图物件列表、真实位姿或评分器。

遮挡后方路线不可见时，先在已观测走廊内做有限侧移恢复视野；只桥接与遮挡范围相符、切向一致且唯一的续段。规划保存原路线及邻线的空间记忆，候选曲线检查车辆曲率上限、估计障碍物净距和邻线间距。绕行过程中保留原路线身份，只有重新观测到与记忆吻合的目标线并接回后才退出绕行。纯预测路径不足以确认重新接入。

侧移和绕行巡航分别限制在 0.25、0.38 m/s；MPC 使用同一请求速度预测，制动仍由公开惯性模型执行。没有可行候选、后续路线身份无法确认或局部规划预算耗尽时请求停车。它是教学仿真的单目局部规划基线，连续遮挡、灰色物件、未知物体形状、模型误差仍有失败，具体成功和失败均保存在 [0920 挑战记录](0920-challenges.md)。规划中的估计净距不能代替评分器的实际车体碰撞检查。

## 端到端模型与训练

`algorithms/learning/model.py` 定义 401,259 参数的 CNN + 96 维 GRU；`algorithm.py` 只加载权重并推理。网络直接输出有界转角和速度，10 Hz 更新动作，仿真仍以 20 Hz 推进。GRU 在每次 `reset` 清空；时间倒退会拒绝运行。

默认使用同时覆盖两种运动模型的 `driver-complex.pt`，来自实际 CPU 训练并通过闭环验证的固定权重。推理 debug 显示实际权重 SHA-256 与输入版本；具体数据、选择过程和复现见 [复杂地图训练说明](custom-learning.md)。历史 `driver.pt` 和 `driver-inertial.pt` 均保留原文件，可通过参数 `checkpoint` 显式选择，不会因加载旧地图而自动退回旧算法。

模型另预测可见性；可见性很低时输出 `LOST`，按统一平台规则停车。该头不是闭环成功概率，学习算法的 `confidence` 留空。缺少依赖、权重或不匹配的权重格式均明确报错，绝不使用随机初始化模型继续驾驶。

当前权重覆盖默认绿色起点标记。点 / 区域提示与自定义标记颜色没有相应训练覆盖，因此当前权重明确拒绝这些初始化方式。网络保留提示输入通道，后续有相应训练数据时可扩展。训练中的相机扰动不意味着支持任意相机、车辆或真实道路。

训练流程包括：

- 使用完整轨迹的特权专家生成监督标签。专家依据有序真值路线驾驶，部署策略无法调用它。
- 随机改变线宽、灰度、光照、阴影、噪声、模糊、相机高度与俯角，施加短时转向扰动并采集真实纠偏轨迹；加入短暂全图遮挡以训练停车信号。
- 最新模型用 24 帧序列训练，真实起步帧参与监督；从轨迹中途截取的窗口才用前 2 帧初始化记忆。训练时水平翻转同步反转转向和历史动作符号。
- DAgger 阶段让旧模型实际驾驶，由专家标注其访问的状态；保留 25% 专家行为混合，数据加入训练集继续拟合。专家只存在于离线采集。
- 接入阶段用 `--acquisition-weight` 加权前 3.5 s 的损失，默认覆盖转向、速度及可见性；`--acquisition-targets steering` 可复现只加权转向的旧实验。
- 训练 / 验证按完整场景分组。复杂地图训练使用开发种子 0–99 范围，离线验证 201–202，闭环验证 203；本轮独立测试使用 6001–6002。用户反馈地图作为开发数据，不能当作未见测试图。5001–5002、1001–1005 分别是两轮历史报告的测试种子。
- 对同一初始模型微调得到的权重，提供参数均值工具，借鉴 model soups 思路。结果仍为单个网络，是否改善以独立闭环验证判断；不把论文中的分类性能迁移为本平台结论。

附带权重、训练参数与逐轮真实日志位于 `algorithms/learning/weights/`，新版数据规模与每个 NPZ 的校验值保存在 [惯性训练数据摘要](../artifacts/algorithms/inertial-data-summary.json)，旧数据见 [历史摘要](../artifacts/algorithms/training-data.json)。原始图像数据在本地 `artifacts/learning/`，不要求学生下载，不纳入版本控制。普通 CPU 可以推理；训练需要额外内存和时间。

从头训练（平台启动无需执行）：

```bash
python scripts/setup_learning.py
python run.py learning collect --data artifacts/learning/new-bc --episodes-per-family 8 --validation-seeds 2 --jobs 4
python run.py learning fit --data artifacts/learning/new-bc --epochs 20 --output artifacts/learning/bc.pt
python run.py learning collect --data artifacts/learning/new-dagger --checkpoint artifacts/learning/bc.pt --beta 0.25 --jobs 4
python run.py learning fit --data artifacts/learning/new-bc artifacts/learning/new-dagger --resume artifacts/learning/bc.pt --epochs 8 --lr 0.00015 --output artifacts/learning/dagger.pt
python run.py learning fit --data artifacts/learning/new-bc artifacts/learning/new-dagger --resume artifacts/learning/bc.pt --epochs 4 --lr 0.00015 --acquisition-weight 8 --output artifacts/learning/acquisition.pt
python run.py learning average --checkpoints artifacts/learning/dagger.pt artifacts/learning/acquisition.pt --output artifacts/learning/mean.pt
```

采集目录已有 manifest 时会拒绝覆盖，防止训练记录被替换。训练主文件按完整验证集损失保存；`--save-every` 另保存固定轮次候选，发布依据独立闭环验证。可通过前端参数 `{"checkpoint":"artifacts/learning/dagger.pt"}` 试验新权重。不要只看离线动作误差来选择驾驶模型。

上述命令使用当前场景生成器建立新的实验，不会复现旧图像分布。新版附带权重由历史驾驶模型初始化，在两组实际惯性轨迹上微调，按独立验证集监督损失选择第 6 轮，之后冻结权重进行闭环测试。复现这次微调的精确命令见惯性模型卡。历史 DAgger 模型与 `collection-policy.pt` 的来源、20 + 8 轮训练及接入加权实验见 [历史选择记录](../artifacts/algorithms/model-selection.json)；旧权重不会被新版默认模型覆盖。

## 固定评测

上一轮复杂地图回归的独立集包含八类默认场景各一个保留种子，以及套圈 / 平行弯线 × 两种物理模型 × 两个保留种子，共每方法 16 回合。默认 640×360 RGB、固定 0.05 s、最多 4000 个算法帧，随后另记实际制动至静止的帧。当时评分器 / 总分版本为 3.0；当前避障回归使用 4.0，两者成绩不可混合。历史评分阈值不能替代新增约束。

维护者可激活 `.venv` 后使用快速评测脚本：

```bash
python scripts/evaluate_algorithms.py --algorithms temporal_pursuit temporal_mpc scanline_pid cnn_gru --seeds 6001 --split test --jobs 4 --output artifacts/reproduction-core
python scripts/evaluate_algorithms.py --algorithms scanline_pid cnn_gru --scene-files artifacts/maps/你的地图.json --steps 4000 --output artifacts/reproduction-custom
```

该脚本实际闭环运行公开 SDK 策略、物理模型与私有评分器；推理耗时统计只计 `step`（含 PNG 解码），不包含工作进程传输。`--scene-files` 冻结完整输入，保留地图、相机、物理模型和原种子，只有显式 `--seeds` 才重复改变种子。报告写入逐回合 JSON、CSV、Markdown、实际轨迹和代码 / 权重 SHA-256；失败全部纳入分母。终止后的制动不会增加任务完成度，但碰撞和舒适性统计覆盖刹停过程。不同机器、同时运行的任务会影响墙钟耗时与实时性分数。运行评测期间应固定代码和权重。

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
