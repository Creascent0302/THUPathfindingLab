# 视觉寻迹闭环评测

集合：test / core；种子：[5001, 5002]；每回合上限：4000 帧。

算法只接收公开 SDK 观测；评分遵循报告内版本，成功阈值未放宽。结束后真实制动轨迹参与安全与平顺性统计。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 均分 | 碰撞 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---:|---:|---|
| temporal_pursuit | 16/16 | 100.0% | 80.6%–100.0% | 89.42 | 0 | 0 | 30.94 | {'success': 16} |
| temporal_mpc | 16/16 | 100.0% | 80.6%–100.0% | 89.47 | 0 | 0 | 33.43 | {'success': 16} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| temporal_pursuit | straight | 2/2 | 98.3% | {} |
| temporal_pursuit | bend | 2/2 | 98.2% | {} |
| temporal_pursuit | s_curve | 2/2 | 98.2% | {} |
| temporal_pursuit | sharp | 2/2 | 98.3% | {} |
| temporal_pursuit | hairpin | 2/2 | 98.6% | {} |
| temporal_pursuit | parallel | 2/2 | 98.3% | {} |
| temporal_pursuit | close_lines | 2/2 | 98.3% | {} |
| temporal_pursuit | repeated | 2/2 | 99.7% | {} |
| temporal_mpc | straight | 2/2 | 98.3% | {} |
| temporal_mpc | bend | 2/2 | 98.2% | {} |
| temporal_mpc | s_curve | 2/2 | 98.3% | {} |
| temporal_mpc | sharp | 2/2 | 98.3% | {} |
| temporal_mpc | hairpin | 2/2 | 98.5% | {} |
| temporal_mpc | parallel | 2/2 | 98.3% | {} |
| temporal_mpc | close_lines | 2/2 | 98.3% | {} |
| temporal_mpc | repeated | 2/2 | 99.7% | {} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
