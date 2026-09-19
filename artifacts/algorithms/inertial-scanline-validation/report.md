# 视觉寻迹闭环评测

集合：validation / core；种子：[204]；每回合上限：1800 帧。

算法只接收公开 SDK 观测；评分遵循报告内版本，成功阈值未放宽。结束后真实制动轨迹参与安全与平顺性统计。耗时为进程内 step（含图像解码），不含工作进程传输、渲染与初始化。

| 算法 | 成功 / 总数 | 成功率 | Wilson 95% 区间 | 均分 | 碰撞 | 非法换线 | 推理均值 ms | 结束原因 |
|---|---:|---:|---|---:|---:|---:|---:|---|
| scanline_pid | 5/8 | 62.5% | 30.6%–86.3% | 60.11 | 0 | 0 | 26.84 | {'success': 5, 'episode_timeout': 3} |

区间按回合二项采样计算；同一生成器的样本有相关性，不能解释为真实道路泛化保证。

| 算法 | 场景族 | 成功 / 总数 | 平均进度 | 失败原因 |
|---|---|---:|---:|---|
| scanline_pid | straight | 1/1 | 98.5% | {} |
| scanline_pid | bend | 1/1 | 98.3% | {} |
| scanline_pid | s_curve | 1/1 | 98.2% | {} |
| scanline_pid | sharp | 1/1 | 98.3% | {} |
| scanline_pid | hairpin | 0/1 | 71.5% | {'episode_timeout': 1} |
| scanline_pid | parallel | 0/1 | 0.0% | {'episode_timeout': 1} |
| scanline_pid | close_lines | 1/1 | 98.5% | {} |
| scanline_pid | repeated | 0/1 | 20.3% | {'episode_timeout': 1} |

逐回合结果、失败详情及最后一帧见 report.json / episodes；完整计划、代码与权重摘要见 plan.json。所有失败均进入分母。
