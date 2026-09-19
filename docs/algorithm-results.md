# 参考算法验收结果（2026-09-19）

> 本文为渲染 v2 / 运动学 v1 的历史验收。当前默认使用三维场景 v3 与惯性 v2，应参考新版结果；本页成绩不代表新环境表现。

核心集：8 类地图 × 5 个保留种子（1001–1005），每种算法 40 个回合；640×360，20 Hz，4000 帧上限。评分阈值未修改，失败均进入分母。

| 算法 | 成功 | 非法换线 | 主要限制 |
|---|---:|---:|---|
| 时序拓扑 + 调速 Pure Pursuit | 40/40 | 0 | 极紧自定义回头弯可能丢失关联 |
| 时序拓扑 + MPC | 40/40 | 0 | 仍依赖平面标定、图像质量和命令运动预测 |
| 扫描线 PD | 25/40 | 0 | 平行线接入、回头弯、多段可见失败 |
| CNN + GRU（DAgger） | 35/40 | 1 | 平行干扰线全部失败；仅支持已训练的默认标记 |

[完整核心报告](../artifacts/algorithms/final-core/report.md) · [逐回合 JSON](../artifacts/algorithms/final-core/report.json) · [CSV](../artifacts/algorithms/final-core/report.csv)。相同生成器的样本存在相关性；40/40 的 Wilson 95% 区间仍为 91.2%–100%，不能据此保证任意环境成功率超过 95%。

## 压力与新地图

| 集合 | Pure Pursuit | MPC | 条件 |
|---|---:|---:|---|
| [appearance](../artifacts/algorithms/test-appearance/report.md) | 3/3 | 3/3 | 光照 0.5–0.8、阴影 0.4、噪声 6、模糊 0.7、线宽 4 cm |
| [camera](../artifacts/algorithms/test-camera/report.md) | 3/3 | 3/3 | 相机高 0.58 m、俯角 0.61 rad、水平视场 92° |
| [occlusion](../artifacts/algorithms/test-occlusion/report.md) | 3/3 | 3/3 | 仿真周期性中央局部遮挡 |
| [offset](../artifacts/algorithms/test-offset/report.md) | 3/3 | 3/3 | 起点横向偏差 ±0.48 m、航向偏差 ±0.26 rad |
| [custom-extended](../artifacts/algorithms/test-custom-extended/report.md) | 4/5 | 5/5 | 新控制点地图，圆角半径 0.60–0.95 m |

外观、相机、遮挡、偏置各使用保留种子 1005 的 parallel / hairpin / repeated，共 12 个压力配置；自定义地图另用 1001–1005 共 5 张。压力结论样本量有限，不混入核心成功率。MPC 在这些自定义图上更稳；Pure Pursuit 在半径 0.600308 m 的 1004 图约 35% 进度处丢失关联并停车。

## 消融与学习选择

| 验证变体 | 成功 / 总数 | 非法换线 |
|---|---:|---:|
| [完整时序拓扑](../artifacts/algorithms/ablation-full/report.json) | 8/8 | 0 |
| [关闭时序记忆](../artifacts/algorithms/ablation-no-temporal-final/report.json) | 0/8 | 1 |
| [关闭连通性约束](../artifacts/algorithms/ablation-no-topology/report.json) | 6/8 | 0 |

消融均为验证种子 203、320×180、4000 帧。关闭时序后还会失去终点盲区的预测能力，因此 0/8 不能全部归因于目标身份切换。关闭连通性时采用扫描行候选均值，会混合不同线段。

学习模型只用 203–204 的 16 个完整闭环回合选择，保留测试集不参与选择。普通行为克隆 14/16；DAgger、接入加权、两种参数平均均为 15/16。按预先记录的规则，在成功数与非法换线数相同时选择成功回合跟踪误差更小的 DAgger。保留测试得到 35/40，尚未达到 95% 的学习算法目标。详见 [模型选择记录](../artifacts/algorithms/model-selection.json) 与 [模型卡](../algorithms/learning/weights/MODEL_CARD.md)。

## 协议与平台回归

- [真实工作进程：传统方法](../artifacts/algorithms/worker-classical/report.md)：验证种子 204、parallel / repeated，两个模块化方法各 2/2，扫描线 0/2，与其能力边界一致。
- [真实工作进程：学习方法](../artifacts/algorithms/worker-learning/report.md)：同样两张验证图均完成；这用于确认加载、JSONL 协议和运行链路，不代替独立测试成功率。
- [自动回归](../artifacts/algorithms/regression.txt)：98 项通过。TypeScript、Prettier、Ruff 与生产构建通过。
- Chromium 原有流程通过；扩展验收覆盖四种算法前端选择、真实执行、ZIP 提交、地图编辑、删除，共 13 组流程，无页面异常。

快速评测的耗时包含策略 step 与 PNG 解码，不含渲染和 JSONL；工作进程报告包含协议往返。测试期间有并行任务，耗时只能作为本机参考。部署推理不读取场景、种子、真值路线或评测器。
