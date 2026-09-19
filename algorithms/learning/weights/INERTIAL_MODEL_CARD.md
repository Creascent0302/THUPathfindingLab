# 惯性车辆 CNN + GRU 模型卡

`driver-inertial.pt` 是针对 `inertial_v2` 与渲染版本 `3` 实际微调的模型。部署按公开车辆模型选择它；历史 `kinematic_v1` 继续加载 `driver.pt`。网络直接从图像和上一条动作预测转向 / 速度，没有几何专家回退。

- 架构：`cnn_gru_v1`，401,259 参数，160×96 RGB + 提示平面，4 层 CNN、96 维 GRU、直接动作与可见性头；10 Hz 网络更新、20 Hz 物理步。
- 初始化：历史真实训练模型，SHA-256 `8184a5a2effc11a935e2033740814b56be2c74cb173720503423e104ab44a0d0`。
- 当前权重 SHA-256：`09e31baca684b4046e416765a314085aea2bb1c74086d4aa55814ebd4609ffdb`。
- 选择：6 轮 CPU 微调中，完整验证场景的监督损失最低第 6 轮；不使用保留测试挑选参数。
- 数据：64 条训练轨迹 / 14,146 帧；32 条验证轨迹 / 7,338 帧。两种相机分布对应 32 个独立训练场景和 16 个独立验证场景，不能把不同视角轨迹算成独立场景。
- 场景：8 族，训练种子 0–3、离线验证 201–202；闭环验证 203–204；新保留测试 5001–5002。按完整场景隔离，没有使用测试帧训练。
- 随机化：相机俯角 0.33–0.47 与 0.46–0.60 rad，高度 / 线宽 / 光照 / 噪声 / 模糊、道路旁立体物件；速度响应 0.14–0.22 s、偏航响应 0.09–0.16 s、横向响应 0.07–0.14 s、加加速度限幅 4.5–7.5 m/s³。
- 训练：CPU PyTorch 2.7.1+cpu，4 线程，种子 42；AdamW 初始学习率 0.0001，序列 12 帧，前 2 帧预热，接入阶段损失权重 3，6 轮耗时 378.8 s。
- 第 6 轮离线验证：归一化转向 MAE 0.02125、速度 MAE 0.00853 m/s。监督误差不能解释为闭环成功率。

闭环结果：新保留种子 5001–5002，8 族共 **15/16 成功**；`parallel / 5002` 在接入目标前超时，进度为 0。闭环验证 203–204 为 **14/16 成功**，两次失败均为 parallel 接入失败后碰撞，进度为 0。失败完整保留；16 个测试回合不足以支持真实道路或任意自定义场景的普适性能结论。

训练监督允许读取私有路线；部署模块仅使用公开 SDK 观测和车辆限制。物件只作为视觉干扰；当前模型没有训练通用避障行为。自定义物件占据目标线时，碰撞由平台记录与扣分；不能把普通视觉寻迹算法视为已具备绕障规划。

模型仅训练默认绿色标记初始化。点 / 区域提示会明确报错；改变标记颜色或超出上述车辆 / 相机分布需要重新训练并评测。可见性头低于阈值时请求 LOST，平台通过真实制动停止；此输出不表示身份置信度。

实际计划与逐轮日志在 `driver-inertial.plan.json` / `driver-inertial.training.json`；每份 NPZ 校验值、数据索引和完整场景参数见 [新数据摘要](../../../artifacts/algorithms/inertial-data-summary.json)。闭环结果分别保存在 `artifacts/algorithms/inertial-learning-validation` 与 `artifacts/algorithms/inertial-learning-core`，历史模型成绩见 [历史模型卡](MODEL_CARD.md)。

复现微调（使用已经采集的数据）：

```bash
python -m algorithms.learning.train fit --data artifacts/learning/inertial-data artifacts/learning/inertial-forward-data --resume algorithms/learning/weights/driver.pt --output artifacts/learning/reproduced-inertial.pt --epochs 6 --threads 4 --lr 0.0001 --acquisition-weight 3
```

重新采集默认前视角分布：

```bash
python -m algorithms.learning.train collect --data artifacts/learning/new-forward-data --episodes-per-family 4 --validation-seeds 2 --jobs 4
```
