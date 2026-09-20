# 复杂自定义地图修复与回归

2026-09-19。扫描线 2.0 和 CNN + GRU 3.0 均完成了用户提供的保存图与历史实际失败图。固定独立测试共每方法 16 回合：扫描线、Pure Pursuit、MPC 各 16/16，CNN + GRU 为 15/16。端到端仍有一例平行弯线末段误切，属于当前能力边界。

## 两份不同的用户地图

| 输入 | 控制点 / 路长 | 相机俯角 | 运动 / 渲染模型 |
|---|---|---|---|
| `486c1f986a8f4a4abd2d4e7a2c3018a2.json` | 18 / 40.59 m | 0.52 rad | kinematic_v1 / 2 |
| 历史失败运行 `052fbbf6485b4ccab11b7a5f44424053` 的场景快照 | 20 / 47.15 m | 0.38 rad | inertial_v2 / 3 |

原文件 SHA-256 为 `3874791b893dd79109838920be0f86dad62e9222442d936d1676b5a9ae6eb3bc`，内容保持不变。两份完整输入分别冻结为 [user-original.json](../artifacts/algorithms/custom-final/scenes/user-original.json) 和 [user-actual.json](../artifacts/algorithms/custom-final/scenes/user-actual.json)。

旧扫描线在保存图上约完成 69% 后超时，在实际失败图中未合法接入起点；旧 CNN 能完成保存图，但在实际失败图的第一处左弯把相邻返回段混入动作，约 14% 处失败。必须区分这两份几何，不能将后者的失败归给前者。

## 修复内容

- **有序评测**：合法接入要求真正经过起点位置和方向门；后续仅沿当前可达的有序路段累计进度。独立干扰线和同一目标路线的远端返回段都参与身份检查。出现更可信的错路证据立即冻结进度，持续 0.5 s 判非法换线；未接入且不再接近起点时判接入失败。正常慢速接近、路线交叉、紧弯和制动滑行有独立回归。
- **界面状态**：算法自报 `TRACK` 与评测确认合法接入分别显示，回放展示当前帧参考路段、错误路线和最终结果。安全制动帧显示执行阶段；最终结果写完后才允许按结束状态进入回放，修复偶发缺失结论的时序问题。
- **地图编辑**：目标路线、干扰线、障碍物三种模式。支持多条折线或圆滑干扰线；障碍物可选类型后点击放置、拖动及编辑属性。完整图层随保存、导入、导出和运行保留。旧图添加物件时升级渲染，保留原目标采样、相机、初始姿态和车辆模型。
- **扫描线**：通过标记与跨帧关联保持目标身份，在目标组件上用旋转的小截面提取有序路线。截面只聚合选中横向簇；历史与控制使用第一个局部距离极小段，避免跳到更近的未来返回段。预瞄角误差 PD 加弱曲率前馈，按轴距、预瞄长度、惯性响应调节；失线恢复重置微分项。前方曲线不再外推到车身盲区。
- **学习策略**：补充密集套圈、平行弯线、实际纠偏与起步训练；真实首帧参与监督；第四输入通道显式给出 RGB 中的绿色提示。网络仍直接产生动作，无私有位置输入或几何控制器回退。训练与权重选择见 [学习说明](custom-learning.md)。

## 闭环结果

全部输入使用原生 640×360 图像、20 Hz 仿真、最多 4000 个算法帧，终止后继续记录真实制动。私有评测器与评分版本均为 3.0。

| 方法 | 用户保存图 | 用户实际失败图 | 默认八类 / 6001 | 独立复杂几何 | 保留集总计 |
|---|---:|---:|---:|---:|---:|
| 扫描线 PD 2.0 | 成功 | 成功 | 8/8 | 8/8 | 16/16 |
| Temporal Pursuit | 成功 | 成功 | 8/8 | 8/8 | 16/16 |
| Temporal MPC | 成功 | 成功 | 8/8 | 8/8 | 16/16 |
| CNN + GRU 3.0 | 成功 | 成功 | 8/8 | 7/8 | 15/16 |

复杂保留集为独立生成的套圈 / 平行弯线 × 新旧两种运动模型 × 种子 6001–6002，共 8 个完整场景。所有场景在执行策略前已冻结；发布模型在进入保留测试前固定。两份用户图是开发案例，另有两种新旧物理下的 20 个验证回合；扫描线和发布 CNN 均为 20/20，这些回合不计入保留测试成功率。

**保留失败**：CNN 在 `parallel_curve / 6001 / inertial_v2` 的 91.81% 进度处切入干扰线。16.2 s 时，距有序目标参考段 0.435 m，距干扰线 0.076 m，连续错路后判非法换线。该回合计入分母；本轮未使用它继续调参。所有方法的本轮保留测试均无碰撞。

显式加载两份历史 CNN 权重，在完全相同的保留输入和评测器下得到 14/16：上述惯性平行弯线在约 80.1% 进度失败，另有运动学套圈 `coil / 6001` 在约 26.6% 进度停止后超时。新版修复了后者，前者仍失败；仅凭这 16 个回合不能给出普遍优于旧模型的结论。历史实际失败地图还分别用新扫描线和新 CNN 完整运行独立 Worker / JSONL 协议，两者均成功结束并关闭工作进程。

统计只说明上述有限仿真集合。相邻线重合、完全遮挡、封堵目标线、未覆盖的提示和动力学配置仍可能导致失败；端到端当前没有通用避障能力。不同批次的并行负载不同，因此本报告不以推理耗时或综合分数给方法排性能名次。

## 平台验证与复现

完整 Python 回归 176 项通过；学习与扫描线相关 38 项复核通过。真实 Chromium 覆盖原地图/提交流程 13 组、批量评测 9 组、新图层编辑 7 组、身份状态与回放 8 组，共 37 组，均无页面异常。TypeScript、Prettier、Vite 构建和 Ruff 检查通过。另有 65 条私有几何审计轨迹验证顺序判定，其结果不计作算法成功率。

可在激活项目环境后复现：

```bash
python scripts/evaluate_algorithms.py \
  --algorithms scanline_pid cnn_gru temporal_pursuit temporal_mpc \
  --scene-files artifacts/algorithms/custom-final/scenes/user-original.json \
    artifacts/algorithms/custom-final/scenes/user-actual.json \
  --steps 4000 --jobs 4 --output artifacts/reproduce-user

python scripts/evaluate_algorithms.py \
  --algorithms scanline_pid cnn_gru temporal_pursuit temporal_mpc \
  --seeds 6001 --split test --steps 4000 --jobs 4 \
  --output artifacts/reproduce-core

python scripts/evaluate_algorithms.py \
  --algorithms scanline_pid cnn_gru temporal_pursuit temporal_mpc \
  --scene-files artifacts/algorithms/custom-final/scenes/coil-*.json \
    artifacts/algorithms/custom-final/scenes/parallel_curve-*.json \
  --split test --steps 4000 --jobs 4 --output artifacts/reproduce-complex
```

[汇总证据](../artifacts/algorithms/custom-final/report.json) 保存逐案例指标、实际权重散列及原始计划；完整逐帧轨迹和开发中间结果保存在本机 `artifacts/custom-map-regression/`，不纳入版本控制。浏览器证据见 [图层编辑](../artifacts/browser-map-layers/report.json) 与 [身份状态](../artifacts/browser-route-identity/checks.json)。历史运行保留原结论，新版规则应用于新运行。
