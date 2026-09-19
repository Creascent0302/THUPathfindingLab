# 视觉寻迹闭环评测

集合：test / core；种子：[5001, 5002]；每回合上限：4000 帧。

算法只接收公开 SDK 观测；评分遵循报告内版本，成功阈值未放宽。结束后真实制动轨迹参与安全与平顺性统计。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 均分 | 碰撞 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---:|---:|---|
| scanline_pid | 12/16 | 75.0% | 50.5%–89.8% | 67.85 | 0 | 0 | 26.64 | {'success': 12, 'episode_timeout': 4} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| scanline_pid | straight | 2/2 | 98.3% | {} |
| scanline_pid | bend | 2/2 | 98.2% | {} |
| scanline_pid | s_curve | 2/2 | 98.3% | {} |
| scanline_pid | sharp | 2/2 | 98.3% | {} |
| scanline_pid | hairpin | 2/2 | 98.5% | {} |
| scanline_pid | parallel | 0/2 | 0.0% | {'episode_timeout': 2} |
| scanline_pid | close_lines | 2/2 | 98.3% | {} |
| scanline_pid | repeated | 0/2 | 20.1% | {'episode_timeout': 2} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
