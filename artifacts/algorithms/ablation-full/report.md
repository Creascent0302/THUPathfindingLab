# 视觉寻迹闭环评测

集合：validation / core；种子：[203]；每回合上限：4000 帧。

算法只接收公开 SDK 观测；评分使用原有私有评分器，阈值未放宽。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---|
| temporal_pursuit | 8/8 | 100.0% | 67.6%–100.0% | 0 | 14.61 | {'success': 8} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| temporal_pursuit | straight | 1/1 | 98.4% | {} |
| temporal_pursuit | bend | 1/1 | 98.3% | {} |
| temporal_pursuit | s_curve | 1/1 | 98.3% | {} |
| temporal_pursuit | sharp | 1/1 | 98.4% | {} |
| temporal_pursuit | hairpin | 1/1 | 98.6% | {} |
| temporal_pursuit | parallel | 1/1 | 98.4% | {} |
| temporal_pursuit | close_lines | 1/1 | 98.4% | {} |
| temporal_pursuit | repeated | 1/1 | 99.7% | {} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
